from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Kyverance Simplified API"
    app_version: str = "0.1.0"
    debug: bool = False
    # local | test | staging | production — controls development-identity eligibility
    app_env: str = "local"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+psycopg://kyverance:kyverance@localhost:5432/kyverance"
    redis_url: str = "redis://localhost:6379/0"

    # Explicit server-owned flag. Never enabled by a request header.
    # Effective only when APP_ENV is local or test (see development_identity_enabled).
    dev_auth: bool = True
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_web_client_id: str = ""
    entra_audience: str = ""
    entra_issuer: str = ""
    entra_jwks_url: str = ""
    default_role_key: str = "member"

    key_vault_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_local_or_test(self) -> bool:
        return self.app_env.strip().lower() in {"local", "test"}

    @property
    def development_identity_enabled(self) -> bool:
        """True only for explicit local/test development identity.

        A browser caller cannot enable this: it is derived solely from server
        environment settings, never from request headers or query parameters.
        """
        return bool(self.dev_auth) and self.is_local_or_test

    @property
    def entra_audience_list(self) -> list[str]:
        values = [v.strip() for v in self.entra_audience.split(",") if v.strip()]
        if self.entra_client_id and self.entra_client_id not in values:
            values.append(self.entra_client_id)
        return values

    @property
    def entra_issuer_list(self) -> list[str]:
        if self.entra_issuer.strip():
            return [self.entra_issuer.strip().rstrip("/")]
        if self.entra_tenant_id.strip():
            tenant = self.entra_tenant_id.strip()
            return [
                f"https://{tenant}.ciamlogin.com/{tenant}/v2.0",
                f"https://login.microsoftonline.com/{tenant}/v2.0",
            ]
        return []

    @property
    def entra_jwks_urls(self) -> list[str]:
        if self.entra_jwks_url.strip():
            return [self.entra_jwks_url.strip()]
        urls: list[str] = []
        for issuer in self.entra_issuer_list:
            base = issuer.rstrip("/")
            if base.endswith("/v2.0"):
                urls.append(f"{base}/discovery/v2.0/keys")
            else:
                urls.append(f"{base}/discovery/v2.0/keys")
        return urls

    @property
    def entra_configured(self) -> bool:
        return bool(self.entra_audience_list and self.entra_issuer_list and self.entra_jwks_urls)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def refresh_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
