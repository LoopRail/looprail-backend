"""fix: txn types

Revision ID: efe4521eb9cc
Revises: 2532a539d147
Create Date: 2026-02-21 02:26:58.508719

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "efe4521eb9cc"
down_revision: Union[str, None] = "2532a539d147"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
