"""add_activity_log_user_id

Revision ID: adcc89019d40
Revises: 12d389eb4c51
Create Date: 2025-12-02 13:27:11.963864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adcc89019d40'
down_revision: Union[str, Sequence[str], None] = '12d389eb4c51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to activity_log table to fix data leak vulnerability."""
    conn = op.get_bind()
    
    # Step 1: Add user_id column as NULLABLE
    op.add_column('activity_log', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Step 2: Backfill existing logs with default user_id (first user or NULL)
    # Get the first user ID if exists
    result = conn.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1"))
    first_user = result.fetchone()
    
    if first_user:
        default_user_id = first_user[0]
        op.execute(f"UPDATE activity_log SET user_id = {default_user_id} WHERE user_id IS NULL")
    
    # Step 3: Make column NOT NULL and add foreign key
    op.alter_column('activity_log', 'user_id', nullable=False)
    op.create_foreign_key(
        'fk_activity_log_user',
        'activity_log',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Step 4: Add index for better query performance
    op.create_index('ix_activity_log_user_id', 'activity_log', ['user_id'])


def downgrade() -> None:
    """Remove user_id column from activity_log table."""
    op.drop_constraint('fk_activity_log_user', 'activity_log', type_='foreignkey')
    op.drop_index('ix_activity_log_user_id', 'activity_log')
    op.alter_column('activity_log', 'user_id', nullable=True)
    op.drop_column('activity_log', 'user_id')
