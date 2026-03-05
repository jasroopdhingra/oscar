#!/usr/bin/env python3
"""
CLI runner for the full pipeline: discover → download → structure.

Usage:
    python run_pipeline.py              # Run all steps
    python run_pipeline.py discover     # Only discover
    python run_pipeline.py download     # Only download
    python run_pipeline.py structure    # Only structure
"""

import sys
import os
import logging

# Add parent dir so we can import app modules when running from backend/
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")

from app.database import init_db, SessionLocal
from app.services.scraper import discover_pdfs
from app.services.downloader import download_all_pdfs
from app.services.structurer import structure_policies


def main():
    init_db()
    db = SessionLocal()

    steps = sys.argv[1:] if len(sys.argv) > 1 else ["discover", "download", "structure"]

    try:
        if "discover" in steps:
            logger.info("=== STEP 1: PDF Discovery ===")
            count = discover_pdfs(db)
            logger.info("Discovery done: %d new policies", count)

        if "download" in steps:
            logger.info("=== STEP 2: PDF Download ===")
            count = download_all_pdfs(db)
            logger.info("Download done: %d successful", count)

        if "structure" in steps:
            logger.info("=== STEP 3: LLM Structuring ===")
            count = structure_policies(db)
            logger.info("Structuring done: %d successful", count)

        logger.info("=== Pipeline complete ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
