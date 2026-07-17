from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kyverance.audit.service import record_audit_event
from kyverance.identity.models import ConsentRecord, RoleGrant, User
from kyverance.identity.roles import DEFAULT_ROLE_KEY


def _display_name(given_name: str | None, family_name: str | None, fallback: str | None = None) -> str | None:
    parts = [p for p in (given_name, family_name) if p]
    if parts:
        return " ".join(parts)
    return fallback


def bootstrap_user_on_sign_in(
    db: Session,
    *,
    entra_oid: str,
    email: str | None = None,
    given_name: str | None = None,
    family_name: str | None = None,
    display_name: str | None = None,
    idp: str | None = None,
    actor_subject: str | None = None,
) -> tuple[User, frozenset[str], bool]:
    """Create or update the local user and ensure exactly one default Member grant.

    Returns (user, role_keys, created_new_user).
    Idempotent under concurrent retries via unique constraints + savepoints.
    """
    now = datetime.now(UTC)
    actor = actor_subject or entra_oid
    created_new_user = False

    user = db.query(User).filter(User.entra_oid == entra_oid).one_or_none()
    if user is None:
        try:
            with db.begin_nested():
                user = User(
                    entra_oid=entra_oid,
                    email=email,
                    given_name=given_name,
                    family_name=family_name,
                    display_name=_display_name(given_name, family_name, display_name),
                    idp=idp,
                    last_sign_in_at=now,
                )
                db.add(user)
                db.flush()
                created_new_user = True
                record_audit_event(
                    db,
                    actor_subject=actor,
                    target_subject=entra_oid,
                    action="user.bootstrap",
                    resource_type="user",
                    resource_id=str(user.id),
                    metadata={"idp": idp} if idp else None,
                )
        except IntegrityError:
            user = db.query(User).filter(User.entra_oid == entra_oid).one()
            created_new_user = False
    else:
        if email:
            user.email = email
        if given_name:
            user.given_name = given_name
        if family_name:
            user.family_name = family_name
        resolved_name = _display_name(user.given_name, user.family_name, display_name)
        if resolved_name:
            user.display_name = resolved_name
        if idp:
            user.idp = idp
        user.last_sign_in_at = now
        db.flush()

    roles = _ensure_default_member_grant(db, user=user, actor_subject=actor)
    db.commit()
    db.refresh(user)
    return user, roles, created_new_user


def _ensure_default_member_grant(db: Session, *, user: User, actor_subject: str) -> frozenset[str]:
    existing = (
        db.query(RoleGrant)
        .filter(RoleGrant.user_id == user.id, RoleGrant.role_key == DEFAULT_ROLE_KEY)
        .one_or_none()
    )
    if existing is None:
        try:
            with db.begin_nested():
                db.add(
                    RoleGrant(
                        user_id=user.id,
                        role_key=DEFAULT_ROLE_KEY,
                        granted_by_subject="system",
                    )
                )
                db.flush()
                record_audit_event(
                    db,
                    actor_subject=actor_subject,
                    target_subject=user.entra_oid,
                    action="role_grant.create",
                    resource_type="role_grant",
                    resource_id=DEFAULT_ROLE_KEY,
                    metadata={"role_key": DEFAULT_ROLE_KEY, "default": True},
                )
        except IntegrityError:
            pass

    grants = db.query(RoleGrant.role_key).filter(RoleGrant.user_id == user.id).all()
    return frozenset(row[0] for row in grants)


def grant_role(
    db: Session,
    *,
    user: User,
    role_key: str,
    actor_subject: str,
) -> RoleGrant:
    existing = (
        db.query(RoleGrant)
        .filter(RoleGrant.user_id == user.id, RoleGrant.role_key == role_key)
        .one_or_none()
    )
    if existing is not None:
        return existing

    grant = RoleGrant(user_id=user.id, role_key=role_key, granted_by_subject=actor_subject)
    db.add(grant)
    db.flush()
    record_audit_event(
        db,
        actor_subject=actor_subject,
        target_subject=user.entra_oid,
        action="role_grant.create",
        resource_type="role_grant",
        resource_id=role_key,
        metadata={"role_key": role_key},
    )
    db.commit()
    db.refresh(grant)
    return grant


def record_consent(
    db: Session,
    *,
    user: User,
    consent_type: str,
    granted: bool,
    actor_subject: str,
    metadata: dict | None = None,
) -> ConsentRecord:
    record = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user.id, ConsentRecord.consent_type == consent_type)
        .one_or_none()
    )
    if record is None:
        record = ConsentRecord(
            user_id=user.id,
            consent_type=consent_type,
            granted=granted,
            metadata_json=metadata,
            recorded_by_subject=actor_subject,
        )
        db.add(record)
        action = "consent.create"
    else:
        record.granted = granted
        record.metadata_json = metadata
        record.recorded_by_subject = actor_subject
        action = "consent.update"

    db.flush()
    record_audit_event(
        db,
        actor_subject=actor_subject,
        target_subject=user.entra_oid,
        action=action,
        resource_type="consent",
        resource_id=consent_type,
        metadata={"consent_type": consent_type, "granted": granted},
    )
    db.commit()
    db.refresh(record)
    return record


def load_role_keys(db: Session, user_id) -> frozenset[str]:
    rows = db.query(RoleGrant.role_key).filter(RoleGrant.user_id == user_id).all()
    return frozenset(row[0] for row in rows)
