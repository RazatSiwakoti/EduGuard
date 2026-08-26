"""add weekly_values to assessment_events and create student_notes

Phase 7.6b. Two unrelated-looking changes in one revision because they
land together and neither is useful without the student card.

weekly_values
    Until now ingestion aggregated a student's raw weekly cells into one
    percentage plus one trend value and DISCARDED the cells (see
    build_weekly_criterion_event). That made a real week-by-week chart
    impossible to draw honestly. This column keeps the normalised list.

    Nullable, and deliberately NOT backfilled: rows written before this
    revision have no weekly data anywhere to recover it from. The card
    renders an empty state for those rather than inventing a chart.

student_notes
    A lecturer's own free-text notes about one student in one unit.
    NOT a column on final_verdicts - that table is append-only, so a
    note attached to one verdict would silently disappear the next time
    the analysis was run. See the model docstring.

Revision ID: b1c2d3e4f5a6
Revises: 9efa39fe6b74
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "9efa39fe6b74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable with no server_default: an existing row genuinely has no
    # weekly data, and NULL says that honestly where an empty list would
    # claim "we recorded seven weeks and they were all absent".
    op.add_column(
        "assessment_events",
        sa.Column("weekly_values", sa.JSON(), nullable=True),
    )

    op.create_table(
        "student_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("lecturer_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["lecturer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        # One note per lecturer per student per unit, enforced by the
        # database so a double submit cannot leave two contradictory rows.
        sa.UniqueConstraint(
            "student_id", "unit_id", "lecturer_id", name="uq_student_note_scope"
        ),
    )
    op.create_index(
        op.f("ix_student_notes_id"), "student_notes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_student_notes_student_id"), "student_notes", ["student_id"], unique=False
    )
    op.create_index(
        op.f("ix_student_notes_unit_id"), "student_notes", ["unit_id"], unique=False
    )
    op.create_index(
        op.f("ix_student_notes_lecturer_id"),
        "student_notes",
        ["lecturer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_student_notes_lecturer_id"), table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_unit_id"), table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_student_id"), table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_id"), table_name="student_notes")
    op.drop_table("student_notes")

    # Downgrading DESTROYS every weekly list captured since the upgrade.
    # There is no other copy of that data anywhere in the schema.
    op.drop_column("assessment_events", "weekly_values")