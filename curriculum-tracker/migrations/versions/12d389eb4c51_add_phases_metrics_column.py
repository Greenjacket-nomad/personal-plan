"""add_phases_metrics_column

Revision ID: 12d389eb4c51
Revises: create_curriculum_structure
Create Date: 2025-12-02 13:11:25.897754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12d389eb4c51'
down_revision: Union[str, Sequence[str], None] = 'create_curriculum_structure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metrics column to phases table for storing success metric definitions."""
    # Add metrics column as TEXT[] array (PostgreSQL array type)
    # This stores the list of success metrics for each phase
    op.add_column('phases', sa.Column('metrics', sa.ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove metrics column from phases table."""
    op.drop_column('phases', 'metrics')
