# File: src/cashpilot/scripts/create_user.py
"""Script to create a new user via CLI."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.core.security import hash_password
from cashpilot.models.business import Business
from cashpilot.models.user import User, UserRole


def get_user_input():
    """Collect user information from CLI input."""
    print("\n🔐 Create New User\n")

    email = input("Email: ").strip()
    password = input("Password: ").strip()
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()

    role_input = input("Role (admin/cashier) [cashier]: ").strip().lower()
    role = UserRole.ADMIN if role_input == "admin" else UserRole.CASHIER

    return email, password, first_name, last_name, role


async def check_user_exists(db, email):
    """Check if user with email already exists."""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def generate_unique_username(db: AsyncSession, email: str) -> str:
    """Generate unique username from email prefix."""
    base_username = email.split('@')[0].lower()[:50]
    username = base_username
    counter = 2

    while True:
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            return username
        username = f"{base_username}{counter}"[:50]
        counter += 1


async def create_user_record(db, email, password, first_name, last_name, role):
    """Create and return new user record."""
    username = await generate_unique_username(db, email)

    user = User(
        email=email.lower(),
        username=username,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, ["businesses"])
    return user


async def fetch_businesses(db):
    """Fetch all active businesses."""
    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    return result.scalars().all()


def display_businesses(businesses):
    """Display list of available businesses."""
    print(f"\n📋 Available Businesses ({len(businesses)}):")
    for idx, biz in enumerate(businesses, 1):
        print(f"   {idx}. {biz.name} ({biz.id})")


def get_business_selection():
    """Get user's business assignment selection."""
    assign_input = input("\nAssign businesses? (y/n) [n]: ").strip().lower()
    if assign_input != "y":
        return None

    print("Enter business numbers separated by commas (e.g., 1,3,4) or 'all':")
    return input("> ").strip()


def parse_business_selection(selection, businesses):
    """Parse selection string and return list of selected businesses."""
    if selection.lower() == "all":
        return businesses, True

    try:
        indices = [int(x.strip()) for x in selection.split(",")]
        selected = [businesses[i - 1] for i in indices if 1 <= i <= len(businesses)]
        return selected, False
    except (ValueError, IndexError):
        return [], False


async def assign_businesses_to_user(user, businesses, is_all):
    """Assign selected businesses to user."""
    for biz in businesses:
        user.businesses.append(biz)

    if is_all:
        print(f"✅ Assigned all {len(businesses)} businesses")
    else:
        print(f"✅ Assigned {len(businesses)} business(es):")
        for biz in businesses:
            print(f"   - {biz.name}")


async def handle_cashier_assignments(db, user):
    """Handle business assignments for cashier users."""
    businesses = await fetch_businesses(db)

    if not businesses:
        print("\n⚠️  No businesses available for assignment")
        print("   Create businesses first with: make create-business")
        return

    display_businesses(businesses)
    selection = get_business_selection()

    if not selection:
        return

    selected_businesses, is_all = parse_business_selection(selection, businesses)

    if not selected_businesses and not is_all:
        print("❌ Invalid selection, skipping assignment")
        return

    await assign_businesses_to_user(user, selected_businesses, is_all)


async def create_user():
    """Create a new user interactively."""
    email, password, first_name, last_name, role = get_user_input()

    async with AsyncSessionLocal() as db:
        # Check if user exists
        if await check_user_exists(db, email):
            print(f"❌ User with email {email} already exists")
            return

        # Create user
        user = await create_user_record(db, email, password, first_name, last_name, role)

        print(f"\n✅ User created: {user.display_name} ({user.email})")
        print(f"   Username: {user.username}")
        print(f"   Role: {user.role.value}")
        print(f"   ID: {user.id}")

        # Handle business assignments for cashiers
        if user.role == UserRole.CASHIER:
            await handle_cashier_assignments(db, user)

        await db.commit()
        print("\n🎉 User setup complete!\n")


if __name__ == "__main__":
    asyncio.run(create_user())
