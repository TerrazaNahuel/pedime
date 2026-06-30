"""drop_orders

Revision ID: a1b2c3d4e5f6
Revises: cf3b250b3535
Create Date: 2026-06-18 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'cf3b250b3535'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table('order_items')
    op.drop_table('orders')


def downgrade() -> None:
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('customer_name', sa.String(100), nullable=True),
        sa.Column('customer_phone', sa.String(50), nullable=True),
        sa.Column('delivery_available', sa.Boolean(), nullable=True),
        sa.Column('delivery_address', sa.String(500), nullable=True),
        sa.Column('delivery_reference', sa.String(500), nullable=True),
        sa.Column('payment_method', sa.String(20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=True),
        sa.Column('delivery_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('total', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_table('order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_order_items_id', 'order_items', ['id'])
