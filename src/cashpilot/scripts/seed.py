"""
Seed script for CashPilot demo data (date+time split version).

Creates:
- 3 pharmacy businesses
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
    """Create 3 pharmacy businesses if they don't exist (idempotent)."""
    result = await db.execute(select(Business).limit(1))
    if result.scalar_one_or_none():
        print("ℹ️  Businesses already exist, skipping...")
        result = await db.execute(select(Business))
        return list(result.scalars().all())

    businesses = [
        Business(
            name="Farmacia Central",
            address="Av. Mariscal López 1234, Asunción",
            phone="+595 21 123-4567",
            is_active=True,
        ),
        Business(
            name="Farmacia San Lorenzo",
            address="Ruta 2 Km 15, San Lorenzo",
            phone="+595 21 234-5678",
            is_active=True,
        ),
        Business(
            name="Farmacia Villa Morra",
            address="Av. San Martín 890, Villa Morra",
            phone="+595 21 345-6789",
            is_active=True,
        ),
    ]

    for business in businesses:
        db.add(business)

    await db.flush()
    print(f"✅ Created {len(businesses)} businesses")
    return businesses


async def seed_cash_sessions(db: AsyncSession, businesses: list[Business]) -> list[CashSession]:
    """Generate 30 days of cash sessions with date+time split."""
    result = await db.execute(select(CashSession).limit(1))
    if result.scalar_one_or_none():
        print("ℹ️  Cash sessions already exist, skipping...")
        result = await db.execute(select(CashSession))
        return list(result.scalars().all())

    cashier_names = [
        "María González",
        "Juan Pérez",
        "Carmen Rodríguez",
        "Luis Martínez",
        "Ana Silva",
        "Carlos Benítez",
    ]

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

                session = CashSession(
                    business_id=business.id,
                    cashier_name=random.choice(cashier_names),
                    session_date=session_date,
                    opened_time=shift["start_time"],
                    initial_cash=initial_cash,
                    envelope_amount=envelope_amount,
                    credit_card_total=credit_card_total,
                    debit_card_total=debit_card_total,
                    bank_transfer_total=bank_transfer_total,
                )

                if not is_open:
                    session.status = "CLOSED"
                    session.final_cash = final_cash
                    session.closed_time = shift["end_time"]

                    # Add optional closing notes for problematic cases
                    if difference < -200_000:
                        session.notes = "Verificar: diferencia significativa detectada"
                    elif difference > 100_000:
                        session.notes = "Revisar: excedente inusual"

                db.add(session)
                sessions.append(session)

    await db.flush()
    print(f"✅ Created {len(sessions)} cash sessions")
    return sessions


async def main():
    """Main seeding function."""
    print("🌱 Starting CashPilot seed script...\n")

    async with AsyncSessionLocal() as db:
        try:
            businesses = await seed_businesses(db)
            sessions = await seed_cash_sessions(db, businesses)

            await db.commit()

            print("\n🎉 Seed complete!")
            print(f"   📊 Businesses: {len(businesses)}")
            print(f"   📊 Cash sessions: {len(sessions)}")

        except Exception as e:
            await db.rollback()
            print(f"❌ Seed failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
