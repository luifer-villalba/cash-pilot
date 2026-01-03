"""convert_timestamp_to_timestamptz

Revision ID: a1b2c3d4e5f6
Revises: 18d57c4c9eab
Create Date: 2026-01-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '18d57c4c9eab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert all TIMESTAMP columns to TIMESTAMPTZ.
    
    This migration converts naive UTC timestamps to timezone-aware timestamps.
    All existing timestamps are assumed to be UTC and are converted using 
    'AT TIME ZONE' to preserve the actual moment in time.
    """
    
    # Businesses table
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN created_at TYPE TIMESTAMPTZ 
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN updated_at TYPE TIMESTAMPTZ 
        USING updated_at AT TIME ZONE 'UTC'
    """)
    
    # Users table
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN created_at TYPE TIMESTAMPTZ 
        USING created_at AT TIME ZONE 'UTC'
    """)
    
    # User businesses table
    op.execute("""
        ALTER TABLE user_businesses 
        ALTER COLUMN assigned_at TYPE TIMESTAMPTZ 
        USING assigned_at AT TIME ZONE 'UTC'
    """)
    
    # Cash sessions table
    # Note: NULL values are preserved during conversion (PostgreSQL handles NULL correctly)
    op.execute("""
        ALTER TABLE cash_sessions 
        ALTER COLUMN last_modified_at TYPE TIMESTAMPTZ 
        USING last_modified_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE cash_sessions 
        ALTER COLUMN deleted_at TYPE TIMESTAMPTZ 
        USING deleted_at AT TIME ZONE 'UTC'
    """)
    
    # Expense items table
    op.execute("""
        ALTER TABLE expense_items 
        ALTER COLUMN created_at TYPE TIMESTAMPTZ 
        USING created_at AT TIME ZONE 'UTC'
    """)
    
    # Transfer items table
    op.execute("""
        ALTER TABLE transfer_items 
        ALTER COLUMN created_at TYPE TIMESTAMPTZ 
        USING created_at AT TIME ZONE 'UTC'
    """)
    
    # Cash session audit logs table
    op.execute("""
        ALTER TABLE cash_session_audit_logs 
        ALTER COLUMN changed_at TYPE TIMESTAMPTZ 
        USING changed_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    """Convert TIMESTAMPTZ columns back to TIMESTAMP (not recommended)."""
    
    # Cash session audit logs table
    op.execute("""
        ALTER TABLE cash_session_audit_logs 
        ALTER COLUMN changed_at TYPE TIMESTAMP 
        USING changed_at AT TIME ZONE 'UTC'
    """)
    
    # Transfer items table
    op.execute("""
        ALTER TABLE transfer_items 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC'
    """)
    
    # Expense items table
    op.execute("""
        ALTER TABLE expense_items 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC'
    """)
    
    # Cash sessions table
    op.execute("""
        ALTER TABLE cash_sessions 
        ALTER COLUMN deleted_at TYPE TIMESTAMP 
        USING deleted_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE cash_sessions 
        ALTER COLUMN last_modified_at TYPE TIMESTAMP 
        USING last_modified_at AT TIME ZONE 'UTC'
    """)
    
    # User businesses table
    op.execute("""
        ALTER TABLE user_businesses 
        ALTER COLUMN assigned_at TYPE TIMESTAMP 
        USING assigned_at AT TIME ZONE 'UTC'
    """)
    
    # Users table
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC'
    """)
    
    # Businesses table
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN updated_at TYPE TIMESTAMP 
        USING updated_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC'
    """)
