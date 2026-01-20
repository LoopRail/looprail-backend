"""ref: payment type

Revision ID: 944f1c5a53bf
Revises: 611b0b7b1ba3
Create Date: 2026-01-20 04:30:24.268773

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "944f1c5a53bf"
down_revision: Union[str, None] = "611b0b7b1ba3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create new enum with all values from PaymentMethod
    new_enum = sa.Enum(
        "BLOCKCHAIN",
        "BANK_TRANSFER",
        "CARD",
        "INTERNAL",
        "WALLET",
        name="paymentmethod",
        create_type=False,  # do not try to create type if it exists
    )
    # Alter the transactions.method column to use new enum
    op.alter_column(
        "transactions",
        "method",
        type_=new_enum,
        existing_type=sa.Enum(
            "CARD",
            "APPLE_PAY",
            "GOOGLE_PAY",
            "BANK_TRANSFER",
            "MOBILE_MONEY",
            "WALLET_TRANSFER",
            name="paymentmethod",
        ),
        nullable=False,
    )


def downgrade() -> None:
    # Downgrade: revert to previous enum values
    old_enum = sa.Enum(
        "CARD",
        "APPLE_PAY",
        "GOOGLE_PAY",
        "BANK_TRANSFER",
        "MOBILE_MONEY",
        "WALLET_TRANSFER",
        name="paymentmethod",
        create_type=False,
    )
    op.alter_column(
        "transactions",
        "method",
        type_=old_enum,
        existing_type=sa.Enum(
            "BLOCKCHAIN",
            "BANK_TRANSFER",
            "CARD",
            "INTERNAL",
            "WALLET",
            name="paymentmethod",
        ),
        nullable=False,
    )
