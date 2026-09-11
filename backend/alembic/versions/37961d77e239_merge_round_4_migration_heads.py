"""merge Round 4 migration heads

Revision ID: 37961d77e239
Revises: c_security_hardening, d79fc875bb9d
Create Date: 2026-09-10 21:35:33.797113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37961d77e239'
down_revision: Union[str, Sequence[str], None] = ('c_security_hardening', 'd79fc875bb9d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
