"""init schema

Revision ID: 98686f11de1d
Revises: 
Create Date: 2025-08-18 13:47:06.146215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '98686f11de1d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the unique constraints
    op.create_unique_constraint(None, 'model_runs', ['id'])
    op.create_unique_constraint(None, 'organizations', ['id'])
    op.create_unique_constraint(None, 'products', ['id'])

    op.alter_column(
        "products",
        "created_at",
        server_default=op.f("now()"),
        existing_type="TIMESTAMP",
        existing_nullable=False,
    )

def downgrade() -> None:
    # Drop default if downgrading
    op.alter_column(
        "products",
        "created_at",
        server_default=None,
        existing_type="TIMESTAMP",
        existing_nullable=False,
    )
    op.drop_constraint(None, 'products', type_='unique')
    op.drop_constraint(None, 'organizations', type_='unique')
    op.drop_constraint(None, 'model_runs', type_='unique')
