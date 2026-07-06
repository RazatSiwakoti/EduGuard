"""Enforce NOT NULL on users.full_name to match the model

Revision ID: d7e1e140c600
Revises: ea13b6ee75bd
Create Date: 2026-07-05 11:00:00.000000

The User model has always declared full_name as nullable=False, but the
Phase 2 migration that added the column left it nullable=True at the DB
level and nothing ever tightened it. This closes that gap.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e1e140c600'
down_revision: Union[str, Sequence[str], None] = 'ea13b6ee75bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill safety net: should be a no-op on your DB today (every seeded
    # user already has a full_name), but protects this migration from
    # failing outright if any row ever slipped through with NULL.
    op.execute("UPDATE users SET full_name = 'Unknown' WHERE full_name IS NULL")

    op.alter_column(
        'users',
        'full_name',
        existing_type=sa.String(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'users',
        'full_name',
        existing_type=sa.String(),
        nullable=True,
    )