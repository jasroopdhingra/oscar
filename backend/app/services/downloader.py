"""
PDF download service.

Each policy's pdf_url points to a Next.js page (not a raw PDF). The actual PDF
is hosted on Contentful's CDN and referenced inside __NEXT_DATA__.  The
downloader resolves this two-step indirection:

  1. Fetch the policy page HTML
  2. Extract the Contentful PDF URL from __NEXT_DATA__ → modules → file → url
  3. Stream-download the actual PDF to backend/pdfs/{policy_id}.pdf

Includes retry (3 attempts, exponential backoff) and polite throttling (1.5s
between requests).
"""

import os
import re
import json
import time
import logging
from datetime import datetime, timezone

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import Session

from app.models import Policy, Download

logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pdfs")
REQUEST_HEADERS = {
    "User-Agent": "OscarGuidelineScraper/1.0 (educational project)",
}
THROTTLE_SECONDS = 1.5


def _resolve_pdf_url(page_url: str) -> str:
    """
    Fetch a policy page and extract the actual PDF URL from __NEXT_DATA__.
    The PDF URL lives at: modules[0].fields.file.url
    """
    resp = requests.get(page_url, headers=REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        resp.text,
    )
    if not match:
        raise ValueError(f"No __NEXT_DATA__ found at {page_url}")

    data = json.loads(match.group(1))
    page_props = data.get("props", {}).get("pageProps", {})

    # Try the initialReduxState path first (SSG pages)
    landing = (
        page_props
        .get("initialReduxState", {})
        .get("landingPage", {})
        .get("data", {})
    )
    modules = landing.get("fields", {}).get("modules", [])

    # Also check top-level pageProps.modules
    if not modules:
        modules = page_props.get("modules", [])

    for mod in modules:
        fields = mod.get("fields", {})
        file_info = fields.get("file", {})
        if not isinstance(file_info, dict):
            continue

        # Path 1: Flattened structure (pageProps.modules) — file.url
        if "url" in file_info:
            url = file_info["url"]
            if url.startswith("//"):
                url = "https:" + url
            return url

        # Path 2: Full Contentful entry (initialReduxState) — file.fields.file.url
        nested = file_info.get("fields", {}).get("file", {})
        if isinstance(nested, dict) and "url" in nested:
            url = nested["url"]
            if url.startswith("//"):
                url = "https:" + url
            return url

    raise ValueError(f"No PDF file URL found in __NEXT_DATA__ at {page_url}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, ValueError)),
    before_sleep=lambda rs: logger.warning(
        "Retry attempt %d for download", rs.attempt_number
    ),
)
def _download_single(policy: Policy, db: Session) -> Download:
    """Download a single policy PDF with retry logic."""
    os.makedirs(PDF_DIR, exist_ok=True)
    stored_path = os.path.join(PDF_DIR, f"{policy.id}.pdf")

    try:
        pdf_url = _resolve_pdf_url(policy.pdf_url)
        logger.info("Resolved PDF URL for '%s': %s", policy.title, pdf_url)

        resp = requests.get(pdf_url, headers=REQUEST_HEADERS, timeout=60, stream=True)
        resp.raise_for_status()

        with open(stored_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        download = Download(
            policy_id=policy.id,
            stored_location=stored_path,
            downloaded_at=datetime.now(timezone.utc),
            http_status=resp.status_code,
            error=None,
        )
        logger.info("Downloaded: %s (%d bytes)", policy.title, os.path.getsize(stored_path))

    except Exception as e:
        download = Download(
            policy_id=policy.id,
            stored_location=None,
            downloaded_at=datetime.now(timezone.utc),
            http_status=getattr(getattr(e, "response", None), "status_code", None),
            error=str(e),
        )
        logger.error("Failed to download '%s': %s", policy.title, e)
        raise

    return download


def download_all_pdfs(db: Session) -> int:
    """
    Download all discovered PDFs that haven't been successfully downloaded yet.
    Returns the number of successful downloads this run.
    """
    policies = db.query(Policy).all()
    success_count = 0

    for policy in policies:
        existing = (
            db.query(Download)
            .filter(Download.policy_id == policy.id, Download.error.is_(None))
            .first()
        )
        if existing:
            logger.debug("Already downloaded: %s", policy.title)
            continue

        try:
            dl = _download_single(policy, db)
            db.add(dl)
            db.commit()
            success_count += 1
        except Exception as e:
            dl = Download(
                policy_id=policy.id,
                stored_location=None,
                downloaded_at=datetime.now(timezone.utc),
                http_status=None,
                error=str(e),
            )
            db.add(dl)
            db.commit()
            logger.error("All retries failed for '%s': %s", policy.title, e)

        time.sleep(THROTTLE_SECONDS)

    logger.info("Download complete. %d successful.", success_count)
    return success_count
