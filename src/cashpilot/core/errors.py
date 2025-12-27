"""Custom exceptions and error response schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Standardized error response."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional context")


class AppError(Exception):
    """Base exception for all app-level errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_response(self) -> ErrorDetail:
        """Convert to API response schema."""
        return ErrorDetail(
            code=self.code,
            message=self.message,
            details=self.details if self.details else None,
        )


class ValidationError(AppError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details,
        )


class NotFoundError(AppError):
    """Raised when resource doesn't exist."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} with ID {resource_id} not found",
            status_code=404,
            details={"resource": resource, "resource_id": resource_id},
        )


class ConflictError(AppError):
    """Raised when resource already exists or operation conflicts."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            details=details,
        )


class InvalidStateError(AppError):
    """Raised when operation conflicts with resource state."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            code="INVALID_STATE",
            message=message,
            status_code=400,
            details=details,
        )


class UnauthorizedError(AppError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class ForbiddenError(AppError):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


class DatabaseError(AppError):
    """Raised on database operation failures."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status_code=500,
            details=details,
        )
