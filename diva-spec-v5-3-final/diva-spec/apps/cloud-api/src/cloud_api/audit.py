"""Audit trail for sensitive actions (TASK-PUB-01, AGENTS.md section 6)."""

from fastapi import Request
from sqlalchemy.orm import Session

from cloud_api.config import get_settings
from cloud_api.models import AuditLog

settings = get_settings()


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    peer = request.client.host
    if peer in settings.trusted_proxies:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


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
        ip=_client_ip(request),
    )
    db.add(entry)
    return entry
