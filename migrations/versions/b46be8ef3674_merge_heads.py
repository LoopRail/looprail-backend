"""merge heads

Revision ID: b46be8ef3674
Revises: 7b288f82d3ac, a04f0f42db98
Create Date: 2026-01-17 01:08:16.431037

"""

from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = "b46be8ef3674"
down_revision: Union[str, None] = ("7b288f82d3ac", "a04f0f42db98")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
