"""add error_message to raw_sales

Revision ID: 34b2137cc08e
Revises: 6cf002aa65b7
Create Date: 2025-08-24 01:33:44.396642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '34b2137cc08e'
down_revision: Union[str, None] = '6cf002aa65b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
   
    op.add_column('raw_sales', sa.Column('error_message', sa.String(), nullable=True))
    


def downgrade() -> None:
   
    op.drop_column('raw_sales', 'error_message')
    