"""kb_search_vector_wo27

Adds PostgreSQL full-text `search_vector` column and GIN index (WO-27).
SQLite dev databases skip this migration body.

Revision ID: a7c3f8e2d901
Revises: 461a0e5c3080
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c3f8e2d901"
down_revision: Union[str, Sequence[str], None] = "461a0e5c3080"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        sa.text(
            """
            ALTER TABLE kb_article ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('english', title || ' ' || coalesce(content, ''))
            ) STORED
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_kbarticle_search_vector ON kb_article USING GIN (search_vector)"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(sa.text("DROP INDEX IF EXISTS ix_kbarticle_search_vector"))
    op.drop_column("kb_article", "search_vector")
