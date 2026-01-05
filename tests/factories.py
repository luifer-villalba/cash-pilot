# File: tests/factories.py
"""Factory classes for creating test objects."""

from datetime import date as date_type, time
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.security import hash_password
from cashpilot.models.business import Business
from cashpilot.models.cash_session import CashSession
from cashpilot.models.daily_reconciliation import DailyReconciliation
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
        name: str = "Test Business",
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
        cashier_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None,
        initial_cash: Decimal = Decimal("1000000.00"),
        session_date: Optional[date_type] = None,
        opened_time: Optional[time] = None,
        status: str = "OPEN",
        final_cash: Optional[Decimal] = None,
        envelope_amount: Decimal = Decimal("0.00"),
        credit_card_total: Decimal = Decimal("0.00"),
        debit_card_total: Decimal = Decimal("0.00"),
        bank_transfer_total: Decimal = Decimal("0.00"),
        expenses: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
        closed_time: Optional[time] = None,
        closing_ticket: Optional[str] = None,
        **kwargs,
    ) -> CashSession:
        """Create a test cash session."""
        # Create business if not provided
        if business_id is None:
            business = await BusinessFactory.create(session)
            business_id = business.id

        # Create user for cashier_id if not provided
        if cashier_id is None:
            user = await UserFactory.create(
                session,
                email=f"cashier_{uuid.uuid4().hex[:8]}@test.com"
            )
            cashier_id = user.id

        # Default created_by to cashier_id
        if created_by is None:
            created_by = cashier_id

        if session_date is None:
            session_date = date_type.today()

        if opened_time is None:
            opened_time = time(9, 0)

        cash_session = CashSession(
            id=kwargs.get("id", uuid.uuid4()),
            business_id=business_id,
            cashier_id=cashier_id,
            created_by=created_by,
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
            notes=notes,
            closed_time=closed_time,
            closing_ticket=closing_ticket,
        )

        session.add(cash_session)
        await session.commit()
        await session.refresh(cash_session)

        return cash_session


class DailyReconciliationFactory:
    """Factory for creating DailyReconciliation objects."""

    @staticmethod
    async def create(
        session: AsyncSession,
        business_id: Optional[uuid.UUID] = None,
        admin_id: Optional[uuid.UUID] = None,
        date: Optional[date_type] = None,
        cash_sales: Optional[Decimal] = None,
        credit_sales: Optional[Decimal] = None,
        card_sales: Optional[Decimal] = None,
        refunds: Optional[Decimal] = None,
        total_sales: Optional[Decimal] = None,
        is_closed: bool = False,
        **kwargs,
    ) -> DailyReconciliation:
        """Create a test daily reconciliation."""
        # Create business if not provided
        if business_id is None:
            business = await BusinessFactory.create(session)
            business_id = business.id

        # Create admin user if not provided
        if admin_id is None:
            admin = await UserFactory.create(
                session,
                email=f"admin_{uuid.uuid4().hex[:8]}@test.com",
                role="ADMIN",
            )
            admin_id = admin.id

        if date is None:
            date = date_type.today()

        reconciliation = DailyReconciliation(
            id=kwargs.get("id", uuid.uuid4()),
            business_id=business_id,
            admin_id=admin_id,
            date=date,
            cash_sales=cash_sales,
            credit_sales=credit_sales,
            card_sales=card_sales,
            refunds=refunds,
            total_sales=total_sales,
            is_closed=is_closed,
        )

        session.add(reconciliation)
        await session.commit()
        await session.refresh(reconciliation)

        return reconciliation