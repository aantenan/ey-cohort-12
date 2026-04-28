"""Baseline migration — no tables yet (WO-2 scaffolding).

Revision ID: 001_baseline
Revises:
Create Date: 2026-04-28

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
