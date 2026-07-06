"""Units: make lecturer_id nullable, add is_active

Revision ID: ea13b6ee75bd
Revises: a1b3c9d7e2f4
Create Date: 2026-07-05 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea13b6ee75bd'
down_revision: Union[str, Sequence[str], None] = 'a1b3c9d7e2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. lecturer_id can now be NULL (unassigned unit / safe lecturer removal)
    op.alter_column(
        'units',
        'lecturer_id',
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 2. is_active, defaulting existing rows to True so nothing that
    # already exists is accidentally treated as archived.
    op.add_column(
        'units',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('units', 'is_active')

    # NOTE: if any unit was unassigned (lecturer_id IS NULL) while this
    # migration was applied, this will fail with a NOT NULL violation.
    # Any such units must be reassigned a lecturer before downgrading.
    op.alter_column(
        'units',
        'lecturer_id',
        existing_type=sa.Integer(),
        nullable=False,
    )