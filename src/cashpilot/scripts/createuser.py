# File: src/cashpilot/scripts/createuser.py
"""Django-style createuser command for creating admin users."""

import asyncio
import sys
from getpass import getpass

from sqlalchemy import select

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password
from cashpilot.models.user import User

logger = get_logger(__name__)


def prompt_for_email() -> str:
    """Prompt for email with validation."""
    while True:
        email = input("Email address: ").strip()

        if not email:
            print("❌ Email cannot be empty")
            continue

        if "@" not in email or "." not in email:
            print("❌ Enter a valid email address")
            continue

        return email


def prompt_for_password() -> str:
    """Prompt for password with validation."""
    while True:
        password = getpass("Password: ")

        if len(password) < 8:
            print("❌ Password must be at least 8 characters")
            continue

        password_confirm = getpass("Password (confirm): ")

        if password != password_confirm:
            print("❌ Passwords don't match")
            continue

        return password


async def create_user() -> None:
    """Interactive user creation."""
    print("\n" + "=" * 50)
    print("CashPilot - Create user")
    print("=" * 50 + "\n")

    async with AsyncSessionLocal() as db:
        # Get email
        email = prompt_for_email()

        # Check if user exists
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"❌ User with email '{email}' already exists\n")
            return

        # Get password
        password = prompt_for_password()

        # Create user
        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
        )

        db.add(user)
        await db.commit()

        print("\n✅ user created successfully!")
        print(f"   Email: {email}")
        print(f"   ID: {user.id}\n")


if __name__ == "__main__":
    try:
        asyncio.run(create_user())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled\n")
        sys.exit(1)
    except Exception as e:
        logger.error("createuser_error", error=str(e))
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)
