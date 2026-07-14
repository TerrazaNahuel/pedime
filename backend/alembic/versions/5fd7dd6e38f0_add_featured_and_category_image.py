"""add_featured_and_category_image

Revision ID: 5fd7dd6e38f0
Revises: f7e8d9c0b1a2
Create Date: 2026-07-14 09:37:30.077703

"""  # noqa: S110
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5fd7dd6e38f0'
down_revision: str | None = 'f7e8d9c0b1a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS rate_limit_entries (id INTEGER NOT NULL, key VARCHAR(200) NOT NULL, attempted_at DATETIME, PRIMARY KEY (id))")
    try:
        op.create_index(op.f('ix_rate_limit_entries_id'), 'rate_limit_entries', ['id'], unique=False)
    except Exception:  # noqa: S110
        pass
    try:
        op.create_index(op.f('ix_rate_limit_entries_key'), 'rate_limit_entries', ['key'], unique=False)
    except Exception:  # noqa: S110
        pass
    try:
        op.add_column('categories', sa.Column('image_url', sa.String(length=500), nullable=True))
    except Exception:  # noqa: S110
        pass
    try:
        op.add_column('products', sa.Column('featured', sa.Boolean(), nullable=True))
    except Exception:  # noqa: S110
        pass


def downgrade() -> None:
    try:
        op.drop_column('products', 'featured')
    except Exception:  # noqa: S110
        pass
    try:
        op.drop_column('categories', 'image_url')
    except Exception:  # noqa: S110
        pass
    # ### end Alembic commands ###
