"""Sentry context middleware to capture request context in error reports."""

import uuid

import sentry_sdk
from starlette.types import ASGIApp, Receive, Scope, Send

from cashpilot.core.logging import get_logger, get_request_id

logger = get_logger(__name__)


class SentryContextMiddleware:
    """
    Middleware to inject structured context into Sentry error reports.

    Captures:
    - request_id: Unique request identifier
    - user_id: Authenticated user ID (if available)
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process request with Sentry context injection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get request ID primarily from headers
        # (since this middleware runs before RequestIDMiddleware)
        # Fall back to context var if available
        request_id = None
        headers = scope.get("headers", [])
        for name, value in headers:
            if name.lower() == b"x-request-id":
                try:
                    request_id = value.decode("latin1")
                except Exception:
                    request_id = None
                break
        if not request_id:
            request_id = get_request_id()
        # Generate UUID as final fallback if still not available
        if not request_id or request_id == "no-request-id":
            request_id = str(uuid.uuid4())

        # Get user_id from session if available
        # Session is populated by SessionMiddleware which runs before this middleware
        session = scope.get("session", {})
        user_id = session.get("user_id")

        # Set Sentry context (Sentry SDK 2.x compatible)
        # Use direct API functions which modify the current scope
        sentry_sdk.set_tag("request_id", request_id)
        if user_id:
            sentry_sdk.set_user({"id": user_id})
            sentry_sdk.set_tag("user_id", user_id)

        # Set additional context
        sentry_sdk.set_context(
            "request",
            {
                "method": scope.get("method"),
                "path": scope.get("path"),
                "request_id": request_id,
            },
        )

        try:
            await self.app(scope, receive, send)
        finally:
            # Clear request-scoped tags and context after request
            # Note: In Sentry SDK 2.x, tags persist in the current scope
            # For proper isolation, consider using isolation context if needed
            pass
