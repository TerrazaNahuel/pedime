"""add_fk_indexes

Revision ID: ddacf23d05d2
Revises: a73ca165b91e
Create Date: 2026-06-25 10:17:53.717422

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ddacf23d05d2'
down_revision: str | None = 'a73ca165b91e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_categories_store_id", "categories", ["store_id"])
    op.create_index("ix_products_store_id", "products", ["store_id"])
    op.create_index("ix_products_category_id", "products", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_products_category_id")
    op.drop_index("ix_products_store_id")
    op.drop_index("ix_categories_store_id")
