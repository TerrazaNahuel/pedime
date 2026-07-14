"""Add working_days column to stores

Revision ID: f7e8d9c0b1a2
Revises: e1f2a3b4c5d6
Create Date: 2026-07-13 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7e8d9c0b1a2"
down_revision: str | None = "1405903931db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.add_column("stores", sa.Column("working_days", sa.String(20), nullable=False, server_default="1,2,3,4,5,6,7"))


def downgrade():
    op.drop_column("stores", "working_days")
