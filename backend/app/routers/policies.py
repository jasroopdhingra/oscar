import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Policy, StructuredPolicy, Download
from app.schemas import PolicyOut, PolicyDetailOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db)):
    policies = db.query(Policy).order_by(Policy.title).all()
    result = []
    for p in policies:
        has_tree = db.query(StructuredPolicy).filter(
            StructuredPolicy.policy_id == p.id,
            StructuredPolicy.structured_json.isnot(None),
            StructuredPolicy.validation_error.is_(None),
        ).first() is not None

        latest_dl = db.query(Download).filter(
            Download.policy_id == p.id
        ).order_by(Download.downloaded_at.desc()).first()

        dl_status = None
        if latest_dl:
            dl_status = "success" if latest_dl.error is None else "failed"

        result.append(PolicyOut(
            id=p.id,
            title=p.title,
            pdf_url=p.pdf_url,
            source_page_url=p.source_page_url,
            discovered_at=p.discovered_at,
            has_structured_tree=has_tree,
            download_status=dl_status,
        ))
    return result


@router.get("/policies/{policy_id}", response_model=PolicyDetailOut)
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
