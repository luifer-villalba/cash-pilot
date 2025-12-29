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
    # Validate inputs
    if session is None:
        raise ValueError("Session is required")
    if db is None:
        raise ValueError("Database connection is required")
    if not hasattr(session, "id") or session.id is None:
        raise ValueError("Session must have a valid id")

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

    # Update session (validate types)
    if transfer_sum is not None and not isinstance(transfer_sum, (Decimal, int, float)):
        transfer_sum = Decimal(0)
    if expense_sum is not None and not isinstance(expense_sum, (Decimal, int, float)):
        expense_sum = Decimal(0)

    session.bank_transfer_total = Decimal(transfer_sum) if transfer_sum is not None else Decimal(0)
    session.expenses = Decimal(expense_sum) if expense_sum is not None else Decimal(0)

    # Debug logging
    print(f"DEBUG: sync_session_totals - transfer_sum={transfer_sum}, expense_sum={expense_sum}")
    print(f"DEBUG: Updated session.bank_transfer_total={session.bank_transfer_total}")
    print(f"DEBUG: Updated session.expenses={session.expenses}")
