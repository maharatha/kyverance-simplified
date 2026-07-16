from __future__ import annotations

from kyverance.db.session import Base, engine


def init_db() -> None:
    """Create tables from metadata (foundation scaffold; Alembic owns schema later)."""
    Base.metadata.create_all(bind=engine)
