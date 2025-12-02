"""remove_default_admin_backdoor

Revision ID: e77e52c09a87
Revises: adcc89019d40
Create Date: 2025-12-02 13:29:56.518252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e77e52c09a87'
down_revision: Union[str, Sequence[str], None] = 'adcc89019d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove default admin backdoor by changing password if default 'changeme' is still in use.
    
    This migration addresses a security vulnerability where the default admin user
    may have the hardcoded password 'changeme'. If the admin user exists and still
    has this password, it will be changed to a secure random value, effectively
    disabling the account until a new password is set.
    """
    from werkzeug.security import check_password_hash, generate_password_hash
    import secrets
    
    conn = op.get_bind()
    
    # Check if admin user exists
    result = conn.execute(sa.text("SELECT id, password_hash FROM users WHERE username = 'admin'"))
    admin_user = result.fetchone()
    
    if admin_user:
        admin_id, current_hash = admin_user[0], admin_user[1]
        
        # Check if password is still the default 'changeme'
        if check_password_hash(current_hash, 'changeme'):
            # Generate a secure random password that nobody knows
            # This effectively disables the account until a proper password is set
            random_password = secrets.token_urlsafe(32)
            new_hash = generate_password_hash(random_password, method='pbkdf2:sha256')
            
            # Update the password to the random value
            conn.execute(sa.text("""
                UPDATE users 
                SET password_hash = :new_hash 
                WHERE id = :admin_id
            """), {'new_hash': new_hash, 'admin_id': admin_id})
            
            conn.commit()
            
            # Log a warning (in production, this should be logged to a security log)
            print("SECURITY WARNING: Default admin password was changed. Account is now disabled.")
            print("Please set a new password for the admin user through proper channels.")


def downgrade() -> None:
    """Downgrade schema - cannot restore default password for security reasons."""
    # Intentionally empty - we should never restore a known password
    pass
