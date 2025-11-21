"""
Seed script for CashPilot demo data (date+time split version).

Creates:
- 5 FZ pharmacy branches with cashier lists
- 30 days of cash sessions (all CLOSED, ~10% FLAGGED)
- TODAY: 75% CLOSED, 15% OPEN, 10% FLAGGED
- Daily patterns: 7AM–3PM (morning) + 3PM–11PM (afternoon)
"""

import asyncio
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.models import Business, CashSession

# Non-overlapping shift patterns (7AM–3PM, 3PM–11PM)
SHIFT_PATTERNS = [
    {"start_time": time(7, 0), "end_time": time(15, 0), "name": "Turno Mañana"},
    {"start_time": time(15, 0), "end_time": time(23, 0), "name": "Turno Tarde"},
]

# Initial cash base (~700k Gs ±150k variance)
INITIAL_CASH_BASE = 700_000
INITIAL_CASH_VARIANCE = 150_000
ENVELOPE_MIN = 2_000_000
ENVELOPE_MAX = 6_000_000


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


def generate_initial_cash() -> Decimal:
    """Generate realistic initial cash with variance."""
    variance = random.randint(-INITIAL_CASH_VARIANCE, INITIAL_CASH_VARIANCE)
    return Decimal(INITIAL_CASH_BASE + variance)


def generate_envelope_amount() -> Decimal:
    """Generate envelope amount (15% of daily transactions)."""
    return Decimal(random.randint(int(ENVELOPE_MIN), int(ENVELOPE_MAX)))


def generate_final_cash(initial_cash: Decimal) -> Decimal:
    """Generate realistic final cash based on initial + sales."""
    # Most shifts end with 20–40% more cash (normal sales)
    sales_factor = random.uniform(1.2, 1.4)
    base = float(initial_cash) * sales_factor
    # Add random variance (±5%)
    variance = random.randint(-int(base * 0.05), int(base * 0.05))
    return Decimal(int(base + variance))


def generate_payment_totals(
    envelope: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Generate realistic payment method totals."""
    total_sales = envelope / Decimal("0.4")
    card_portion = float(total_sales * Decimal("0.3"))

    credit = Decimal(str(int(card_portion * random.uniform(0.4, 0.6))))
    debit = Decimal(str(int(card_portion - float(credit))))
    transfer = Decimal(str(int(float(total_sales * Decimal("0.3")))))

    return credit, debit, transfer


def generate_status_today(shift_idx: int) -> tuple[str, bool, str | None]:
    """Generate session status for TODAY only.

    Today distribution: 75% CLOSED, 15% OPEN, 10% FLAGGED
    Returns: (status, is_flagged, flag_reason)
    """
    rand = random.random()

    if rand < 0.75:  # 75% CLOSED
        return "CLOSED", False, None
    elif rand < 0.90:  # 15% OPEN
        return "OPEN", False, None
    else:  # 10% FLAGGED
        reasons = [
            "Discrepancia en efectivo alta",
            "Desajuste de caja registradora",
            "Discrepancia de inventario",
        ]
        return "CLOSED", True, random.choice(reasons)


def generate_status_historical() -> tuple[str, bool, str | None]:
    """Generate session status for historical data (30 days ago).

    Historical distribution: ~90% CLOSED, ~10% FLAGGED
    Returns: (status, is_flagged, flag_reason)
    """
    rand = random.random()

    if rand < 0.90:  # 90% CLOSED (normal)
        return "CLOSED", False, None
    else:  # 10% FLAGGED
        reasons = [
            "Discrepancia en efectivo alta",
            "Desajuste de caja registradora",
            "Discrepancia de inventario",
        ]
        return "CLOSED", True, random.choice(reasons)


async def seed_cash_sessions(db: AsyncSession, businesses: list[Business]) -> list[CashSession]:
    """Generate 30 days of cash sessions with realistic patterns."""
    result = await db.execute(select(CashSession).limit(1))
    if result.scalar_one_or_none():
        print("ℹ️  Cash sessions already exist, skipping...")
        result = await db.execute(select(CashSession))
        return list(result.scalars().all())

    sessions = []
    today = datetime.now().date()

    # Generate exactly one session per business per shift per day (no skips)
    for business in businesses:
        for days_ago in range(30, -1, -1):  # 30 days ago → today
            session_date = today - timedelta(days=days_ago)
            is_today = days_ago == 0

            # Morning + Afternoon shifts (always 2 per day)
            for shift_idx, shift in enumerate(SHIFT_PATTERNS):
                initial_cash = generate_initial_cash()
                envelope_amount = generate_envelope_amount()
                final_cash = generate_final_cash(initial_cash)
                credit, debit, transfer = generate_payment_totals(envelope_amount)

                # Different status distributions for today vs historical
                if is_today:
                    status, is_flagged, flag_reason = generate_status_today(shift_idx)
                else:
                    status, is_flagged, flag_reason = generate_status_historical()

                closed_time = None if status == "OPEN" else shift["end_time"]
                final_cash_val = None if status == "OPEN" else final_cash

                # For OPEN sessions, zero out payment totals
                if status == "OPEN":
                    envelope_amount = Decimal(0)
                    credit = Decimal(0)
                    debit = Decimal(0)
                    transfer = Decimal(0)

                # Select cashier
                cashier_name = random.choice(business.cashiers)

                session = CashSession(
                    business_id=business.id,
                    cashier_name=cashier_name,
                    status=status,
                    session_date=session_date,
                    opened_time=shift["start_time"],
                    closed_time=closed_time,
                    initial_cash=initial_cash,
                    final_cash=final_cash_val,
                    envelope_amount=envelope_amount,
                    credit_card_total=credit,
                    debit_card_total=debit,
                    bank_transfer_total=transfer,
                    expenses=Decimal(0),
                    flagged=is_flagged,
                    flag_reason=flag_reason,
                    flagged_by="admin" if is_flagged else None,
                    notes=random.choice(
                        [
                            None,
                            "Cierre de turno rutinario.",
                            "Reembolso procesado.",
                            "Sistema POS sin conexión por 5 min.",
                        ]
                    ),
                )
                sessions.append(session)
                db.add(session)

    await db.flush()
    print(f"✅ Created {len(sessions)} cash sessions (2 per business per day)")
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
        today = datetime.now().date()
        today_sessions = [s for s in sessions if s.session_date == today]
        historical_sessions = [s for s in sessions if s.session_date < today]

        today_closed = [s for s in today_sessions if s.status == "CLOSED"]
        today_open = [s for s in today_sessions if s.status == "OPEN"]
        today_flagged = [s for s in today_closed if s.flagged]

        hist_closed = [s for s in historical_sessions if s.status == "CLOSED"]
        hist_flagged = [s for s in hist_closed if s.flagged]

        print()
        print("   📅 TODAY:")
        print(
            f"      ✓ Closed: {len(today_closed)} ({len(today_closed)
                                                    /len(today_sessions)*100:.0f}%)"
        )
        print(f"      ◯ Open: {len(today_open)} ({len(today_open)/len(today_sessions)*100:.0f}%)")
        print(f"      🚩 Flagged: {len(today_flagged)}")
        print()
        print("   📊 HISTORICAL (30 days):")
        print(f"      ✓ Closed: {len(hist_closed)}")
        print(
            f"      🚩 Flagged: {len(hist_flagged)} ({len(hist_flagged)/len(hist_closed)*100:.0f}%"
            f" of closed)"
        )


if __name__ == "__main__":
    asyncio.run(main())
