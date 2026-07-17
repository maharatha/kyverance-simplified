from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jose import JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from kyverance.auth.jwks import signing_key_for_token
from kyverance.auth.models import DEV_SUBJECT, AuthenticatedSubject
from kyverance.config import Settings, get_settings
from kyverance.db.session import get_db
from kyverance.identity.service import bootstrap_user_on_sign_in

_bearer = HTTPBearer(auto_error=False)

_OID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_directory_oid(value: str | None) -> bool:
    return bool(value and _OID_RE.match(value.strip()))


def _truncate(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed[:max_len] if trimmed else None


def _sanitize_name(value: str | None) -> str | None:
    trimmed = _truncate(value, 256)
    if not trimmed:
        return None
    if trimmed.lower() in {"unknown", "n/a", "anonymous"}:
        return None
    return trimmed


def _token_audiences(payload: dict) -> list[str]:
    aud = payload.get("aud")
    if isinstance(aud, list):
        return [str(value) for value in aud if value]
    if isinstance(aud, str) and aud:
        return [aud]
    return []


def _validate_token_claims(payload: dict, settings: Settings) -> None:
    iss = str(payload.get("iss", "")).rstrip("/")
    allowed_issuers = {value.rstrip("/") for value in settings.entra_issuer_list}
    if allowed_issuers and iss not in allowed_issuers:
        raise JWTError("Invalid issuer")

    allowed_audiences = set(settings.entra_audience_list)
    token_audiences = _token_audiences(payload)
    if allowed_audiences and not any(aud in allowed_audiences for aud in token_audiences):
        raise JWTError("Invalid audience")


def decode_entra_token(token: str, settings: Settings) -> dict:
    if not settings.entra_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Entra auth is not configured",
        )
    token = token.strip()
    try:
        key = signing_key_for_token(token, settings.entra_jwks_urls)
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_at_hash": False, "verify_iss": False, "verify_aud": False},
        )
        _validate_token_claims(payload, settings)
        return payload
    except JWTError as exc:
        detail = f"Invalid or expired token: {exc}" if settings.debug else "Invalid or expired token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        ) from exc
    except (ValueError, httpx.HTTPError) as exc:
        detail = f"Token validation failed: {exc}" if settings.debug else "Token validation failed"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        ) from exc
    except Exception as exc:  # noqa: BLE001
        detail = f"Auth error: {type(exc).__name__}" if settings.debug else "Authentication failed"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        ) from exc


def _claims_to_subject(payload: dict) -> AuthenticatedSubject:
    subject = payload.get("oid") or payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    idp = payload.get("idp") or payload.get("identityProvider")
    if isinstance(idp, str) and idp.startswith("http"):
        idp = idp.rstrip("/").split("/")[-1]

    given_name = _sanitize_name(payload.get("given_name"))
    family_name = _sanitize_name(payload.get("family_name"))
    name = _sanitize_name(payload.get("name"))
    if not given_name and not family_name and name:
        parts = name.split(" ", 1)
        given_name = _sanitize_name(parts[0])
        family_name = _sanitize_name(parts[1]) if len(parts) > 1 else None

    return AuthenticatedSubject(
        subject=str(subject),
        display_name=_sanitize_name(name) or _display_from_parts(given_name, family_name),
        given_name=given_name,
        family_name=family_name,
        idp=_truncate(idp, 64) if isinstance(idp, str) else None,
    )


def _display_from_parts(given_name: str | None, family_name: str | None) -> str | None:
    parts = [p for p in (given_name, family_name) if p]
    return " ".join(parts) if parts else None


def _prefer_directory_subject(
    access_subject: AuthenticatedSubject,
    id_token: str | None,
    settings: Settings,
) -> AuthenticatedSubject:
    if not id_token:
        return access_subject
    try:
        payload = decode_entra_token(id_token.strip(), settings)
        supplemental = _claims_to_subject(payload)
    except HTTPException:
        return access_subject

    if _is_directory_oid(access_subject.subject):
        subject = access_subject.subject
    elif _is_directory_oid(supplemental.subject):
        subject = supplemental.subject
    else:
        subject = access_subject.subject

    return AuthenticatedSubject(
        subject=subject,
        display_name=access_subject.display_name or supplemental.display_name,
        given_name=access_subject.given_name or supplemental.given_name,
        family_name=access_subject.family_name or supplemental.family_name,
        idp=access_subject.idp or supplemental.idp,
    )


def _bootstrap_subject(db: Session, subject: AuthenticatedSubject, email: str | None = None) -> AuthenticatedSubject:
    user, roles, _created = bootstrap_user_on_sign_in(
        db,
        entra_oid=subject.subject,
        email=email,
        given_name=subject.given_name,
        family_name=subject.family_name,
        display_name=subject.display_name,
        idp=subject.idp,
        actor_subject=subject.subject,
    )
    return AuthenticatedSubject(
        subject=subject.subject,
        user_id=str(user.id),
        display_name=user.display_name or subject.display_name,
        given_name=user.given_name or subject.given_name,
        family_name=user.family_name or subject.family_name,
        idp=user.idp or subject.idp,
        roles=roles,
        is_dev=subject.is_dev,
    )


def _email_from_claims(payload: dict) -> str | None:
    for key in ("email", "preferred_username", "upn"):
        value = payload.get(key)
        if isinstance(value, str) and "@" in value and not value.lower().endswith(".onmicrosoft.com"):
            return _truncate(value, 256)
    for key in ("email", "preferred_username", "upn"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _truncate(value, 256)
    return None


def require_authenticated(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_id_token: Annotated[str | None, Header(alias="X-Id-Token")] = None,
) -> AuthenticatedSubject:
    """Require an authenticated actor. Deny-by-default with a neutral 401."""
    if credentials is None:
        if settings.development_identity_enabled:
            return _bootstrap_subject(db, DEV_SUBJECT, email="dev@kyverance.local")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = decode_entra_token(credentials.credentials, settings)
        subject = _prefer_directory_subject(_claims_to_subject(payload), x_id_token, settings)
        return _bootstrap_subject(db, subject, email=_email_from_claims(payload))
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        detail = "Database error during authentication" if not settings.debug else str(exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail) from exc


def get_optional_subject(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_id_token: Annotated[str | None, Header(alias="X-Id-Token")] = None,
) -> AuthenticatedSubject | None:
    if credentials is None:
        if settings.development_identity_enabled:
            return _bootstrap_subject(db, DEV_SUBJECT, email="dev@kyverance.local")
        return None
    return require_authenticated(settings, db, credentials, x_id_token)
