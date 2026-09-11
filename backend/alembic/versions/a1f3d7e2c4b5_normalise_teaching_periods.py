"""Normalise unit teaching periods.

Revision ID: a1f3d7e2c4b5
Revises: ef4d8a91f2c3
Create Date: 2026-09-01 21:46:05.903000

The note "date should be fixed to 3" is interpreted as the teaching period
capped at three trimesters (T1/T2/T3), not as a restriction on the real
calendar start_date field.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1f3d7e2c4b5'
down_revision: Union[str, Sequence[str], None] = 'ef4d8a91f2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalise free-form teaching periods to the closed T1/T2/T3 set."""
    op.execute(
        """
        UPDATE units
        SET teaching_period = UPPER(TRIM(teaching_period))
        WHERE teaching_period IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE units
        SET teaching_period = NULL
        WHERE teaching_period IS NOT NULL
          AND UPPER(TRIM(teaching_period)) NOT IN ('T1', 'T2', 'T3')
        """
    )


def downgrade() -> None:
    """Downgrade is intentionally a no-op.

    This migration normalises historical free-form values into a closed set of
    canonical terms. The original values are not recoverable reliably.
    """
    pass
