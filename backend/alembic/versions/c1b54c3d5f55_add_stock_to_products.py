"""add stock to products

Revision ID: c1b54c3d5f55
Revises: e1f2a3b4c5d6
Create Date: 2026-06-25 21:41:28.352718

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c1b54c3d5f55'
down_revision: str | None = 'e1f2a3b4c5d6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('products', sa.Column('stock', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('products', 'stock')
