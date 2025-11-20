"""
Seed script for CashPilot demo data (date+time split version).

Creates:
- 5 FZ pharmacy branches with cashier lists
- 30 days of cash sessions with varied reconciliation outcomes
- Non-overlapping shift patterns (7am-3pm, 3pm-11pm)
"""

import asyncio
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.models import Business, CashSession

# Non-overlapping shift patterns (no conflicts)
SHIFT_PATTERNS = [
    {"start_time": time(7, 0), "end_time": time(15, 0), "name": "Turno Mañana"},
    {"start_time": time(15, 0), "end_time": time(23, 0), "name": "Turno Tarde"},
]


async def seed_businesses(db: AsyncSession) -> list[Business]:
    """Create 5 FZ pharmacy branches with cashier lists (idempotent)."""
    result = await db.execute(select(Business).limit(1))
    if result.scalar_one_or_none():
        print("ℹ️  Businesses already exist, skipping...")
        result = await db.execute(select(Business))
        return list(result.scalars().all())

    businesses = [
        Business(
            name="FZ - Sucursal 1",
            address="Quinta Avenida c/ EEUU, Asunción",
            phone="+595 21 123-4567",
            cashiers=["Felipa Peralta", "Fermina Cáceres"],
            is_active=True,
        ),
        Business(
            name="FZ - Sucursal 2",
            address="Teodoro S. Mongelos Esq. Gral. Aquino, Asunción",
            phone="+595 21 234-5678",
            cashiers=["María Samaniego", "Fernanda Samaniego"],
            is_active=True,
        ),
        Business(
            name="FZ - Sucursal 5",
            address="Paolo Alberzoni 1267, Pilar",
            phone="+595 21 345-6789",
            cashiers=["Gilda Quintana", "Nancy Pineda"],
            is_active=True,
        ),
        Business(
            name="FZ - Sucursal 6",
            address="14 de Mayo 9042, Pilar",
            phone="+595 21 456-7890",
            cashiers=["Rocío Ponce", "Marissa Bordon"],
            is_active=True,
        ),
        Business(
            name="FZ - Plaza",
            address="Bernardino Caballero esq. 14 de mayo, Pilar",
            phone="+595 21 567-8901",
            cashiers=["Sonia Borba", "Jessica Dure"],
            is_active=True,
        ),
    ]

    for business in businesses:
        db.add(business)

    await db.flush()
    print(f"✅ Created {len(businesses)} businesses with cashiers")
    return businesses


async def seed_cash_sessions(db: AsyncSession, businesses: list[Business]) -> list[CashSession]:
    """Generate 30 days of cash sessions with date+time split."""
    result = await db.execute(select(CashSession).limit(1))
    if result.scalar_one_or_none():
        print("ℹ️  Cash sessions already exist, skipping...")
        result = await db.execute(select(CashSession))
        return list(result.scalars().all())

    sessions = []
    today = datetime.now().date()

    for business in businesses:
        for days_ago in range(30, 0, -1):
            session_date = today - timedelta(days=days_ago)

            # Skip some days randomly
            if random.random() < 0.15:
                continue

            # 1-2 sessions per day per business
            num_sessions = random.choices([1, 2], weights=[0.3, 0.7])[0]

            for i in range(num_sessions):
                shift = SHIFT_PATTERNS[i % 2]

                # Base values
                initial_cash = Decimal(random.randint(500_000, 1_000_000))
                envelope_amount = Decimal(random.randint(0, 300_000))

                # Card payments
                credit_card_total = Decimal(random.randint(1_000_000, 3_000_000))
                debit_card_total = Decimal(random.randint(500_000, 2_000_000))
                bank_transfer_total = Decimal(random.randint(0, 1_000_000))

                # Determine reconciliation outcome
                outcome = random.random()

                if outcome < 0.60:  # 60% perfect match
                    difference = Decimal(0)
                elif outcome < 0.85:  # 25% small shortage
                    difference = Decimal(random.randint(-200_000, -50_000))
                elif outcome < 0.95:  # 10% small surplus
                    difference = Decimal(random.randint(10_000, 100_000))
                else:  # 5% significant shortage
                    difference = Decimal(random.randint(-500_000, -200_001))

                final_cash = initial_cash + difference

                # Determine if session is closed (last 2 days might be open)
                is_open = days_ago <= 2 and random.random() < 0.3

                # Select cashier from business's cashier list
                cashier_name = random.choice(business.cashiers)

                session = CashSession(
                    business_id=business.id,
                    cashier_name=cashier_name,
                    status="OPEN" if is_open else "CLOSED",
                    session_date=session_date,
                    opened_time=shift["start_time"],
                    closed_time=None if is_open else shift["end_time"],
                    initial_cash=initial_cash,
                    final_cash=None if is_open else final_cash,
                    envelope_amount=Decimal(0) if is_open else envelope_amount,
                    credit_card_total=Decimal(0) if is_open else credit_card_total,
                    debit_card_total=Decimal(0) if is_open else debit_card_total,
                    bank_transfer_total=Decimal(0) if is_open else bank_transfer_total,
                    expenses=Decimal(0),
                )
                sessions.append(session)
                db.add(session)

    await db.flush()
    print(f"✅ Created {len(sessions)} cash sessions")
    return sessions


async def main():
    """Run seed script."""
    print("🌱 Starting CashPilot seed script...")
    print()

    async with AsyncSessionLocal() as db:
        # Create businesses
        businesses = await seed_businesses(db)

        # Create cash sessions
        sessions = await seed_cash_sessions(db, businesses)

        # Commit all changes
        await db.commit()

    print()
    print("🎉 Seed complete!")
    print(f"   📊 Businesses: {len(businesses)}")
    print(f"   📊 Cash sessions: {len(sessions)}")

    if sessions:
        closed_sessions = [s for s in sessions if s.status == "CLOSED"]
        open_sessions = [s for s in sessions if s.status == "OPEN"]

        shortages = sum(1 for s in closed_sessions if s.cash_sales < 0)
        surpluses = sum(1 for s in closed_sessions if s.cash_sales > 0)
        matches = len(closed_sessions) - shortages - surpluses

        print()
        print("   📈 Reconciliation outcomes:")
        print(f"      ✓ Perfect matches: {matches}")
        print(f"      ⚠ Shortages: {shortages}")
        print(f"      📦 Surpluses: {surpluses}")
        print(f"      📂 Open sessions: {len(open_sessions)}")


if __name__ == "__main__":
    asyncio.run(main())
