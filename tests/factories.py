"""Factory classes for creating test data."""

from datetime import date, time
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models import Business, CashSession


class BusinessFactory:
    """Factory for creating test Business instances."""

    @staticmethod
    async def create(db: AsyncSession, **kwargs: Any) -> Business:
        """Create and persist a Business."""
        defaults = {
            "id": uuid4(),
            "name": f"Test Pharmacy {uuid4().hex[:8]}",
            "address": "123 Test St",
            "phone": "555-0123",
            "is_active": True,
        }
        defaults.update(kwargs)

        business = Business(**defaults)
        db.add(business)
        await db.commit()
        await db.refresh(business)
        return business


class CashSessionFactory:
    """Factory for creating test CashSession instances."""

    @staticmethod
    async def create(db: AsyncSession, **kwargs: Any) -> CashSession:
        """Create and persist a CashSession."""
        defaults = {
            "id": uuid4(),
            "business_id": uuid4(),
            "status": "OPEN",
            "cashier_name": f"Cashier {uuid4().hex[:6]}",
            "session_date": date.today(),
            "opened_time": time(9, 0),
            "closed_time": None,
            "initial_cash": Decimal("1000.00"),
            "final_cash": None,
            "envelope_amount": Decimal("0.00"),
            "credit_card_total": Decimal("0.00"),
            "debit_card_total": Decimal("0.00"),
            "bank_transfer_total": Decimal("0.00"),
            "expenses": Decimal("0.00"),
            "closing_ticket": None,
            "notes": None,
            "has_conflict": False,
            "last_modified_at": None,
            "last_modified_by": None,
        }
        defaults.update(kwargs)

        session = CashSession(**defaults)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
