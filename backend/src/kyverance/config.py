from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Kyverance Simplified API"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+psycopg://kyverance:kyverance@localhost:5432/kyverance"
    redis_url: str = "redis://localhost:6379/0"

    dev_auth: bool = True
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_web_client_id: str = ""
    entra_audience: str = ""
    entra_issuer: str = ""

    key_vault_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def refresh_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
