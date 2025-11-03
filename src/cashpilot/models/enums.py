"""
Enums for domain models.
Enums provide type safety and clarity. Validation for categorical fields.
"""

import enum


class SessionStatus(str, enum.Enum):
    """Session lifecycle states."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
