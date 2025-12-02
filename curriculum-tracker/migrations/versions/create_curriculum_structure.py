"""create_curriculum_structure

Revision ID: create_curriculum_structure
Revises: a967b926756c
Create Date: 2025-12-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'create_curriculum_structure'
down_revision: Union[str, Sequence[str], None] = 'a967b926756c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add dynamic curriculum structure."""
    
    # Create phases table
    op.create_table(
        'phases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('color', sa.Text(), server_default='#6366f1'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_phases_user_id', 'phases', ['user_id'])
    op.create_index('ix_phases_order_index', 'phases', ['order_index'])
    op.create_unique_constraint('uq_phases_user_order', 'phases', ['user_id', 'order_index'])
    
    # Create weeks table
    op.create_table(
        'weeks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phase_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['phase_id'], ['phases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_weeks_user_id', 'weeks', ['user_id'])
    op.create_index('ix_weeks_phase_id', 'weeks', ['phase_id'])
    op.create_index('ix_weeks_order_index', 'weeks', ['order_index'])
    # CRITICAL: Unique constraint with user_id, phase_id, order_index
    op.create_unique_constraint('uq_weeks_user_phase_order', 'weeks', ['user_id', 'phase_id', 'order_index'])
    
    # Create days table
    op.create_table(
        'days',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('week_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['week_id'], ['weeks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_days_user_id', 'days', ['user_id'])
    op.create_index('ix_days_week_id', 'days', ['week_id'])
    op.create_index('ix_days_order_index', 'days', ['order_index'])
    op.create_unique_constraint('uq_days_user_week_order', 'days', ['user_id', 'week_id', 'order_index'])
    
    # Add day_id column to resources table (nullable FK)
    op.add_column('resources', sa.Column('day_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_resources_day', 'resources', 'days', ['day_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_resources_day_id', 'resources', ['day_id'])


def downgrade() -> None:
    """Downgrade schema - remove curriculum structure."""
    
    # Remove day_id from resources
    op.drop_constraint('fk_resources_day', 'resources', type_='foreignkey')
    op.drop_index('ix_resources_day_id', 'resources')
    op.drop_column('resources', 'day_id')
    
    # Drop days table
    op.drop_table('days')
    
    # Drop weeks table
    op.drop_table('weeks')
    
    # Drop phases table
    op.drop_table('phases')
