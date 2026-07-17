from __future__ import annotations

import base64
import time
from typing import Any

import httpx
from jose import jwt as jose_jwt
from jose.backends.base import Key
from jose.exceptions import JWKError

_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 3600


def clear_jwks_cache() -> None:
    _JWKS_CACHE.clear()


def _cache_key(jwks_url: str) -> str:
    return jwks_url.rstrip("/")


def fetch_jwks(jwks_url: str) -> dict[str, Any]:
    key = _cache_key(jwks_url)
    now = time.time()
    cached = _JWKS_CACHE.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    response = httpx.get(jwks_url, timeout=10.0)
    response.raise_for_status()
    jwks = response.json()
    _JWKS_CACHE[key] = (now, jwks)
    return jwks


def _key_from_jwk_data(key_data: dict[str, Any]) -> Key:
    try:
        from jose import jwk

        return jwk.construct(key_data)
    except JWKError:
        pass

    x5c = key_data.get("x5c")
    if x5c and key_data.get("kty") == "RSA":
        from cryptography.hazmat.backends import default_backend
        from cryptography.x509 import load_der_x509_certificate
        from jose.backends.cryptography_backend import CryptographyRSAKey

        cert = load_der_x509_certificate(base64.b64decode(x5c[0]), default_backend())
        return CryptographyRSAKey(cert.public_key(), "RS256")

    raise ValueError(f"Unable to build signing key for kid={key_data.get('kid')}")


def signing_key_for_token(token: str, jwks_urls: str | list[str]) -> Key:
    header = jose_jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise ValueError("Token header missing kid")

    urls = [jwks_urls] if isinstance(jwks_urls, str) else list(jwks_urls)
    last_error: Exception | None = None
    for jwks_url in urls:
        try:
            jwks = fetch_jwks(jwks_url)
            for key_data in jwks.get("keys", []):
                if key_data.get("kid") == kid:
                    return _key_from_jwk_data(key_data)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise ValueError(f"No matching JWK for kid={kid}") from last_error
    raise ValueError(f"No matching JWK for kid={kid}")
