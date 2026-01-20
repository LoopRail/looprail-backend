"""ref: add us dollar to currency enum
Revision ID: f535e8dc3c62
Revises: e146de517967
Create Date: 2026-01-20 04:40:38.441965
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f535e8dc3c62"
down_revision: Union[str, None] = "e146de517967"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'usd' to the currency enum
    # PostgreSQL allows adding enum values without recreating the type
    op.execute("ALTER TYPE currency ADD VALUE IF NOT EXISTS 'US_Dollar'")


def downgrade() -> None:
    # Step 1: Alter all columns using currency to text
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN currency TYPE VARCHAR USING currency::text"
    )

    # Step 2: Drop the enum type
    op.execute("DROP TYPE IF EXISTS currency")

    # Step 3: Recreate enum without 'usd'
    op.execute("""
        CREATE TYPE currency AS ENUM (
            'NAIRA'
        )
    """)

    # Step 4: Convert columns back to enum
    op.execute("""
        ALTER TABLE transactions 
        ALTER COLUMN currency TYPE currency 
        USING currency::currency
    """)
