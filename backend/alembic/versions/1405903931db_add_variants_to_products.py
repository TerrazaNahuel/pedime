"""add variants to products

Revision ID: 1405903931db
Revises: c59174683330
Create Date: 2026-07-06 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1405903931db"
down_revision: str | None = "c59174683330"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("variants", sa.Text(), server_default="", nullable=False))


def downgrade() -> None:
    op.drop_column("products", "variants")
