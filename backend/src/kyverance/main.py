from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kyverance.api.routes import health, me
from kyverance.config import get_settings

# Ensure identity/audit metadata is registered for Alembic and create_all.
import kyverance.audit.models  # noqa: F401
import kyverance.identity.models  # noqa: F401


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(me.router, prefix="/api/v1")
    return app


app = create_app()


def run() -> None:
    uvicorn.run("kyverance.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
