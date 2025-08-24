"""add default to products.created_at

Revision ID: 6cf002aa65b7
Revises: 98686f11de1d
Create Date: 2025-08-24 01:17:32.250360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cf002aa65b7'
down_revision: Union[str, None] = '98686f11de1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from alembic import op

def upgrade() -> None:
    op.alter_column(
        "products",
        "created_at",
        server_default=op.f("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )



def downgrade() -> None:
    op.alter_column(
        "products",
        "created_at",
    server_default=None,
    existing_type=sa.Datetime(),
    existing_nullable=False, )