"""Add criteria shape lifecycle columns to units (section T1)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-27

WHAT THIS ADDS
--------------
Three nullable columns on `units`:

  criteria_updated_at   when the unit's criteria SHAPE last changed
  criteria_unlocked_at  a one-shot admin unlock window, cleared on save
  criteria_unlocked_by  who opened it

WHY NOTHING IS BACK-FILLED
--------------------------
`criteria_updated_at` is left NULL on every existing row, and that is the
whole point of the choice.

Staleness is derived: a FinalVerdict is stale when it was computed BEFORE
`criteria_updated_at`. Back-filling the column with the migration date -
the obvious "sensible default" - would therefore mark every risk result
in the database as computed against an older shape the moment this ran,
across every unit, with no shape having actually changed. Lecturers would
open their reports to a caveat telling them their whole cohort's results
were suspect, and the only way to clear it would be re-analysing every
unit.

NULL means "no shape change has ever been recorded", which is both true
and the safe reading.

NO STATE IS INFERRED EITHER
---------------------------
It would be possible to guess a shape-change date from the newest
criteria row, or to pre-lock units that already hold assessment data.
Neither is done: the lock is COMPUTED at read time from the events and
verdicts that actually exist (see `app/services/unit_composition.py`), so
a unit with data is already locked the first time anyone asks, without a
stored flag that could drift out of agreement with the data it describes.

DOWNGRADE
---------
Drops the three columns. Genuinely reversible - no data other than these
columns is touched, and the lock state they modify is recomputed from
scratch on every read.
"""

from alembic import op
import sqlalchemy as sa

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "units",
        sa.Column("criteria_updated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "units",
        sa.Column("criteria_unlocked_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "units",
        sa.Column("criteria_unlocked_by", sa.Integer(), nullable=True),
    )
    # Named explicitly: an unnamed constraint cannot be dropped portably
    # in downgrade(), which is how a "reversible" migration turns out not
    # to be on the day someone needs it.
    #
    # SQLite has no ALTER for constraints at all, so this is skipped
    # there. Production is PostgreSQL; SQLite only appears in the test
    # suites, which build their schema from the models and never run
    # alembic. Skipping rather than wrapping in batch_alter_table keeps
    # the Postgres path - the one that actually runs - a plain ALTER.
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_units_criteria_unlocked_by_users",
            "units",
            "users",
            ["criteria_unlocked_by"],
            ["id"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            "fk_units_criteria_unlocked_by_users", "units", type_="foreignkey"
        )
    op.drop_column("units", "criteria_unlocked_by")
    op.drop_column("units", "criteria_unlocked_at")
    op.drop_column("units", "criteria_updated_at")