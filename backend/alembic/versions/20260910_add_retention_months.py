"""add retention months to units"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_retention_months"
down_revision = "f99efd1945e3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("units", sa.Column("retention_months", sa.Integer(), nullable=False, server_default="24"))


def downgrade():
    op.drop_column("units", "retention_months")
