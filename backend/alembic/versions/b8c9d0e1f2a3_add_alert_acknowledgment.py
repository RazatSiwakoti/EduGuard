"""add alert acknowledgment token and timestamp to email_messages

Revision ID: b8c9d0e1f2a3
Revises: a6b7c8d9e0f1
Create Date: 2026-08-28

Adds the two columns behind the student acknowledgment receipt.

BOTH ARE NULLABLE, ON PURPOSE. Every message already in the table was
sent before this feature existed and was never acknowledged, which is
different from "acknowledged at an unknown time". NULL says that
correctly; a backfilled default would invent evidence.

THE UNIQUE CONSTRAINT IS THE SECURITY BOUNDARY, not a tidiness rule.
The token is what authorises a stranger to mark a notice acknowledged.
Two rows sharing one would make a single link resolve to whichever row
the database happened to return first.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_messages",
        sa.Column("ack_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "email_messages",
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
    )
    # A unique INDEX rather than a unique CONSTRAINT: the token is looked
    # up on every click of an acknowledgment link, so it needs the index
    # regardless, and one object serves both purposes on every backend
    # this project runs on.
    op.create_index(
        "ix_email_messages_ack_token",
        "email_messages",
        ["ack_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_email_messages_ack_token", table_name="email_messages")
    op.drop_column("email_messages", "acknowledged_at")
    op.drop_column("email_messages", "ack_token")
