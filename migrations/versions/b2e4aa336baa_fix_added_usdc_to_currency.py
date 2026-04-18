"""fix: added usdc to currency

Revision ID: b2e4aa336baa
Revises: 9e87e3bd35b3
Create Date: 2026-04-18 12:28:58.853590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b2e4aa336baa'
down_revision: Union[str, None] = '9e87e3bd35b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE currency ADD VALUE IF NOT EXISTS 'USDC'")


def downgrade() -> None:
    pass
