from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel


# --- Criteria tree schema (matches oscar.json) ---

class RuleNode(BaseModel):
    rule_id: str
    rule_text: str
    operator: Optional[Literal["AND", "OR"]] = None
    rules: Optional[list[RuleNode]] = None


class CriteriaTree(BaseModel):
    title: str
    insurance_name: str
    rules: RuleNode


# --- API response schemas ---

class PolicyOut(BaseModel):
    id: int
    title: str
    pdf_url: str
    source_page_url: str
    discovered_at: datetime
    has_structured_tree: bool = False
    download_status: Optional[str] = None

    model_config = {"from_attributes": True}


class DownloadOut(BaseModel):
    id: int
    policy_id: int
    stored_location: Optional[str]
    downloaded_at: datetime
    http_status: Optional[int]
    error: Optional[str]

    model_config = {"from_attributes": True}


class StructuredPolicyOut(BaseModel):
    id: int
    policy_id: int
    structured_json: Optional[dict]
    structured_at: datetime
    llm_metadata: Optional[dict]
    validation_error: Optional[str]

    model_config = {"from_attributes": True}


class PolicyDetailOut(BaseModel):
    id: int
    title: str
    pdf_url: str
    source_page_url: str
    discovered_at: datetime
    downloads: list[DownloadOut] = []
    structured_policies: list[StructuredPolicyOut] = []

    model_config = {"from_attributes": True}


class PipelineStatusOut(BaseModel):
    status: str
    message: str
    count: int = 0
