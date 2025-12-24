# File: src/cashpilot/core/line_items.py
"""Line item helpers for bank transfers and expenses."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.cash_session import CashSession
from cashpilot.models.expense_item import ExpenseItem
from cashpilot.models.transfer_item import TransferItem


async def sync_session_totals(session: CashSession, db: AsyncSession) -> None:
    """Recalculate bank_transfer_total and expenses from items.

    Does NOT commit - caller is responsible for commit.
    """
    # Sum transfer items
    transfer_sum = await db.scalar(
        select(func.sum(TransferItem.amount)).where(
            TransferItem.session_id == session.id,
            ~TransferItem.is_deleted,
        )
    )

    # Sum expense items
    expense_sum = await db.scalar(
        select(func.sum(ExpenseItem.amount)).where(
            ExpenseItem.session_id == session.id,
            ~ExpenseItem.is_deleted,
        )
    )

    # Update session
    session.bank_transfer_total = transfer_sum or Decimal(0)
    session.expenses = expense_sum or Decimal(0)

    # Debug logging
    print(f"DEBUG: sync_session_totals - transfer_sum={transfer_sum}, expense_sum={expense_sum}")
    print(f"DEBUG: Updated session.bank_transfer_total={session.bank_transfer_total}")
    print(f"DEBUG: Updated session.expenses={session.expenses}")
