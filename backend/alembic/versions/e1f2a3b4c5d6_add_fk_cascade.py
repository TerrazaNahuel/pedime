"""Agrega ON DELETE CASCADE en todas las FKs (PostgreSQL)

SQLite no soporta ALTER de FKs y no las enforce por defecto,
así que el upgrade es no-op en SQLite.

Revision ID: e1f2a3b4c5d6
Revises: ddacf23d05d2
Create Date: 2026-06-25 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "ddacf23d05d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FK_NAMES = [
    ("categories", "categories_store_id_fkey", "stores", ["store_id"]),
    ("products", "products_store_id_fkey", "stores", ["store_id"]),
    ("products", "products_category_id_fkey", "categories", ["category_id"]),
]


def upgrade():
    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        return

    for table, fk_name, ref, columns in FK_NAMES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(fk_name, ref, columns, ["id"], ondelete="CASCADE")


def downgrade():
    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        return

    for table, fk_name, ref, columns in FK_NAMES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(fk_name, ref, columns, ["id"])
