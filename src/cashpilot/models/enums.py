"""
Enums for domain models.
Enums provide type safety and clarity. Validation for categorical fields.
"""

import enum


class MovementType(enum.Enum):
    """
    Type of cash flow movement.

    INCOME: Money coming in (salary, sales, refunds, etc.)
    EXPENSE: Money going out (rent, groceries, bills, etc.)
    """

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

    def __str__(self) -> str:
        return self.value


class CategoryType(enum.Enum):
    """
    Category scope for movements.

    INCOME: Only for income movements
    EXPENSE: Only for expense movements
    BOTH: Can be used for either (e.g., "Other")
    """

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    BOTH = "BOTH"

    def __str__(self) -> str:
        return self.value
