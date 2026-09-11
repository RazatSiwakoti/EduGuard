"""add email_templates and email_messages

Phase 7.8 - Alerts.

Two tables:

  email_templates  the wording of an alert. lecturer_id NULL means a
                   system default, seeded at startup and read-only.
  email_messages   the outbox AND the log. A row is written BEFORE the
                   email is dispatched, so a crash mid-send leaves a
                   queued row to retry rather than delivered emails
                   nobody has a record of.

Note that email_messages stores the RENDERED subject and body, not just
 a template reference. Templates are editable; the log must not be
 rewritten when one changes.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        # NULL = system default.
        sa.Column("lecturer_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["lecturer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_templates_id"), "email_templates", ["id"])
    op.create_index(
        op.f("ix_email_templates_lecturer_id"), "email_templates", ["lecturer_id"]
    )
    op.create_index(
        op.f("ix_email_templates_risk_tier"), "email_templates", ["risk_tier"]
    )

    op.create_table(
        "email_messages",
        sa.Column(
            "id", sa.Integer(), nullable=False
        ),
        sa.Column(
            "kind", sa.String(), nullable=False, server_default="student_alert"
        ),
        # NULL on a lecturer summary, which is about a cohort.
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("lecturer_id", sa.Integer(), nullable=False),
        # Captured at queue time so a later address change cannot
        # retroactively alter who the log says was contacted.
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("recipient_name", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("template_name", sa.String(), nullable=True),
        sa.Column("risk_tier", sa.String(), nullable=True),
        sa.Column("verdict_id", sa.Integer(), nullable=True),
        sa.Column("trigger", sa.String(), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "queued_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["lecturer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["verdict_id"], ["final_verdicts.id"]),
        # SET NULL, not CASCADE: deleting a template must never delete
        # the record of emails already sent with it.
        sa.ForeignKeyConstraint(
            ["template_id"], ["email_templates.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_messages_id"), "email_messages", ["id"])
    op.create_index(op.f("ix_email_messages_kind"), "email_messages", ["kind"])
    op.create_index(
        op.f("ix_email_messages_student_id"), "email_messages", ["student_id"]
    )
    op.create_index(op.f("ix_email_messages_unit_id"), "email_messages", ["unit_id"])
    op.create_index(
        op.f("ix_email_messages_lecturer_id"), "email_messages", ["lecturer_id"]
    )
    op.create_index(op.f("ix_email_messages_status"), "email_messages", ["status"])
    op.create_index(op.f("ix_email_messages_trigger"), "email_messages", ["trigger"])
    # The outbox drain filters on status and orders by queued_at, and
    # the suppression check reads the most recent alert per student.
    op.create_index(
        op.f("ix_email_messages_queued_at"), "email_messages", ["queued_at"]
    )


def downgrade() -> None:
    for index in (
        "ix_email_messages_queued_at",
        "ix_email_messages_trigger",
        "ix_email_messages_status",
        "ix_email_messages_lecturer_id",
        "ix_email_messages_unit_id",
        "ix_email_messages_student_id",
        "ix_email_messages_kind",
        "ix_email_messages_id",
    ):
        op.drop_index(op.f(index), table_name="email_messages")
    op.drop_table("email_messages")

    for index in (
        "ix_email_templates_risk_tier",
        "ix_email_templates_lecturer_id",
        "ix_email_templates_id",
    ):
        op.drop_index(op.f(index), table_name="email_templates")
    op.drop_table("email_templates")
