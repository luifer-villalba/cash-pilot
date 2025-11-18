"""add_cashiers_json_to_businesses

Revision ID: 68c3404d57c9
Revises: 028e5ee441f3
Create Date: 2025-11-18 02:31:44.102805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '68c3404d57c9'
down_revision: Union[str, None] = '028e5ee441f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cashiers column as nullable first
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cashiers', sa.JSON(), nullable=True))

    # Set default empty array for existing records
    op.execute("UPDATE businesses SET cashiers = '[]'::json WHERE cashiers IS NULL")

    # Make NOT NULL now that all rows have values
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.alter_column('cashiers', nullable=False)

    # Handle other changes
    with op.batch_alter_table('cash_session_audit_logs', schema=None) as batch_op:
        batch_op.drop_constraint('cash_session_audit_logs_session_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cash_sessions', ['session_id'], ['id'])

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('users_email_key', type_='unique')


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_unique_constraint('users_email_key', ['email'])

    with op.batch_alter_table('cash_session_audit_logs', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('cash_session_audit_logs_session_id_fkey', 'cash_sessions', ['session_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_column('cashiers')