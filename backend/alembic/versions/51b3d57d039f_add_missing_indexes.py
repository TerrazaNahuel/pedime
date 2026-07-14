"""add_missing_indexes

Revision ID: 51b3d57d039f
Revises: 5fd7dd6e38f0
Create Date: 2026-07-14 11:00:10.662139

"""
from collections.abc import Sequence

from alembic import op

revision: str = '51b3d57d039f'
down_revision: str | None = '5fd7dd6e38f0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(op.f('ix_categories_store_id'), 'categories', ['store_id'], unique=False)
    op.create_index(op.f('ix_products_category_id'), 'products', ['category_id'], unique=False)
    op.create_index(op.f('ix_products_sort_order'), 'products', ['sort_order'], unique=False)
    op.create_index(op.f('ix_products_store_id'), 'products', ['store_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_products_store_id'), table_name='products')
    op.drop_index(op.f('ix_products_sort_order'), table_name='products')
    op.drop_index(op.f('ix_products_category_id'), table_name='products')
    op.drop_index(op.f('ix_categories_store_id'), table_name='categories')
