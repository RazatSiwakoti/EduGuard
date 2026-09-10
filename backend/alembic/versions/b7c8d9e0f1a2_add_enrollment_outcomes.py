"""Add ground-truth outcomes to enrolments."""

from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("enrollments", sa.Column("final_outcome", sa.String(), nullable=True))
    op.add_column("enrollments", sa.Column("final_mark", sa.Float(), nullable=True))
    op.add_column("enrollments", sa.Column("outcome_recorded_at", sa.DateTime(), nullable=True))
    op.add_column("enrollments", sa.Column("outcome_recorded_by", sa.Integer(), nullable=True))
    op.create_index("ix_enrollments_final_outcome", "enrollments", ["final_outcome"])
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_enrollments_outcome_recorded_by_users",
            "enrollments", "users", ["outcome_recorded_by"], ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_enrollments_outcome_recorded_by_users", "enrollments", type_="foreignkey")
    op.drop_index("ix_enrollments_final_outcome", table_name="enrollments")
    op.drop_column("enrollments", "outcome_recorded_by")
    op.drop_column("enrollments", "outcome_recorded_at")
    op.drop_column("enrollments", "final_mark")
    op.drop_column("enrollments", "final_outcome")
