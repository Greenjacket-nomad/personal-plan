"""add_user_id_foreign_keys

Revision ID: a967b926756c
Revises: a9570b3d9429
Create Date: 2025-12-01 19:56:31.554601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a967b926756c'
down_revision: Union[str, Sequence[str], None] = 'a9570b3d9429'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from werkzeug.security import generate_password_hash
    
    # Step 1: Add user_id columns as NULLABLE (only if they don't exist)
    conn = op.get_bind()
    tables_to_update = ['progress', 'resources', 'time_logs', 'journal_entries', 'completed_metrics', 'blocked_days']
    
    for table in tables_to_update:
        # Check if column already exists
        result = conn.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = 'user_id'
        """))
        if not result.fetchone():
            op.add_column(table, sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Step 2: Create default "admin" user (if it doesn't exist)
    # Use pbkdf2:sha256 method to avoid scrypt issues on older Python versions
    conn = op.get_bind()
    # Check if admin user already exists
    result = conn.execute(sa.text("SELECT id FROM users WHERE username = 'admin'"))
    existing_user = result.fetchone()
    
    if existing_user:
        default_user_id = existing_user[0]
    else:
        password_hash = generate_password_hash('changeme', method='pbkdf2:sha256')
        result = conn.execute(sa.text("""
            INSERT INTO users (username, password_hash) 
            VALUES ('admin', :password_hash) 
            RETURNING id
        """), {'password_hash': password_hash})
        default_user_id = result.fetchone()[0]
        conn.commit()
    
    # Step 3: Backfill all existing rows with default user_id
    op.execute(f"UPDATE progress SET user_id = {default_user_id} WHERE user_id IS NULL")
    op.execute(f"UPDATE resources SET user_id = {default_user_id} WHERE user_id IS NULL")
    op.execute(f"UPDATE time_logs SET user_id = {default_user_id} WHERE user_id IS NULL")
    op.execute(f"UPDATE journal_entries SET user_id = {default_user_id} WHERE user_id IS NULL")
    op.execute(f"UPDATE completed_metrics SET user_id = {default_user_id} WHERE user_id IS NULL")
    op.execute(f"UPDATE blocked_days SET user_id = {default_user_id} WHERE user_id IS NULL")
    
    # Step 4: Make columns NOT NULL and add foreign keys
    op.alter_column('progress', 'user_id', nullable=False)
    op.alter_column('resources', 'user_id', nullable=False)
    op.create_foreign_key('fk_resources_user', 'resources', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('time_logs', 'user_id', nullable=False)
    op.create_foreign_key('fk_time_logs_user', 'time_logs', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('journal_entries', 'user_id', nullable=False)
    op.create_foreign_key('fk_journal_user', 'journal_entries', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('completed_metrics', 'user_id', nullable=False)
    op.create_foreign_key('fk_metrics_user', 'completed_metrics', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('blocked_days', 'user_id', nullable=False)
    op.create_foreign_key('fk_blocked_days_user', 'blocked_days', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # Step 5: Update progress table - make user_id unique (one progress record per user)
    op.execute("ALTER TABLE progress DROP CONSTRAINT IF EXISTS progress_pkey")
    op.execute("ALTER TABLE progress ADD PRIMARY KEY (user_id)")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign keys
    op.drop_constraint('fk_blocked_days_user', 'blocked_days', type_='foreignkey')
    op.drop_constraint('fk_metrics_user', 'completed_metrics', type_='foreignkey')
    op.drop_constraint('fk_journal_user', 'journal_entries', type_='foreignkey')
    op.drop_constraint('fk_time_logs_user', 'time_logs', type_='foreignkey')
    op.drop_constraint('fk_resources_user', 'resources', type_='foreignkey')
    
    # Set columns to nullable
    op.alter_column('blocked_days', 'user_id', nullable=True)
    op.alter_column('completed_metrics', 'user_id', nullable=True)
    op.alter_column('journal_entries', 'user_id', nullable=True)
    op.alter_column('time_logs', 'user_id', nullable=True)
    op.alter_column('resources', 'user_id', nullable=True)
    op.alter_column('progress', 'user_id', nullable=True)
    
    # Restore progress primary key
    op.execute("ALTER TABLE progress DROP CONSTRAINT IF EXISTS progress_pkey")
    op.execute("ALTER TABLE progress ADD PRIMARY KEY (id)")
    
    # Drop user_id columns
    op.drop_column('blocked_days', 'user_id')
    op.drop_column('completed_metrics', 'user_id')
    op.drop_column('journal_entries', 'user_id')
    op.drop_column('time_logs', 'user_id')
    op.drop_column('resources', 'user_id')
    op.drop_column('progress', 'user_id')
