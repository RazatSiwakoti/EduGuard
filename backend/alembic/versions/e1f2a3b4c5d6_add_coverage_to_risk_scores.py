"""add coverage to risk_scores

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-31

One nullable column recording how much of the evidence a score was
actually based on.

NULLABLE ON PURPOSE, and not backfilled. Every score computed before
this column existed was computed without measuring coverage, so NULL is
the only honest value - it means "not measured". Defaulting to 1.0 would
assert full evidence for rows nobody has checked; defaulting to 0.0
would send every historical student straight to a review queue. The
verdict layer treats NULL as "cannot judge sufficiency" and leaves those
verdicts exactly as they were, so applying this migration changes
nothing until the next analysis run.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_scores", sa.Column("coverage", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_scores", "coverage")