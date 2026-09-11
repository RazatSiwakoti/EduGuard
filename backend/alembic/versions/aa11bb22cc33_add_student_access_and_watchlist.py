"""add student portal access tokens and lecturer watchlists

Revision ID: aa11bb22cc33
Revises: f99efd1945e3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "aa11bb22cc33"
down_revision: Union[str, Sequence[str], None] = "f99efd1945e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_access_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "unit_id", name="uq_student_access_student_unit"),
        sa.UniqueConstraint("token_hash", name="uq_student_access_token_hash"),
    )
    op.create_index("ix_student_access_tokens_student_id", "student_access_tokens", ["student_id"])
    op.create_index("ix_student_access_tokens_unit_id", "student_access_tokens", ["unit_id"])
    op.create_index("ix_student_access_tokens_token_hash", "student_access_tokens", ["token_hash"])
    op.create_index("ix_student_access_tokens_expires_at", "student_access_tokens", ["expires_at"])

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lecturer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.UniqueConstraint("lecturer_id", "student_id", "unit_id", name="uq_watchlist_scope"),
    )
    op.create_index("ix_watchlists_lecturer_id", "watchlists", ["lecturer_id"])


def downgrade() -> None:
    op.drop_index("ix_watchlists_lecturer_id", table_name="watchlists")
    op.drop_table("watchlists")
    for name in ("ix_student_access_tokens_expires_at", "ix_student_access_tokens_token_hash",
                 "ix_student_access_tokens_unit_id", "ix_student_access_tokens_student_id"):
        op.drop_index(name, table_name="student_access_tokens")
    op.drop_table("student_access_tokens")
