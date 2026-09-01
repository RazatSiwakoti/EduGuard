"""merge teaching period normalisation migration

Revision ID: 0126e65c40a6
Revises: 984e705feccb, a1f3d7e2c4b5
Create Date: 2026-09-01 21:48:37.839847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0126e65c40a6'
down_revision: Union[str, Sequence[str], None] = ('984e705feccb', 'a1f3d7e2c4b5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
