"""add_primary_color_logo

Revision ID: cf3b250b3535
Revises: 045ee0dbd6f8
Create Date: 2026-06-18 14:41:17.193922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf3b250b3535'
down_revision: Union[str, None] = '045ee0dbd6f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("primary_color", sa.String(7), nullable=True))
    op.add_column("stores", sa.Column("logo_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "logo_url")
    op.drop_column("stores", "primary_color")
