"""Add assessment kind to criteria (section T2)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-08-28

WHAT THIS ADDS
--------------
One nullable column on `criteria`:

  kind   "quiz" | "assignment", NULL for every other category

WHY A SECOND COLUMN RATHER THAN TWO MORE `category` VALUES
----------------------------------------------------------
`category` is the ML contract. `rule_score_service`, `ml_score_service`,
`report_service`, `dashboard_service` and `student_detail_service` all
branch on `CriteriaCategory.ASSESSMENT`, and so does the feature builder
that fed the trained model. Splitting ASSESSMENT into QUIZ and ASSIGNMENT
would have made every one of those branches stop matching - not with an
error, but with assessments silently disappearing from the blend, the
report and the feature vector. `kind` is additive: nothing in the scoring
path reads it.

NOTHING IS BACK-FILLED
----------------------
Existing assessment rows keep `kind = NULL`. NULL reads as "the
coordinator has not said", which is true - the concept did not exist when
those rows were written. Guessing a kind from the free-text `name`
("Quiz 1" -> quiz) would have been a fabricated fact stored as a real
one, and the setup form is the place that question gets answered.

DOWNGRADE
---------
Drops the column, then the enum type on PostgreSQL. Order matters: a type
still referenced by a column cannot be dropped.
"""

from alembic import op
import sqlalchemy as sa

revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None

# Declared once and reused by both directions so the two can never
# disagree about the type's name - which is how a downgrade fails on the
# day it is actually needed.
KIND_ENUM = sa.Enum("quiz", "assignment", name="assessmentkind")


def upgrade() -> None:
    bind = op.get_bind()

    # PostgreSQL needs the type to exist before a column can reference
    # it, and `op.add_column` does NOT create it. SQLite has no native
    # enum type at all - SQLAlchemy renders it as VARCHAR with a CHECK -
    # so the create is skipped there rather than failing.
    if bind.dialect.name != "sqlite":
        KIND_ENUM.create(bind, checkfirst=True)

    op.add_column(
        "criteria",
        sa.Column("kind", KIND_ENUM, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("criteria", "kind")

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        KIND_ENUM.drop(bind, checkfirst=True)