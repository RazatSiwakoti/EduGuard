"""add verdict_reviews table and final_verdicts.review_id

Phase 7.7. Moves a lecturer's review decision off final_verdicts and
into a record that survives re-analysis.

THE BUG THIS FIXES
------------------
submit_review_decision() mutated the final_verdicts row in place, but
compute_and_stage_final_verdict() always INSERTs a new one and every
read takes the latest per (student, unit). So a review was silently
destroyed by the next "Run Analysis": the student reappeared in the
queue and the decision became unreachable.

Reviews now live in their own append-only table, stamped with the
rule_tier and ml_tier they were made about, so a later run can tell
whether it is looking at the same disagreement and carry the decision
forward only when it is.

The three review columns already on final_verdicts are KEPT and now hold
a denormalised copy of whichever review resolved that verdict, so the
existing risk router and anything reading the table directly keep
working. verdict_reviews is the source of truth.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verdict_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("checkpoint_week", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=False),
        # The engine pair this decision resolved - the carry-forward key.
        sa.Column("rule_tier", sa.String(), nullable=False),
        sa.Column("ml_tier", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_verdict_reviews_id"), "verdict_reviews", ["id"])
    op.create_index(
        op.f("ix_verdict_reviews_student_id"), "verdict_reviews", ["student_id"]
    )
    op.create_index(op.f("ix_verdict_reviews_unit_id"), "verdict_reviews", ["unit_id"])
    # Lookups are always "latest review for this student/unit/checkpoint",
    # so created_at is indexed for the ORDER BY rather than for filtering.
    op.create_index(
        op.f("ix_verdict_reviews_created_at"), "verdict_reviews", ["created_at"]
    )

    op.add_column(
        "final_verdicts", sa.Column("review_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_final_verdicts_review_id",
        "final_verdicts",
        "verdict_reviews",
        ["review_id"],
        ["id"],
    )

    # Rescue reviews made under the old in-place scheme. Rows whose engine
    # scores were deleted are skipped instead of inventing a carry-forward key.
    op.execute(
        """
        INSERT INTO verdict_reviews (
            student_id, unit_id, checkpoint_week, decision, comment,
            reviewed_by, rule_tier, ml_tier, created_at
        )
        SELECT fv.student_id, fv.unit_id, fv.checkpoint_week,
               fv.review_decision, NULL,
               fv.reviewed_by, rs.risk_level, ms.risk_level,
               COALESCE(fv.reviewed_at, fv.created_at)
        FROM final_verdicts fv
        JOIN risk_scores rs ON rs.id = fv.rule_score_id
        JOIN risk_scores ms ON ms.id = fv.ml_score_id
        WHERE fv.reviewed_by IS NOT NULL
          AND fv.review_decision IS NOT NULL
        """
    )

    # Point each rescued verdict at the row created for it.
    op.execute(
        """
        UPDATE final_verdicts fv
        SET review_id = vr.id
        FROM verdict_reviews vr
        WHERE vr.student_id = fv.student_id
          AND vr.unit_id = fv.unit_id
          AND vr.checkpoint_week = fv.checkpoint_week
          AND vr.reviewed_by = fv.reviewed_by
          AND vr.decision = fv.review_decision
          AND fv.reviewed_by IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_final_verdicts_review_id", "final_verdicts", type_="foreignkey"
    )
    op.drop_column("final_verdicts", "review_id")

    op.drop_index(op.f("ix_verdict_reviews_created_at"), table_name="verdict_reviews")
    op.drop_index(op.f("ix_verdict_reviews_unit_id"), table_name="verdict_reviews")
    op.drop_index(op.f("ix_verdict_reviews_student_id"), table_name="verdict_reviews")
    op.drop_index(op.f("ix_verdict_reviews_id"), table_name="verdict_reviews")

    # Every review made since the upgrade is destroyed here. The copies
    # on final_verdicts survive only for verdicts that were never
    # superseded by a later analysis run.
    op.drop_table("verdict_reviews")
