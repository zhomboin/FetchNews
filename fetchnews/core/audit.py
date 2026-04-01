from __future__ import annotations

from sqlalchemy.orm import Session

from fetchnews.models import AuditLog, User



def record_audit_log(
    session: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    actor: User | None = None,
    detail: dict | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor.id if actor is not None else None,
        actor_username=actor.username if actor is not None else "system",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=detail or {},
    )
    session.add(audit_log)
    session.flush()
    return audit_log
