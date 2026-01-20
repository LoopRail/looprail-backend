"""ref: payment type

Revision ID: e146de517967
Revises: 944f1c5a53bf
Create Date: 2026-01-20 04:38:36.986697

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "e146de517967"
down_revision: Union[str, None] = "944f1c5a53bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Alter column to text temporarily
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN method TYPE VARCHAR USING method::text"
    )

    # Step 2: Drop the old enum type
    op.execute("DROP TYPE IF EXISTS paymentmethod")

    # Step 3: Create new enum type with new values
    op.execute("""
        CREATE TYPE paymentmethod AS ENUM (
            'BLOCKCHAIN',
            'BANK_TRANSFER',
            'CARD',
            'INTERNAL',
            'WALLET'
        )
    """)

    # Step 4: Convert column back to enum type
    op.execute("""
        ALTER TABLE transactions 
        ALTER COLUMN method TYPE paymentmethod 
        USING method::paymentmethod
    """)


def downgrade() -> None:
    # Step 1: Alter column to text temporarily
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN method TYPE VARCHAR USING method::text"
    )

    # Step 2: Drop the new enum type
    op.execute("DROP TYPE IF EXISTS paymentmethod")

    # Step 3: Recreate old enum type
    op.execute("""
        CREATE TYPE paymentmethod AS ENUM (
            'CARD',
            'APPLE_PAY',
            'GOOGLE_PAY',
            'BANK_TRANSFER',
            'MOBILE_MONEY',
            'WALLET_TRANSFER'
        )
    """)

    # Step 4: Convert column back to enum type
    op.execute("""
        ALTER TABLE transactions 
        ALTER COLUMN method TYPE paymentmethod 
        USING method::paymentmethod
    """)
