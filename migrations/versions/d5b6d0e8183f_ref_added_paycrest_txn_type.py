"""ref: added paycrest txn type

Revision ID: d5b6d0e8183f
Revises: 1ed93ce85b1d
Create Date: 2026-03-23 13:34:45.826275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd5b6d0e8183f'
down_revision: Union[str, None] = '1ed93ce85b1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

paycrest_status_enum = sa.Enum(
    'INITIATED', 'PENDING', 'VALIDATED', 'EXPIRED', 'SETTLED', 'REFUNDED',
    name='paycrestorderstatus'
)

def upgrade() -> None:
    paycrest_status_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        'bank_transfer_details', 'paycrest_status',
        existing_type=sa.VARCHAR(),
        type_=paycrest_status_enum,
        existing_nullable=True,
        postgresql_using="paycrest_status::paycrestorderstatus"
    )

def downgrade() -> None:
    op.alter_column(
        'bank_transfer_details', 'paycrest_status',
        existing_type=paycrest_status_enum,
        type_=sa.VARCHAR(),
        existing_nullable=True,
        postgresql_using="paycrest_status::varchar"
    )
    paycrest_status_enum.drop(op.get_bind(), checkfirst=True)