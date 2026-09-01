"""Normalise unit level values.

Revision ID: ef4d8a91f2c3
Revises: 9efa39fe6b74
Create Date: 2026-09-01 21:35:59.818000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ef4d8a91f2c3'
down_revision: Union[str, Sequence[str], None] = '9efa39fe6b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalise free-form unit levels to the closed vocabulary."""
    op.execute(
        """
        UPDATE units
        SET level = 'diploma'
        WHERE level IS NOT NULL
          AND LOWER(TRIM(level)) LIKE '%diplom%'
        """
    )
    op.execute(
        """
        UPDATE units
        SET level = 'bachelor'
        WHERE level IS NOT NULL
          AND LOWER(TRIM(level)) LIKE '%bach%'
        """
    )
    op.execute(
        """
        UPDATE units
        SET level = 'masters'
        WHERE level IS NOT NULL
          AND (
            LOWER(TRIM(level)) LIKE '%master%'
            OR LOWER(TRIM(level)) LIKE '%mast%'
          )
        """
    )
    op.execute(
        """
        UPDATE units
        SET level = NULL
        WHERE level IS NOT NULL
          AND LOWER(TRIM(level)) NOT IN ('diploma', 'bachelor', 'masters')
        """
    )


def downgrade() -> None:
    """Downgrade is intentionally a no-op.

    This migration normalises legacy free-form values into a closed set of
    canonical levels. Those original values cannot be recovered reliably.
    """
    pass
