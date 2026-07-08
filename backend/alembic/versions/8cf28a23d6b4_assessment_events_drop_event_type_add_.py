"""assessment_events: drop event_type, add criteria_id, source, created_by

Revision ID: 8cf28a23d6b4
Revises: c371de738933
Create Date: 2026-07-08 11:38:27.552193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cf28a23d6b4'
down_revision: Union[str, Sequence[str], None] = 'c371de738933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enum type must be created explicitly first - passing sa.Enum(...)
    # inline to add_column does NOT auto-create the Postgres type.
    # checkfirst=True makes this safe to re-run even after a prior
    # failed/rolled-back attempt.
    event_source_enum = sa.Enum('bulk_upload', 'manual', name='eventsource')
    event_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('assessment_events', sa.Column('criteria_id', sa.Integer(), nullable=False))
    op.add_column('assessment_events', sa.Column('source', event_source_enum, nullable=False))
    op.add_column('assessment_events', sa.Column('created_by', sa.Integer(), nullable=False))

    # Named explicitly (not left as None) so downgrade() can drop them by name.
    op.create_foreign_key(
        'fk_assessment_events_criteria_id', 'assessment_events', 'criteria', ['criteria_id'], ['id']
    )
    op.create_foreign_key(
        'fk_assessment_events_created_by', 'assessment_events', 'users', ['created_by'], ['id']
    )

    op.drop_column('assessment_events', 'event_type')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('assessment_events', sa.Column('event_type', sa.VARCHAR(), autoincrement=False, nullable=False))

    op.drop_constraint('fk_assessment_events_created_by', 'assessment_events', type_='foreignkey')
    op.drop_constraint('fk_assessment_events_criteria_id', 'assessment_events', type_='foreignkey')

    op.drop_column('assessment_events', 'created_by')
    op.drop_column('assessment_events', 'source')
    op.drop_column('assessment_events', 'criteria_id')

    event_source_enum = sa.Enum('bulk_upload', 'manual', name='eventsource')
    event_source_enum.drop(op.get_bind(), checkfirst=True)