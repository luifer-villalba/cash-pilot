"""merge_card_totals_into_single_field

Revision ID: e7f8a9b0c1d2
Revises: cce21123ed07
Create Date: 2026-01-08 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'cce21123ed07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Combine credit_card_total and debit_card_total into a single card_total field."""
    # Add new card_total column as nullable first
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('card_total', sa.Numeric(precision=12, scale=2), nullable=True))

    # Migrate data: card_total = credit_card_total + debit_card_total
    op.execute("""
        UPDATE cash_sessions 
        SET card_total = COALESCE(credit_card_total, 0.00) + COALESCE(debit_card_total, 0.00)
    """)

    # Set default value for any remaining NULL values (shouldn't happen, but just in case)
    op.execute("UPDATE cash_sessions SET card_total = 0.00 WHERE card_total IS NULL")

    # Now make card_total NOT NULL
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.alter_column('card_total', nullable=False)

    # Drop the old columns
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_column('debit_card_total')
        batch_op.drop_column('credit_card_total')


def downgrade() -> None:
    """Split card_total back into credit_card_total and debit_card_total.
    
    Note: This downgrade will split the card_total 50/50 between credit and debit,
    as the original split information is lost after the upgrade.
    """
    # Add back the old columns as nullable first
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('credit_card_total', sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column('debit_card_total', sa.Numeric(precision=12, scale=2), nullable=True))

    # Restore data: split card_total 50/50 (we can't know the original split)
    op.execute("""
        UPDATE cash_sessions 
        SET credit_card_total = COALESCE(card_total, 0.00) / 2,
            debit_card_total = COALESCE(card_total, 0.00) / 2
    """)

    # Set default values for any NULL values
    op.execute("UPDATE cash_sessions SET credit_card_total = 0.00 WHERE credit_card_total IS NULL")
    op.execute("UPDATE cash_sessions SET debit_card_total = 0.00 WHERE debit_card_total IS NULL")

    # Make them NOT NULL
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.alter_column('credit_card_total', nullable=False)
        batch_op.alter_column('debit_card_total', nullable=False)

    # Drop the card_total column
    with op.batch_alter_table('cash_sessions', schema=None) as batch_op:
        batch_op.drop_column('card_total')
