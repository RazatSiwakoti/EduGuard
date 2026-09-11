"""set email student fk null on delete

Revision ID: 7033427e04c3
Revises: 4da34bbb41ae
Create Date: 2026-09-04 20:57:27.373821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7033427e04c3'
down_revision: Union[str, Sequence[str], None] = '4da34bbb41ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "email_messages_student_id_fkey",
        "email_messages",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "email_messages_student_id_fkey",
        "email_messages",
        "students",
        ["student_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "email_messages_student_id_fkey",
        "email_messages",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "email_messages_student_id_fkey",
        "email_messages",
        "students",
        ["student_id"],
        ["id"],
    )