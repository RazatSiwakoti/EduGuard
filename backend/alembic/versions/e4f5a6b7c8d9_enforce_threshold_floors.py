"""Enforce threshold floors on existing criteria (section D1)

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-27

WHY THIS MIGRATION EXISTS
-------------------------
Until now nothing validated a Criteria threshold: `validate_lecturer_threshold`
existed but had no callers, and it was also keyed "tutorial" while the enum
value is "weekly_tut", so tutorial thresholds would have passed at any value
even if it HAD been called.

Section D1 wires it up. That instantly creates a class of rows the API would
now reject but the database already holds - a threshold of 0 on a tutorial,
an attendance threshold somebody edited by hand. Leaving them means the rule
engine keeps scoring against bars the system no longer considers legal, and
the first lecturer to open the edit form gets an error about a value they
never set.

So the data is brought up to the rules, not the other way round.

WHAT IT DOES NOT DO
-------------------
It does not lower anything. Every change here raises a threshold or resets
it to a system constant, so no student moves from "at risk" to "safe" as a
result of running it. Some students may move the other way, which is the
correct direction for an early-warning system to err when a bar is corrected.
"""

from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None

# Mirrors app/core/risk_constants.py. Repeated as literals on purpose:
# a migration must describe what it did on the day it ran, and importing

# the constants would let a future edit silently rewrite history.
ASSESSMENT_FLOOR = 45.0
TUTORIAL_FLOOR = 40.0
DEFAULT_THRESHOLD = 50.0
FIXED_ATTENDANCE_THRESHOLD = 50.0
FIXED_MOODLE_THRESHOLD = 10.0


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Attendance and Moodle are system constants. Any drift here means
    #    the rule engine was scoring against a bar that neither the seeding
    #    code nor the constants file knows about.
    connection.execute(
        sa.text(
            "UPDATE criteria SET threshold = :t "
            "WHERE category = 'attendance' AND threshold <> :t"
        ),
        {"t": FIXED_ATTENDANCE_THRESHOLD},
    )
    connection.execute(
        sa.text(
            "UPDATE criteria SET threshold = :t "
            "WHERE category = 'moodle' AND threshold <> :t"
        ),
        {"t": FIXED_MOODLE_THRESHOLD},
    )

    # 2. Adjustable categories: raise anything below its floor UP to the
    #    floor. Not to 50 - a lecturer who deliberately set 46 keeps 46.
    connection.execute(
        sa.text(
            "UPDATE criteria SET threshold = :f "
            "WHERE category = 'assessment' AND threshold < :f"
        ),
        {"f": ASSESSMENT_FLOOR},
    )
    connection.execute(
        sa.text(
            "UPDATE criteria SET threshold = :f "
            "WHERE category = 'weekly_tut' AND threshold < :f"
        ),
        {"f": TUTORIAL_FLOOR},
    )

    # 3. Anything ABOVE the default is brought back down to it. The API
    #    now refuses to raise a bar, so a stored value above 50 is a bar
    #    no lecturer could set today and none of them agreed to.
    connection.execute(
        sa.text(
            "UPDATE criteria SET threshold = :d "
            "WHERE category IN ('assessment', 'weekly_tut') AND threshold > :d"
        ),
        {"d": DEFAULT_THRESHOLD},
    )


def downgrade() -> None:
    """
    Deliberately a no-op.

    The original per-row values are not recorded anywhere, so there is
    nothing to restore. Writing a downgrade that reset every threshold to
    some guessed value would destroy the lecturers' real choices in the
    name of reversibility.
    """
    pass