"""add structured interventions

Revision ID: fa1b2c3d4e5f
Revises: f99efd1945e3
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "fa1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "f99efd1945e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interventions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lecturer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("follow_up_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    for column in ("student_id", "unit_id", "lecturer_id", "kind", "occurred_at", "outcome", "follow_up_on"):
        op.create_index(f"ix_interventions_{column}", "interventions", [column])


def downgrade() -> None:
    for column in ("follow_up_on", "outcome", "occurred_at", "kind", "lecturer_id", "unit_id", "student_id"):
        op.drop_index(f"ix_interventions_{column}", table_name="interventions")
    op.drop_table("interventions")
