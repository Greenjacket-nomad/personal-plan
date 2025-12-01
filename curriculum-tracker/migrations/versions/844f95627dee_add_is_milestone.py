"""add_is_milestone

Revision ID: 844f95627dee
Revises: 
Create Date: 2025-12-01 19:21:27.557817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '844f95627dee'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_milestone column to resources table
    op.execute("ALTER TABLE resources ADD COLUMN is_milestone BOOLEAN DEFAULT FALSE;")
    
    # Data backfill: Set is_milestone = TRUE for existing Day 6 resources (Build Days)
    op.execute("UPDATE resources SET is_milestone = TRUE WHERE day = 6;")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove is_milestone column
    op.execute("ALTER TABLE resources DROP COLUMN is_milestone;")
