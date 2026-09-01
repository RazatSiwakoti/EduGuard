"""add class_code to units and widen the offering uniqueness constraint

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-29

KOI runs the same subject more than once in a trimester - ICT730LA1 and
ICT730LA2 are separate classes with separate lecturers and students. The
old constraint on (unit_code, year, teaching_period) made the second one
impossible to create, so this adds `class_code` and puts it inside the
constraint.

EXISTING ROWS GET "", NOT NULL, AND NOT "LA1".

  * NOT NULL, because a nullable column inside a UNIQUE constraint stops
    constraining as soon as it is NULL - SQL does not treat NULL as
    equal to itself, so two classless ICT730 rows in one trimester would
    both be accepted. The empty string is a real value the constraint
    can compare, so the old guarantee survives this change untouched.

  * NOT "LA1", because that would assert something about existing data
    that nobody has checked. An existing ICT730 is a unit whose class
    was never recorded, which is what "" says. Backfilling a class onto
    it would put a fact in the database that came from this migration
    rather than from the institution.

THE CONSTRAINT IS REPLACED, NOT ADDED ALONGSIDE. Leaving the old one in
place would keep refusing the second class, which is the entire point of
this change.

`batch_alter_table` is used because SQLite cannot ALTER a constraint in
place; it rebuilds the table. On PostgreSQL it degrades to plain DDL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_CONSTRAINT = "uq_unit_code_year_period"
NEW_CONSTRAINT = "uq_unit_code_year_period_class"


def upgrade() -> None:
    # server_default="" fills every existing row in the same statement,
    # which is what lets the column be NOT NULL immediately rather than
    # needing a nullable column, a backfill and an ALTER.
    op.add_column(
        "units",
        sa.Column(
            "class_code",
            sa.String(length=8),
            nullable=False,
            server_default="",
        ),
    )

    with op.batch_alter_table("units") as batch:
        # The old constraint may not exist under that name on a database
        # built by create_all rather than by migrations, so its removal
        # is tolerated failing. The new one is not optional.
        try:
            batch.drop_constraint(OLD_CONSTRAINT, type_="unique")
        except Exception:  # noqa: BLE001 - see above
            pass
        batch.create_unique_constraint(
            NEW_CONSTRAINT,
            ["unit_code", "year", "teaching_period", "class_code"],
        )


def downgrade() -> None:
    # Reversing this can genuinely fail, and that is correct behaviour:
    # if two classes of one subject exist, the old three-column
    # constraint cannot be recreated without deleting one of them. A
    # migration that silently dropped a class to go backwards would lose
    # a cohort's data.
    with op.batch_alter_table("units") as batch:
        batch.drop_constraint(NEW_CONSTRAINT, type_="unique")
        batch.create_unique_constraint(
            OLD_CONSTRAINT,
            ["unit_code", "year", "teaching_period"],
        )
    op.drop_column("units", "class_code")