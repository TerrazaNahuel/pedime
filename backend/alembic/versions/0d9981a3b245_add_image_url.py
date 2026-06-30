"""add_image_url

Revision ID: 0d9981a3b245
Revises: 034c64c3c71d
Create Date: 2026-06-18 14:36:40.655181

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0d9981a3b245'
down_revision: str | None = '034c64c3c71d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_url")
