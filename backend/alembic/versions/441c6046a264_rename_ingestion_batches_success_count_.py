"""rename ingestion_batches success_count/failure_count to values_stored/values_failed

Revision ID: 441c6046a264
Revises: 4c7c4d8af49d
Create Date: 2026-07-08 19:05:03.517880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441c6046a264'
down_revision: Union[str, Sequence[str], None] = '4c7c4d8af49d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    op.alter_column('ingestion_batches', 'success_count', new_column_name='values_stored')
    op.alter_column('ingestion_batches', 'failure_count', new_column_name='values_failed')


def downgrade() -> None:
    op.alter_column('ingestion_batches', 'values_stored', new_column_name='success_count')
    op.alter_column('ingestion_batches', 'values_failed', new_column_name='failure_count')