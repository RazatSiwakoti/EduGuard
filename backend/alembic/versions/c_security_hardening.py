"""security hardening credentials and login attempts

Revision ID: c_security_hardening
Revises: current feature heads
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c_security_hardening"
down_revision: Union[str, Sequence[str], None] = (
    "20260910_retention_months",
    "aa11bb22cc33",
    "fa1b2c3d4e5f",
    "b7c8d9e0f1a2",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"])
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_login_attempts_id", "login_attempts", ["id"])
    op.create_index("ix_login_attempts_email_attempted_at", "login_attempts", ["email", "attempted_at"])
    op.create_index("ix_login_attempts_ip_attempted_at", "login_attempts", ["ip", "attempted_at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempts_ip_attempted_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_email_attempted_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_id", table_name="login_attempts")
    op.drop_table("login_attempts")
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "password_changed_at")
