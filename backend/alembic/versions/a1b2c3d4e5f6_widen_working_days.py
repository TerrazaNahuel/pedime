"""widen_working_days column to String(50)

Revision ID: a1b2c3d4e5f6
Revises: 51b3d57d039f
Create Date: 2026-07-17 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "51b3d57d039f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("stores", "working_days", existing_type=sa.String(20), type_=sa.String(50), existing_nullable=False, existing_server_default="1,2,3,4,5,6,7")


def downgrade() -> None:
    op.alter_column("stores", "working_days", existing_type=sa.String(50), type_=sa.String(20), existing_nullable=False, existing_server_default="1,2,3,4,5,6,7")
