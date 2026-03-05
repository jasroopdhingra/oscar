import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import PipelineStatusOut
from app.services.scraper import discover_pdfs
from app.services.downloader import download_all_pdfs
from app.services.structurer import structure_policies

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/discover", response_model=PipelineStatusOut)
def run_discovery(db: Session = Depends(get_db)):
    logger.info("Starting PDF discovery pipeline")
    count = discover_pdfs(db)
    return PipelineStatusOut(
        status="completed",
        message=f"Discovered {count} policies",
        count=count,
    )


@router.post("/download", response_model=PipelineStatusOut)
def run_downloads(db: Session = Depends(get_db)):
    logger.info("Starting PDF download pipeline")
    count = download_all_pdfs(db)
    return PipelineStatusOut(
        status="completed",
        message=f"Downloaded {count} PDFs",
        count=count,
    )


@router.post("/structure", response_model=PipelineStatusOut)
def run_structuring(db: Session = Depends(get_db)):
    logger.info("Starting structuring pipeline")
    count = structure_policies(db)
    return PipelineStatusOut(
        status="completed",
        message=f"Structured {count} policies",
        count=count,
    )
