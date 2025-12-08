# File: src/cashpilot/scripts/assign-cashiers.py

"""Script to assign businesses to cashiers via CLI."""

import asyncio

from sqlalchemy import select

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.models.business import Business
from cashpilot.models.user import User, UserRole
from cashpilot.models.user_business import UserBusiness


async def fetch_cashiers(db):
    """Fetch all active cashiers."""
    stmt = (
        select(User)
        .where(User.role == UserRole.CASHIER, User.is_active is True)
        .order_by(User.first_name, User.last_name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def fetch_businesses(db):
    """Fetch all active businesses."""
    stmt = select(Business).where(Business.is_active is True).order_by(Business.name)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_assignment_count(db, cashier_id):
    """Get count of business assignments for a cashier."""
    stmt = select(UserBusiness).where(UserBusiness.user_id == cashier_id)
    result = await db.execute(stmt)
    return len(result.scalars().all())


async def get_current_assignments(db, cashier_id):
    """Get current business assignments for a cashier."""
    stmt = select(UserBusiness).where(UserBusiness.user_id == cashier_id)
    result = await db.execute(stmt)
    return result.scalars().all()


def display_cashiers(cashiers, assignments_count):
    """Display list of cashiers with assignment counts."""
    print(f"📋 Available Cashiers ({len(cashiers)}):")
    for idx, cashier in enumerate(cashiers, 1):
        count = assignments_count.get(cashier.id, 0)
        assigned = f"{count} assigned" if count > 0 else "none"
        print(f"   {idx}. {cashier.display_name} ({cashier.email}) - {assigned}")


def display_current_assignments(assignments, businesses):
    """Display current assignments for selected cashier."""
    if assignments:
        print(f"📌 Current assignments ({len(assignments)}):")
        for assignment in assignments:
            biz = next((b for b in businesses if b.id == assignment.business_id), None)
            if biz:
                print(f"   - {biz.name}")
    else:
        print("📌 No current assignments")


def display_businesses(businesses, current_business_ids):
    """Display all businesses with assignment markers."""
    print(f"\n🏪 Available Businesses ({len(businesses)}):")
    for idx, biz in enumerate(businesses, 1):
        is_assigned = biz.id in current_business_ids
        marker = "✓" if is_assigned else " "
        print(f"   [{marker}] {idx}. {biz.name} ({biz.id})")


def get_user_selection():
    """Get and parse user's business selection input."""
    print("\nOptions:")
    print("  - Enter numbers separated by commas (e.g., 1,2,3) to REPLACE assignments")
    print("  - Enter 'all' to assign all businesses")
    print("  - Enter 'none' to remove all assignments")
    print("  - Press Enter to keep current assignments")
    return input("> ").strip()


async def clear_assignments(db, assignments):
    """Remove all current assignments."""
    for assignment in assignments:
        await db.delete(assignment)


async def add_assignments(db, cashier_id, businesses):
    """Add business assignments for cashier."""
    for biz in businesses:
        ub = UserBusiness(user_id=cashier_id, business_id=biz.id)
        db.add(ub)


async def process_assignment_selection(db, selection, cashier_id, assignments, businesses):
    """Process user's assignment selection and update database."""
    if not selection:
        print("✅ No changes made")
        return False

    if selection.lower() == "none":
        await clear_assignments(db, assignments)
        print("✅ Removed all business assignments")
        return True

    if selection.lower() == "all":
        await clear_assignments(db, assignments)
        await add_assignments(db, cashier_id, businesses)
        print(f"✅ Assigned all {len(businesses)} businesses")
        return True

    try:
        indices = [int(x.strip()) for x in selection.split(",")]
        new_assignments = [businesses[i - 1] for i in indices if 1 <= i <= len(businesses)]

        await clear_assignments(db, assignments)
        await add_assignments(db, cashier_id, new_assignments)

        print(f"✅ Updated assignments ({len(new_assignments)} businesses):")
        for biz in new_assignments:
            print(f"   - {biz.name}")
        return True
    except (ValueError, IndexError):
        print("❌ Invalid selection")
        return False


async def assign_cashiers():
    """Assign businesses to cashiers interactively."""
    print("\n👥 Assign Businesses to Cashiers\n")

    async with AsyncSessionLocal() as db:
        # Fetch data
        cashiers = await fetch_cashiers(db)
        if not cashiers:
            print("❌ No cashiers found. Create cashiers first with: make create-user")
            return

        businesses = await fetch_businesses(db)
        if not businesses:
            print("❌ No businesses found. Create businesses first with: make create-business")
            return

        # Get assignment counts
        assignments_count = {}
        for cashier in cashiers:
            assignments_count[cashier.id] = await get_assignment_count(db, cashier.id)

        # Display and select cashier
        display_cashiers(cashiers, assignments_count)

        print("\nSelect cashier number:")
        try:
            cashier_idx = int(input("> ").strip())
            if not (1 <= cashier_idx <= len(cashiers)):
                print("❌ Invalid cashier number")
                return
            selected_cashier = cashiers[cashier_idx - 1]
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Cancelled")
            return

        print(f"\n✅ Selected: {selected_cashier.display_name}")

        # Get and display current assignments
        current_assignments = await get_current_assignments(db, selected_cashier.id)
        current_business_ids = {a.business_id for a in current_assignments}

        display_current_assignments(current_assignments, businesses)
        display_businesses(businesses, current_business_ids)

        # Get user selection and process
        selection = get_user_selection()
        updated = await process_assignment_selection(
            db, selection, selected_cashier.id, current_assignments, businesses
        )

        if updated:
            await db.commit()
            print(f"\n🎉 Assignments updated for {selected_cashier.display_name}\n")


if __name__ == "__main__":
    asyncio.run(assign_cashiers())
