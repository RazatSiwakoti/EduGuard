
"""add user avatar and preferences

Revision ID: f99efd1945e3
Revises: 7033427e04c3
Create Date: 2026-09-06 21:34:43.815050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f99efd1945e3"
down_revision: Union[str, Sequence[str], None] = "7033427e04c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add avatar and preferences columns to users table."""
    op.add_column(
        "users",
        sa.Column("avatar", sa.Text(), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column(
            "preferences",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Remove avatar and preferences columns from users table."""
    op.drop_column("users", "preferences")
    op.drop_column("users", "avatar")

