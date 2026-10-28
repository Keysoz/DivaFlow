"""Audit trail for sensitive actions (TASK-PUB-01, AGENTS.md section 6)."""

from fastapi import Request
from sqlalchemy.orm import Session

from cloud_api.models import AuditLog


def record_audit(
    db: Session,
    *,
    actor: str | None,
    action: str,
    target: str | None = None,
    result: str = "ok",
    detail: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        target=target,
        result=result,
        detail=detail,
        ip=request.client.host if request and request.client else None,
    )
    db.add(entry)
    return entry
