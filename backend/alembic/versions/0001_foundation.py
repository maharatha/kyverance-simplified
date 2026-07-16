"""Foundation revision — empty schema baseline for Kyverance Simplified."""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "0001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Domain tables arrive in later tasks (SIM-01, ID-02, …).
    pass


def downgrade() -> None:
    pass
