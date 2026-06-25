"""add_opening_hours

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-18 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stores', sa.Column('opening_time', sa.String(5), nullable=True))
    op.add_column('stores', sa.Column('closing_time', sa.String(5), nullable=True))


def downgrade() -> None:
    op.drop_column('stores', 'closing_time')
    op.drop_column('stores', 'opening_time')
