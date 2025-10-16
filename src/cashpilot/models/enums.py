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
        """ Return the enum value as string. """
        return self.value