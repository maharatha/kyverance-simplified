"""Audit module — immutable security/business audit events."""

from kyverance.audit.models import AuditEvent
from kyverance.audit.service import record_audit_event

__all__ = ["AuditEvent", "record_audit_event"]
