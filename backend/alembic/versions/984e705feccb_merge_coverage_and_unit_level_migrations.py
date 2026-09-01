"""merge coverage and unit level migrations

Revision ID: 984e705feccb
Revises: e1f2a3b4c5d6, ef4d8a91f2c3
Create Date: 2026-09-01 21:40:32.744802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '984e705feccb'
down_revision: Union[str, Sequence[str], None] = ('e1f2a3b4c5d6', 'ef4d8a91f2c3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
