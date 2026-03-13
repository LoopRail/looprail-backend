"""add processing to transaction status

Revision ID: 192fadf78cb1
Revises: 7332c348b6ee
Create Date: 2026-03-13 13:13:22.345494

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "192fadf78cb1"
down_revision: Union[str, None] = "7332c348b6ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'PROCESSING' to the transactionstatus enum (SQLModel persists member names)
    # Use autocommit to allow ALTER TYPE inside the migration
    op.execute("COMMIT")
    op.execute("ALTER TYPE transactionstatus ADD VALUE IF NOT EXISTS 'PROCESSING'")


def downgrade() -> None:
    # Downgrading enums in Postgres is complex as there's no DROP VALUE.
    # We follow the recreative approach if absolute rollback is needed.
    pass
