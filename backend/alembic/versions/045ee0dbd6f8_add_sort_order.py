"""add_sort_order

Revision ID: 045ee0dbd6f8
Revises: 0d9981a3b245
Create Date: 2026-06-18 14:39:50.188836

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '045ee0dbd6f8'
down_revision: str | None = '0d9981a3b245'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("sort_order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "sort_order")
