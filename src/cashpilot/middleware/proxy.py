"""Middleware for static asset headers when behind Cloudflare/Railway proxy."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from cashpilot.core.logging import get_logger

logger = get_logger(__name__)


class StaticAssetHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add proper headers for static assets when behind Cloudflare proxy.

    This ensures static files (CSS, JS, images) are served with correct headers
    for caching and CORS, which can help resolve loading issues behind proxies.
    """

    async def dispatch(self, request: Request, call_next):
        is_static = request.url.path.startswith("/static")
        if is_static:
            logger.info(
                "middleware.static_headers.request",
                path=request.url.path,
                method=request.method,
            )

        response = await call_next(request)

        # Add proper headers for static assets to ensure they load correctly
        # behind Cloudflare proxy
        if isinstance(response, Response) and is_static:
            logger.info(
                "middleware.static_headers.adding_headers",
                path=request.url.path,
                status_code=getattr(response, "status_code", "N/A"),
            )
            # Ensure static files have proper cache headers
            response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
            # Ensure CORS headers (shouldn't be needed for same-origin, but helps with proxy)
            response.headers.setdefault("Access-Control-Allow-Origin", "*")

        return response
