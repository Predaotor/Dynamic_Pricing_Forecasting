"""Add unique constraint to sales_daily product_id and date

Revision ID: f1df74e93c99
Revises: f67bef8cc643
Create Date: 2025-08-24 01:50:40.990034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1df74e93c99'
down_revision: Union[str, None] = 'f67bef8cc643'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_unique_constraint(
        "uq_sales_daily_product_date",
        "sales_daily",
        ["product_id", "date"]
    )

def downgrade():
    op.drop_constraint(
        "uq_sales_daily_product_date",
        "sales_daily",
        type_="unique"
    )
