"""add notifications seen at

Revision ID: d79fc875bb9d
Revises: f99efd1945e3
Create Date: 2026-09-10 20:17:41.808743

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd79fc875bb9d'
down_revision: Union[str, Sequence[str], None] = 'f99efd1945e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notifications_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "notifications_seen_at")