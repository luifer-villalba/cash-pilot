"""Factory classes for creating test objects."""

from datetime import date as date_type, time
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.security import hash_password
from cashpilot.models.business import Business
from cashpilot.models.cash_session import CashSession
from cashpilot.models.user import User


class UserFactory:
    """Factory for creating User objects."""

    @staticmethod
    async def create(
        session: AsyncSession,
        email: str = "test@example.com",
        hashed_password: Optional[str] = None,
        first_name: str = "Test",
        last_name: str = "User",
        role: str = "CASHIER",
        is_active: bool = True,
        **kwargs,
    ) -> User:
        """Create a test user."""
        if hashed_password is None:
            hashed_password = hash_password("testpass123")

        user = User(
            id=kwargs.get("id", uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=is_active,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user


class BusinessFactory:
    """Factory for creating Business objects."""

    @staticmethod
    async def create(
        session: AsyncSession,
        name: str = "Test Farmacia",
        address: Optional[str] = "Test Address",
        phone: Optional[str] = "+595 21 123-4567",
        is_active: bool = True,
        **kwargs,
    ) -> Business:
        """Create a test business."""
        business = Business(
            id=kwargs.get("id", uuid.uuid4()),
            name=name,
            address=address,
            phone=phone,
            is_active=is_active,
        )

        session.add(business)
        await session.commit()
        await session.refresh(business)

        return business


class CashSessionFactory:
    """Factory for creating CashSession objects."""

    @staticmethod
    async def create(
        session: AsyncSession,
        business_id: Optional[uuid.UUID] = None,
        cashier_name: str = "Test Cashier",
        initial_cash: Decimal = Decimal("1000000.00"),
        session_date: Optional[date_type] = None,
        opened_time: Optional[time] = None,
        created_by: Optional[uuid.UUID] = None,
        status: str = "OPEN",
        final_cash: Optional[Decimal] = None,
        envelope_amount: Decimal = Decimal("0.00"),
        credit_card_total: Decimal = Decimal("0.00"),
        debit_card_total: Decimal = Decimal("0.00"),
        bank_transfer_total: Decimal = Decimal("0.00"),
        expenses: Decimal = Decimal("0.00"),
        closed_time: Optional[time] = None,
        closing_ticket: Optional[str] = None,
        notes: Optional[str] = None,
        last_modified_at: Optional[str] = None,
        last_modified_by: Optional[str] = None,
        **kwargs,
    ) -> CashSession:
        """Create a test cash session."""
        if business_id is None:
            business = await BusinessFactory.create(session)
            business_id = business.id

        # If created_by not provided, create a default user
        if created_by is None:
            user = await UserFactory.create(session, email=f"cashier_{uuid.uuid4().hex[:8]}@test.com")
            created_by = user.id

        if session_date is None:
            session_date = date_type.today()

        if opened_time is None:
            opened_time = time(9, 0)

        cash_session = CashSession(
            id=kwargs.get("id", uuid.uuid4()),
            business_id=business_id,
            created_by=created_by,
            cashier_name=cashier_name,
            initial_cash=initial_cash,
            session_date=session_date,
            opened_time=opened_time,
            status=status,
            final_cash=final_cash,
            envelope_amount=envelope_amount,
            credit_card_total=credit_card_total,
            debit_card_total=debit_card_total,
            bank_transfer_total=bank_transfer_total,
            expenses=expenses,
            closed_time=closed_time,
            closing_ticket=closing_ticket,
            notes=notes,
            last_modified_at=last_modified_at,
            last_modified_by=last_modified_by,
        )

        session.add(cash_session)
        await session.commit()
        await session.refresh(cash_session)

        return cash_session
