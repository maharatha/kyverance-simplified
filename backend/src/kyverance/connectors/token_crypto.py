"""Local Fernet encryption for Plaid access tokens (token-reference-ready)."""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from kyverance.config import Settings
from kyverance.connectors.constants import LOCAL_ENCRYPTION_KID

logger = logging.getLogger(__name__)

# Deterministic local-only material — never use outside APP_ENV local/test.
_LOCAL_FALLBACK_MATERIAL = b"kyverance-simplified-local-plaid-token-key-v1"


def _fernet_from_key_material(raw: bytes) -> Fernet:
    digest = hashlib.sha256(raw).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def resolve_token_fernet(settings: Settings) -> tuple[Fernet, str]:
    """Return (Fernet, encryption_kid) for sealing Plaid access tokens."""
    configured = (settings.plaid_token_encryption_key or "").strip()
    if configured:
        try:
            # Accept a Fernet key directly, or derive from an arbitrary secret string.
            if len(configured) == 44 and configured.endswith("="):
                return Fernet(configured.encode("utf-8")), LOCAL_ENCRYPTION_KID
            return _fernet_from_key_material(configured.encode("utf-8")), LOCAL_ENCRYPTION_KID
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid PLAID_TOKEN_ENCRYPTION_KEY",
            ) from exc

    if settings.is_local_or_test:
        return _fernet_from_key_material(_LOCAL_FALLBACK_MATERIAL), LOCAL_ENCRYPTION_KID

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Plaid token encryption is not configured",
    )


def encrypt_access_token(plaintext: str, settings: Settings) -> tuple[str, str]:
    fernet, kid = resolve_token_fernet(settings)
    ciphertext = fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return ciphertext, kid


def decrypt_access_token(ciphertext: str, settings: Settings) -> str:
    fernet, _kid = resolve_token_fernet(settings)
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        logger.info("Plaid token decrypt failed (invalid ciphertext or key)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored connection token could not be decrypted",
        ) from exc
