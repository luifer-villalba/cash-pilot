"""Seed database with sample data for development and demo."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.models import Business, CashSession


async def clear_data():
    """Clear existing data (for development only)."""
    async with AsyncSessionLocal() as session:
        await session.execute("DELETE FROM cash_sessions")
        await session.execute("DELETE FROM businesses")
        await session.commit()
    print("✅ Cleared existing data")


async def seed_businesses():
    """Create sample businesses."""
    businesses = [
        Business(
            name="Farmacia Central",
            address="Av. Mariscal López 1234, Asunción",
            phone="+595 21 123-4567",
            is_active=True,
        ),
        Business(
            name="Farmacia Villa Morra",
            address="Av. San Martín 5678, Asunción",
            phone="+595 21 987-6543",
            is_active=True,
        ),
    ]

    async with AsyncSessionLocal() as session:
        session.add_all(businesses)
        await session.commit()
        for biz in businesses:
            await session.refresh(biz)

    print(f"✅ Created {len(businesses)} businesses")
    return businesses


async def seed_cash_sessions(businesses: list[Business]):
    """Create realistic cash sessions."""

    biz1, biz2 = businesses
    base_date = datetime.now() - timedelta(days=7)

    sessions = [
        # Session 1: Perfect reconciliation (no shortage/surplus)
        CashSession(
            business_id=biz1.id,
            cashier_name="María González",
            shift_hours="08:00-16:00",
            opened_at=base_date,
            closed_at=base_date + timedelta(hours=8),
            status="CLOSED",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("3500000.00"),
            envelope_amount=Decimal("1000000.00"),
            credit_card_total=Decimal("800000.00"),
            debit_card_total=Decimal("600000.00"),
            bank_transfer_total=Decimal("200000.00"),
            closing_ticket="TKT-001",
            notes="Turno tranquilo, sin problemas",
        ),
        # Session 2: High cash sales day
        CashSession(
            business_id=biz1.id,
            cashier_name="Juan Pérez",
            shift_hours="16:00-22:00",
            opened_at=base_date + timedelta(days=1),
            closed_at=base_date + timedelta(days=1, hours=6),
            status="CLOSED",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("6500000.00"),
            envelope_amount=Decimal("2000000.00"),
            credit_card_total=Decimal("1200000.00"),
            debit_card_total=Decimal("900000.00"),
            bank_transfer_total=Decimal("400000.00"),
            closing_ticket="TKT-002",
            notes="Viernes muy movido, muchas ventas",
        ),
        # Session 3: Mostly card payments
        CashSession(
            business_id=biz2.id,
            cashier_name="Ana Silva",
            shift_hours="08:00-16:00",
            opened_at=base_date + timedelta(days=2),
            closed_at=base_date + timedelta(days=2, hours=8),
            status="CLOSED",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("1800000.00"),
            envelope_amount=Decimal("500000.00"),
            credit_card_total=Decimal("2500000.00"),
            debit_card_total=Decimal("1800000.00"),
            bank_transfer_total=Decimal("700000.00"),
            closing_ticket="TKT-003",
            notes="Mayoría pagó con tarjeta",
        ),
        # Session 4: Large bank transfer
        CashSession(
            business_id=biz2.id,
            cashier_name="Carlos Ramírez",
            shift_hours="16:00-22:00",
            opened_at=base_date + timedelta(days=3),
            closed_at=base_date + timedelta(days=3, hours=6),
            status="CLOSED",
            initial_cash=Decimal("500000.00"),
            final_cash=Decimal("2200000.00"),
            envelope_amount=Decimal("800000.00"),
            credit_card_total=Decimal("600000.00"),
            debit_card_total=Decimal("400000.00"),
            bank_transfer_total=Decimal("3500000.00"),
            closing_ticket="TKT-004",
            notes="Cliente hizo transferencia grande por medicamento especial",
        ),
        # Session 5: Currently OPEN (in progress)
        CashSession(
            business_id=biz1.id,
            cashier_name="María González",
            shift_hours="08:00-16:00",
            opened_at=datetime.now() - timedelta(hours=2),
            status="OPEN",
            initial_cash=Decimal("500000.00"),
            final_cash=None,
            envelope_amount=Decimal("0.00"),
            credit_card_total=Decimal("0.00"),
            debit_card_total=Decimal("0.00"),
            bank_transfer_total=Decimal("0.00"),
        ),
    ]

    async with AsyncSessionLocal() as session:
        session.add_all(sessions)
        await session.commit()

    print(f"✅ Created {len(sessions)} cash sessions")
    print("   - 4 closed sessions (realistic scenarios)")
    print("   - 1 open session (in progress)")


async def main():
    """Run all seed functions."""
    print("🌱 Starting database seed...")

    # Optional: clear existing data
    # await clear_data()

    businesses = await seed_businesses()
    await seed_cash_sessions(businesses)

    print("\n✅ Seed complete!")
    print("\n📊 Summary:")
    print("   - 2 pharmacies (Farmacia Central, Farmacia Villa Morra)")
    print("   - 5 cash sessions (4 closed, 1 open)")
    print("   - Various scenarios: perfect day, high volume, card-heavy, large transfer")
    print("\n💡 Test with: GET /cash-sessions or GET /businesses")


if __name__ == "__main__":
    asyncio.run(main())
