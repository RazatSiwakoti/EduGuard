"""add missing-data flag to final verdicts

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "0126e65c40a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "final_verdicts",
        sa.Column("is_missing_data", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("final_verdicts", "is_missing_data")
