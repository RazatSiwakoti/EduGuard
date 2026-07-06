"""Rename userrole enum values to lowercase to match application code

Revision ID: a1b3c9d7e2f4
Revises: 52cc8af5d2f0
Create Date: 2026-07-04 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a1b3c9d7e2f4'
down_revision = '52cc8af5d2f0'
branch_labels = None
depends_on = None


# The `userrole` Postgres enum type currently holds uppercase labels
# (SUPER_ADMIN, ADMIN, LECTURER) - a leftover from an earlier
# migration generated before the model's values_callable fix existed.
# RENAME VALUE relabels the type in place: no column type change, no
# cast, no data touched.
RENAMES = {
    "SUPER_ADMIN": "super_admin",
    "ADMIN": "admin",
    "LECTURER": "lecturer",
}


def upgrade() -> None:
    for old_value, new_value in RENAMES.items():
        op.execute(f"ALTER TYPE userrole RENAME VALUE '{old_value}' TO '{new_value}'")


def downgrade() -> None:
    for old_value, new_value in RENAMES.items():
        op.execute(f"ALTER TYPE userrole RENAME VALUE '{new_value}' TO '{old_value}'")