"""Request logging and ID injection middleware."""

import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

from cashpilot.core.logging import get_logger, set_request_id


class RequestIDMiddleware:
    """
    Inject unique request ID into context.

    Every request gets a UUID. If X-Request-ID header exists, use it.
    Available in logs via request_id context var.
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process request with request ID injection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get or generate request ID
        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", str(uuid.uuid4()).encode()).decode()
        set_request_id(request_id)

        # Log incoming request
        self.logger.info(
            "request.start",
            method=scope["method"],
            path=scope["path"],
        )

        # Intercept send to add response header
        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers

                # Log response
                self.logger.info(
                    "request.complete",
                    status_code=message.get("status"),
                )

            await send(message)

        await self.app(scope, receive, send_with_request_id)
