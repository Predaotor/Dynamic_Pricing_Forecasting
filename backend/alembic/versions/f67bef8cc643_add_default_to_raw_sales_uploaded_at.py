"""Add default to raw_sales.uploaded_at

Revision ID: f67bef8cc643
Revises: 34b2137cc08e
Create Date: 2025-08-24 01:43:27.885886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f67bef8cc643'
down_revision: Union[str, None] = '34b2137cc08e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.alter_column(
        "raw_sales",
        "uploaded_at",
        server_default=op.f("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )



def downgrade() -> None:
    op.alter_column(
        "raw_sales",
        "uploaded_at",
    server_default=None,
    existing_type=sa.Datetime(),
    existing_nullable=False, )