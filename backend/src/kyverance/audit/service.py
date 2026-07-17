from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kyverance.audit.models import AuditEvent


def record_audit_event(
    db: Session,
    *,
    actor_subject: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    target_subject: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an immutable audit event. Caller owns the transaction commit."""
    event = AuditEvent(
        actor_subject=actor_subject,
        target_subject=target_subject,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata,
    )
    db.add(event)
    db.flush()
    return event
