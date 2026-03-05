"""
PDF text extraction service.

Uses pdfplumber to extract text from downloaded PDFs. Caps extraction at
MAX_PAGES to keep LLM context within reasonable token limits — medical
guideline PDFs can be 30+ pages, but the criteria we need are typically
in the first 10-15 pages.

Also performs heuristic pre-filtering for "initial" criteria sections:
  Layer 1 of the two-layer initial-only strategy.
"""

import re
import logging

import pdfplumber

logger = logging.getLogger(__name__)

MAX_PAGES = 15
MAX_CHARS = 30_000


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF file, capped at MAX_PAGES pages and MAX_CHARS characters."""
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        extract_count = min(page_count, MAX_PAGES)

        if page_count > MAX_PAGES:
            logger.warning(
                "PDF has %d pages, extracting first %d only: %s",
                page_count, MAX_PAGES, pdf_path,
            )

        for page in pdf.pages[:extract_count]:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    full_text = "\n\n".join(pages_text)

    if len(full_text) > MAX_CHARS:
        logger.warning(
            "Extracted text is %d chars, truncating to %d: %s",
            len(full_text), MAX_CHARS, pdf_path,
        )
        full_text = full_text[:MAX_CHARS]

    return full_text


def extract_initial_section(full_text: str) -> str:
    """
    Heuristic pre-filter (Layer 1 of initial-only strategy).

    Scans for section headers that distinguish "Initial" from "Continuation"
    criteria. If found, returns only the initial section. If no clear
    distinction exists, returns the full text and lets the LLM handle it
    (Layer 2).

    Common header patterns in Oscar guidelines:
      - "Initial Authorization Criteria"
      - "Initial Criteria"
      - "Continuation of Therapy Criteria"
      - "Continuation/Renewal Criteria"
    """
    initial_patterns = [
        r"(?i)(initial\s+authorization\s+criteria)",
        r"(?i)(initial\s+criteria)",
        r"(?i)(initial\s+medical\s+necessity\s+criteria)",
        r"(?i)(criteria\s+for\s+initial\s+authorization)",
    ]
    continuation_patterns = [
        r"(?i)(continuation\s+of\s+therapy\s+criteria)",
        r"(?i)(continuation\s*/?renewal\s+criteria)",
        r"(?i)(continuation\s+criteria)",
        r"(?i)(reauthorization\s+criteria)",
        r"(?i)(renewal\s+criteria)",
    ]

    # Find the start of initial section
    initial_start = None
    for pattern in initial_patterns:
        match = re.search(pattern, full_text)
        if match:
            initial_start = match.start()
            logger.info("Found initial criteria header at char %d", initial_start)
            break

    # Find the start of continuation section
    continuation_start = None
    for pattern in continuation_patterns:
        match = re.search(pattern, full_text)
        if match:
            continuation_start = match.start()
            logger.info("Found continuation criteria header at char %d", continuation_start)
            break

    if initial_start is not None and continuation_start is not None:
        if initial_start < continuation_start:
            section = full_text[initial_start:continuation_start].strip()
            logger.info(
                "Extracted initial section: %d chars (from %d to %d)",
                len(section), initial_start, continuation_start,
            )
            return section

    if initial_start is not None:
        section = full_text[initial_start:].strip()
        logger.info("Extracted initial section from header to end: %d chars", len(section))
        return section

    logger.info("No initial/continuation headers found — using full text for LLM")
    return full_text
