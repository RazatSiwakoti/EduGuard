"""add audit_events table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-28

One table, no changes to any existing one. The audit log observes the
rest of the schema and is observed by none of it, which is what lets it
be added and removed without touching a single existing row.

EVERY FOREIGN KEY IS ondelete="SET NULL".
Deleting a lecturer, a unit or a student must not delete the record of
what was done to them - that record is the reason the table exists. The
captured `actor_email`, `unit_code` and `student_name` columns are what
keep the row readable afterwards.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(), nullable=True),
        sa.Column("actor_name", sa.String(), nullable=True),
        sa.Column("actor_role", sa.String(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("unit_code", sa.String(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("student_name", sa.String(), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("before_state", sa.Text(), nullable=True),
        sa.Column("after_state", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_id", "audit_events", ["id"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_unit_id", "audit_events", ["unit_id"])
    op.create_index("ix_audit_events_student_id", "audit_events", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_student_id", table_name="audit_events")
    op.drop_index("ix_audit_events_unit_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_index("ix_audit_events_id", table_name="audit_events")
    op.drop_table("audit_events")