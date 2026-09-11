"""set email verdict fk null on delete

Revision ID: 4da34bbb41ae
Revises: f6a7b8c9d0e1
Create Date: 2026-09-04 20:49:33.627221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4da34bbb41ae'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "email_messages_verdict_id_fkey",
        "email_messages",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "email_messages_verdict_id_fkey",
        "email_messages",
        "final_verdicts",
        ["verdict_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "email_messages_verdict_id_fkey",
        "email_messages",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "email_messages_verdict_id_fkey",
        "email_messages",
        "final_verdicts",
        ["verdict_id"],
        ["id"],
    )

