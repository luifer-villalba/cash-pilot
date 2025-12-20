"""Seed script for CashPilot demo data."""

import asyncio
import random
from datetime import time, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.models import Business, CashSession, User
from cashpilot.models.user import UserRole
from cashpilot.utils.datetime import today_local

SHIFT_PATTERNS = [
    {"start_time": time(7, 0), "end_time": time(15, 0), "name": "Turno Mañana"},
    {"start_time": time(15, 0), "end_time": time(23, 0), "name": "Turno Tarde"},
]

CASHIER_POOL = [
    ("María", "González"),
    ("Juan", "Pérez"),
    ("Carmen", "Rodríguez"),
    ("Luis", "Martínez"),
    ("Ana", "Silva"),
    ("Carlos", "Benítez"),
]


async def seed_users(db: AsyncSession) -> dict[str, User]:
    """Create cashier users (one per name in CASHIER_POOL)."""
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        print("ℹ️  Users already exist, skipping...")
        result = await db.execute(select(User))
        return {f"{u.first_name} {u.last_name}": u for u in result.scalars().all()}

    users = {}
    for first_name, last_name in CASHIER_POOL:
        email = f"{first_name.lower()}.{last_name.lower()}@farmacia.local"
        user = User(
            id=uuid4(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.CASHIER,
            is_active=True,
        )
        # Set a demo password hash (use a simple one for seeding)
        user.hashed_password = "demo_hash_change_in_prod"
        users[f"{first_name} {last_name}"] = user
        db.add(user)

    await db.flush()
    print(f"✅ Created {len(users)} cashier users")
    return users


async def seed_businesses(db: AsyncSession) -> list[Business]:
    """Create businesses."""
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


async def seed_cash_sessions(
    db: AsyncSession, businesses: list[Business], users: dict[str, User]
) -> list[CashSession]:
    """Generate 30 days of cash sessions with realistic reconciliation data."""
    sessions = []
    user_list = list(users.values())

    base_date = today_local() - timedelta(days=30)

    for business in businesses:
        for day_offset in range(30):
            session_date = base_date + timedelta(days=day_offset)

            for shift in SHIFT_PATTERNS:
                cashier = random.choice(user_list)
                is_closed = random.random() > 0.3  # 70% closed, 30% open

                # Realistic sales distribution
                initial_cash = Decimal(random.randint(200000, 600000))

                if is_closed:
                    # Generate realistic payment breakdown
                    cash_sales = Decimal(random.randint(300000, 1500000))
                    final_cash = initial_cash + cash_sales
                    envelope_amount = Decimal(random.randint(50000, 300000))
                    credit_card_total = Decimal(random.randint(200000, 800000))
                    debit_card_total = Decimal(random.randint(100000, 500000))
                    bank_transfer_total = Decimal(random.randint(50000, 300000))
                else:
                    final_cash = None
                    envelope_amount = Decimal(0)
                    credit_card_total = Decimal(0)
                    debit_card_total = Decimal(0)
                    bank_transfer_total = Decimal(0)

                session = CashSession(
                    id=uuid4(),
                    business_id=business.id,
                    cashier_id=cashier.id,
                    initial_cash=initial_cash,
                    final_cash=final_cash,
                    envelope_amount=envelope_amount,
                    credit_card_total=credit_card_total,
                    debit_card_total=debit_card_total,
                    bank_transfer_total=bank_transfer_total,
                    expenses=Decimal(random.randint(0, 50000)) if is_closed else Decimal(0),
                    credit_sales_total=(
                        Decimal(random.randint(50000, 300000)) if is_closed else Decimal(0)
                    ),
                    credit_payments_collected=(
                        Decimal(random.randint(30000, 200000)) if is_closed else Decimal(0)
                    ),
                    session_date=session_date,
                    opened_time=shift["start_time"],
                    closed_time=shift["end_time"] if is_closed else None,
                    status="CLOSED" if is_closed else "OPEN",
                    notes=f"Seed: {cashier.first_name} {cashier.last_name} - {shift['name']}",
                )
                sessions.append(session)
                db.add(session)

    await db.flush()
    print(f"✅ Created {len(sessions)} cash sessions with reconciliation data")
    return sessions


async def main():
    """Run seed script."""
    print("🌱 Starting CashPilot seed script...\n")

    async with AsyncSessionLocal() as db:
        users = await seed_users(db)
        businesses = await seed_businesses(db)
        sessions = await seed_cash_sessions(db, businesses, users)
        await db.commit()

    print("\n🎉 Seed complete!")
    print(f"   👥 Users: {len(users)}")
    print(f"   🏪 Businesses: {len(businesses)}")
    print(f"   📊 Sessions: {len(sessions)}")


if __name__ == "__main__":
    asyncio.run(main())
