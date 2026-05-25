"""Append-only audit logger.

Every grading and every review decision writes a row here, stamped with the
rubric / prompt / model versions in effect at the time. This is what gives
the brief's "Traceability for all grading decisions" non-functional
requirement actual teeth.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .config import settings
from .db import AuditLog


def log_event(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_id: int | None = None,
    before: dict | None = None,
    after: dict | None = None,
    rubric_version: str | None = None,
) -> AuditLog:
    """Write one audit row. Caller is responsible for db.commit()."""
    row = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        before=before,
        after=after,
        rubric_version=rubric_version,
        prompt_version=settings.prompt_version,
        model_version=settings.grader_model,
    )
    db.add(row)
    return row
