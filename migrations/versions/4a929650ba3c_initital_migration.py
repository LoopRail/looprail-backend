"""initital migration

Revision ID: 4a929650ba3c
Revises:
Create Date: 2026-01-13 17:11:48.110432

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a929650ba3c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    gender_enum = sa.Enum("MALE", "FEMALE", name="gender")
    gender_enum.create(op.get_bind(), checkfirst=True)

    # 2️⃣ Add the column using the enum type
    op.add_column(
        "users", sa.Column("gender", gender_enum, nullable=False, server_default="MALE")
    )

    # 3️⃣ Optional: remove default if you don’t want it afterwards
    op.alter_column("users", "gender", server_default=None)


def downgrade() -> None:
    # Drop the column first
    op.drop_column("users", "gender")

    # Then drop the enum type
    gender_enum = sa.Enum("MALE", "FEMALE", name="gender")
    gender_enum.drop(op.get_bind(), checkfirst=True)
