"""feat: add email_notifications field to users

Revision ID: c1a2b477d130
Revises: b2e4aa336baa
Create Date: 2026-04-18 16:02:32.232496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c1a2b477d130'
down_revision: Union[str, None] = 'b2e4aa336baa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("users", "email_notifications")
