"""
PDF discovery service.

Strategy: fetch the Oscar clinical guidelines page and parse the __NEXT_DATA__
JSON that Next.js embeds in the HTML. This gives structured access to all
guideline titles and their page-level URLs — more reliable than DOM scraping.

Three sections are harvested:
  - Module 2: "Upcoming Policy Changes" (nested items)
  - Module 3: "Medical Guidelines" (flat items)
  - Module 4: "Adopted Guidelines" (only items with link text "PDF")
"""

import re
import json
import logging
import time
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Policy

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.hioscar.com/clinical-guidelines/medical"
BASE_URL = "https://www.hioscar.com"
REQUEST_HEADERS = {
    "User-Agent": "OscarGuidelineScraper/1.0 (educational project)",
    "Accept": "text/html",
}


def _fetch_next_data(url: str) -> dict:
    """Fetch a Next.js page and extract the __NEXT_DATA__ JSON."""
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        resp.text,
    )
    if not match:
        raise ValueError(f"Could not find __NEXT_DATA__ in {url}")
    return json.loads(match.group(1))


def _extract_guidelines(next_data: dict) -> list[dict]:
    """
    Walk the Contentful modules and collect (title, href) for every PDF link.
    Returns list of {"title": str, "pdf_url": str}.
    """
    landing = (
        next_data
        .get("props", {})
        .get("pageProps", {})
        .get("initialReduxState", {})
        .get("landingPage", {})
        .get("data", {})
    )
    modules = landing.get("fields", {}).get("modules", [])
    guidelines = []

    for mod in modules:
        fields = mod.get("fields", {})
        content_type = (
            mod.get("sys", {})
            .get("contentType", {})
            .get("sys", {})
            .get("id", "")
        )

        if content_type == "landing.expandableList":
            list_items = fields.get("listItems", [])
            for item in list_items:
                item_fields = item.get("fields", {})

                # Flat items (Medical Guidelines, Adopted Guidelines)
                link = item_fields.get("link", {})
                if isinstance(link, dict):
                    link_f = link.get("fields", {})
                    if link_f.get("text") == "PDF":
                        href = link_f.get("href", "")
                        title = item_fields.get("item", "").strip()
                        if href and title:
                            full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                            guidelines.append({"title": title, "pdf_url": full_url})

                # Nested items (Upcoming Policy Changes)
                nested_items = item_fields.get("nestedItems", [])
                for nested in nested_items:
                    n_fields = nested.get("fields", {})
                    n_link = n_fields.get("link", {})
                    if isinstance(n_link, dict):
                        n_link_f = n_link.get("fields", {})
                        if n_link_f.get("text") == "PDF":
                            href = n_link_f.get("href", "")
                            title = n_fields.get("item", "").strip()
                            if href and title:
                                full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                                guidelines.append({"title": title, "pdf_url": full_url})

    return guidelines


def discover_pdfs(db: Session) -> int:
    """
    Discover all PDF links from the Oscar clinical guidelines page.
    Upserts into the policies table — idempotent on pdf_url.
    Returns the number of newly inserted policies.
    """
    logger.info("Fetching source page: %s", SOURCE_URL)
    next_data = _fetch_next_data(SOURCE_URL)
    guidelines = _extract_guidelines(next_data)
    logger.info("Found %d guideline PDF links on the page", len(guidelines))

    new_count = 0
    for g in guidelines:
        existing = db.execute(
            select(Policy).where(Policy.pdf_url == g["pdf_url"])
        ).scalar_one_or_none()

        if existing is None:
            policy = Policy(
                title=g["title"],
                pdf_url=g["pdf_url"],
                source_page_url=SOURCE_URL,
                discovered_at=datetime.now(timezone.utc),
            )
            db.add(policy)
            new_count += 1
            logger.info("Discovered: %s", g["title"])
        else:
            logger.debug("Already exists: %s", g["title"])

    db.commit()
    logger.info("Discovery complete. %d new policies added.", new_count)
    return new_count
