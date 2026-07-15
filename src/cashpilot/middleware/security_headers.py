"""Security response headers middleware.

Adds a conservative set of hardening headers to every response:

- ``X-Frame-Options`` / CSP ``frame-ancestors`` — clickjacking protection.
- ``X-Content-Type-Options: nosniff`` — stop MIME sniffing.
- ``Referrer-Policy`` — limit referrer leakage.
- ``Strict-Transport-Security`` — force HTTPS (production only).
- ``Content-Security-Policy`` — restrict where scripts/styles/frames may load
  from. The policy keeps ``'unsafe-inline'`` and the current CDN origins because
  the templates rely on inline scripts/handlers and load htmx/Chart.js from a
  CDN. ``'unsafe-eval'`` is also required: the templates use htmx ``hx-on`` and
  ``hx-vals='js:...'`` attributes, which htmx evaluates via ``Function()`` —
  without it, adding transfers/expenses on the close-session form is blocked by
  the browser (EvalError). The policy still blocks unknown external script
  origins, framing, plugins, and ``<base>`` hijacking. Tighten toward nonces
  (and drop ``'unsafe-eval'``) if the inline scripts and js: attributes are
  removed.

  The Cloudflare Web Analytics beacon is proxy-injected in production
  (``static.cloudflareinsights.com`` in ``script-src``); it reports RUM data to
  ``cloudflareinsights.com``, allowed in ``connect-src``.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://static.cloudflareinsights.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://cloudflareinsights.com; "
    "frame-ancestors 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every response."""

    def __init__(self, app, is_production: bool = False):
        super().__init__(app)
        self._is_production = is_production

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers.setdefault("Content-Security-Policy", _CSP)
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Only assert HSTS over HTTPS (production) — sending it on plaintext dev
        # would wrongly pin localhost to HTTPS in the browser.
        if self._is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response
