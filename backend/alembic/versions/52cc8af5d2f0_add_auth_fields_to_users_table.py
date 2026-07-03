"""Add auth fields to users table

Revision ID: 52cc8af5d2f0
Revises: 2fb9fa009e7d
Create Date: 2026-07-03 14:35:31.755081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52cc8af5d2f0'
down_revision: Union[str, Sequence[str], None] = '2fb9fa009e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type first
    userrole = sa.Enum('SUPER_ADMIN', 'ADMIN', 'LECTURER', name='userrole')
    userrole.create(op.get_bind(), checkfirst=True)

    # Add new columns
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))

    # FIXED ROLE CONVERSION (IMPORTANT PART)
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN role TYPE userrole
        USING role::userrole
    """)

    # Ensure not null + default
    op.alter_column('users', 'role', nullable=False)

def downgrade() -> None:
    op.alter_column('users', 'role', type_=sa.VARCHAR())

    op.drop_column('users', 'last_login')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'full_name')

    userrole = sa.Enum(name='userrole')
    userrole.drop(op.get_bind(), checkfirst=True)