from __future__ import annotations

"""
LLM structuring service.

Takes extracted PDF text and uses Groq (Llama 3.3 70B) to produce a JSON
criteria tree matching the oscar.json schema.

Two-layer initial-only strategy:
  Layer 1: Heuristic text pre-filtering (in extractor.py)
  Layer 2: Explicit LLM prompt instruction to extract only initial criteria

Validation: Every LLM response is validated against the CriteriaTree Pydantic
model. Failures are stored in validation_error rather than silently dropped.
"""

import os
import json
import time
import logging
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Policy, Download, StructuredPolicy
from app.schemas import CriteriaTree
from app.services.extractor import extract_text, extract_initial_section

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"
STRUCTURING_DELAY = 3  # seconds between LLM calls (Groq free-tier rate limit)
MIN_POLICIES_TO_STRUCTURE = 10

SYSTEM_PROMPT = """You are a medical policy analyst. Your task is to extract medical necessity criteria from clinical guideline documents and structure them as a JSON decision tree.

You MUST respond with ONLY valid JSON matching this exact schema:

{
  "title": "<guideline title>",
  "insurance_name": "Oscar Health",
  "rules": {
    "rule_id": "1",
    "rule_text": "<root criterion description>",
    "operator": "AND" or "OR",
    "rules": [
      {
        "rule_id": "1.1",
        "rule_text": "<sub-criterion>",
        "operator": "AND" or "OR" (only if it has children),
        "rules": [...] (only if it has children)
      },
      {
        "rule_id": "1.2",
        "rule_text": "<leaf criterion>"
      }
    ]
  }
}

Rules:
- rule_id: hierarchical dot notation (1, 1.1, 1.2, 1.2.1, etc.)
- rule_text: the actual criterion text, concise but complete
- operator: ONLY "AND" or "OR", ONLY on non-leaf nodes that have children
- rules: array of child nodes, ONLY on non-leaf nodes
- Leaf nodes have ONLY rule_id and rule_text (no operator, no rules array)
- insurance_name is ALWAYS "Oscar Health"

CRITICAL: Extract ONLY the INITIAL authorization/medical necessity criteria.
Do NOT include:
- Continuation of therapy criteria
- Renewal/reauthorization criteria
- Exclusion criteria
- Appendices or references

If the document has both initial and continuation criteria, extract ONLY the initial criteria section."""


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )


def _structure_text(text: str, title: str) -> tuple[dict | None, str | None, dict]:
    """
    Send extracted text to Groq LLM and parse the response.
    Returns (structured_json, validation_error, llm_metadata).
    """
    client = _get_client()

    user_prompt = f"""Extract the INITIAL medical necessity criteria from this clinical guideline and structure them as a JSON decision tree.

Guideline title: {title}

Document text:
---
{text}
---

Respond with ONLY the JSON object. No markdown, no explanation."""

    llm_metadata = {"model": MODEL, "prompt_chars": len(user_prompt)}

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096,
        )
        raw_content = response.choices[0].message.content
        llm_metadata["completion_tokens"] = response.usage.completion_tokens
        llm_metadata["prompt_tokens"] = response.usage.prompt_tokens

    except Exception as e:
        logger.error("LLM API call failed: %s", e)
        return None, f"LLM API error: {e}", llm_metadata

    # Parse JSON
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("LLM returned invalid JSON: %s", e)
        return None, f"Invalid JSON: {e}", llm_metadata

    # Validate against Pydantic schema
    try:
        CriteriaTree.model_validate(parsed)
    except ValidationError as e:
        logger.error("Schema validation failed: %s", e)
        return parsed, f"Schema validation error: {e}", llm_metadata

    return parsed, None, llm_metadata


def structure_policies(db: Session, limit: int = MIN_POLICIES_TO_STRUCTURE) -> int:
    """
    Structure at least `limit` policies that have successful downloads
    but no structured output yet. Returns count of successfully structured.
    """
    # Find policies with downloads but no structured output
    already_structured_ids = (
        db.query(StructuredPolicy.policy_id)
        .filter(StructuredPolicy.structured_json.isnot(None))
        .all()
    )
    already_structured_ids = {row[0] for row in already_structured_ids}

    downloaded_policies = (
        db.query(Policy)
        .join(Download, Download.policy_id == Policy.id)
        .filter(
            Download.error.is_(None),
            Download.stored_location.isnot(None),
        )
        .all()
    )

    candidates = [p for p in downloaded_policies if p.id not in already_structured_ids]
    to_structure = candidates[:limit]

    logger.info(
        "Structuring %d policies (of %d candidates, %d already done)",
        len(to_structure), len(candidates), len(already_structured_ids),
    )

    success_count = 0
    for policy in to_structure:
        download = (
            db.query(Download)
            .filter(Download.policy_id == policy.id, Download.error.is_(None))
            .first()
        )
        if not download or not download.stored_location:
            continue

        logger.info("Structuring: %s", policy.title)

        # Layer 1: Extract text and pre-filter for initial criteria
        try:
            full_text = extract_text(download.stored_location)
            filtered_text = extract_initial_section(full_text)
        except Exception as e:
            logger.error("Text extraction failed for '%s': %s", policy.title, e)
            sp = StructuredPolicy(
                policy_id=policy.id,
                extracted_text=None,
                structured_json=None,
                structured_at=datetime.now(timezone.utc),
                llm_metadata={"error": "text_extraction_failed"},
                validation_error=str(e),
            )
            db.add(sp)
            db.commit()
            continue

        # Layer 2: LLM structuring with explicit initial-only instruction
        structured_json, validation_error, llm_metadata = _structure_text(
            filtered_text, policy.title
        )

        sp = StructuredPolicy(
            policy_id=policy.id,
            extracted_text=filtered_text[:50_000],  # cap stored text
            structured_json=structured_json,
            structured_at=datetime.now(timezone.utc),
            llm_metadata=llm_metadata,
            validation_error=validation_error,
        )
        db.add(sp)
        db.commit()

        if validation_error is None:
            success_count += 1
            logger.info("Successfully structured: %s", policy.title)
        else:
            logger.warning("Structured with errors: %s — %s", policy.title, validation_error)

        time.sleep(STRUCTURING_DELAY)

    logger.info("Structuring complete. %d/%d successful.", success_count, len(to_structure))
    return success_count
