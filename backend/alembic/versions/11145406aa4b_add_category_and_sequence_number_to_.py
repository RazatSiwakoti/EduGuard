"""add category and sequence_number to criteria

Revision ID: 11145406aa4b
Revises: 9fc3608872e6
Create Date: 2026-07-16 17:33:53.347922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11145406aa4b'
down_revision: Union[str, Sequence[str], None] = '9fc3608872e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    category_enum = sa.Enum('attendance', 'weekly_tut', 'assessment', 'moodle', name='criteriacategory')
    category_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('criteria', sa.Column('category', category_enum, nullable=True))
    op.add_column('criteria', sa.Column('sequence_number', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('criteria', 'sequence_number')
    op.drop_column('criteria', 'category')
    category_enum = sa.Enum(name='criteriacategory')
    category_enum.drop(op.get_bind(), checkfirst=True)