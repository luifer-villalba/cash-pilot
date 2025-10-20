"""Seed default categories for new installations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.models.category import Category
from cashpilot.models.enums import CategoryType


async def seed_categories(db: AsyncSession) -> None:
    """Create default categories if none exist."""

    # Check if categories already exist
    result = await db.execute(select(Category).limit(1))
    if result.scalar_one_or_none() is not None:
        print("✅ Categories already seeded, skipping...")
        return

    categories = [
        # Income categories
        Category(name="Salary", type=CategoryType.INCOME),
        Category(name="Freelance", type=CategoryType.INCOME),
        Category(name="Investment", type=CategoryType.INCOME),
        Category(name="Gift", type=CategoryType.INCOME),
        # Expense categories
        Category(name="Food", type=CategoryType.EXPENSE),
        Category(name="Transport", type=CategoryType.EXPENSE),
        Category(name="Housing", type=CategoryType.EXPENSE),
        Category(name="Utilities", type=CategoryType.EXPENSE),
        Category(name="Entertainment", type=CategoryType.EXPENSE),
        Category(name="Health", type=CategoryType.EXPENSE),
        # Both (flexible)
        Category(name="Other", type=CategoryType.BOTH),
    ]

    db.add_all(categories)
    await db.commit()

    print(f"✅ Seeded {len(categories)} default categories")
