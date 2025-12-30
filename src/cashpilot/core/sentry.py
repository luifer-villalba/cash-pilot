"""Sentry error tracking configuration and initialization."""

import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from cashpilot.core.logging import get_logger

logger = get_logger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking.

    Only initializes if SENTRY_DSN environment variable is set.
    This allows local development without Sentry (no DSN = no init).

    Configuration:
    - Disables performance monitoring (paid feature, not needed)
    - Disables SQL query logging in error payloads (security)
    - Logging integration disabled to avoid duplication with structlog
    - Captures structured context (request_id, user_id)
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        logger.info("sentry.disabled", message="Sentry DSN not found, error tracking disabled")
        return

    environment = os.getenv("ENVIRONMENT", "development")

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        # Disable performance monitoring (paid feature)
        traces_sample_rate=0.0,
        # Disable SQL query logging in error payloads (security)
        send_default_pii=False,
        # Integrate with FastAPI
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=None, event_level=None),  # Don't duplicate logs
            # Note: SqlalchemyIntegration is NOT included to prevent SQL query capture
        ],
        # Additional options
        before_send=_filter_sensitive_data,
    )

    logger.info(
        "sentry.initialized", message="Sentry error tracking enabled", environment=environment
    )


def _filter_sensitive_data(event: dict, hint: dict) -> dict:
    """
    Filter sensitive data from Sentry events.

    Ensures no SQL queries or sensitive information is sent to Sentry.
    """
    # Don't filter events when running in a test environment
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment in {"test", "testing"}:
        return event

    try:
        # Remove any SQL-related data from extra, if it is a mapping
        extra = event.get("extra")
        if isinstance(extra, dict):
            filtered_extra = {}
            for key, value in extra.items():
                key_str = str(key).lower()
                value_str = str(value).lower()
                # Skip any entry where the key or value suggests SQL content
                if "sql" in key_str or "sql" in value_str:
                    continue
                filtered_extra[key] = value
            event["extra"] = filtered_extra

        # Remove breadcrumbs that might contain SQL
        breadcrumbs = event.get("breadcrumbs")
        if isinstance(breadcrumbs, list):
            filtered_breadcrumbs = []
            for b in breadcrumbs:
                # Support both dict and non-dict breadcrumb items
                if isinstance(b, dict):
                    message = b.get("message", "")
                else:
                    message = b
                if "sql" not in str(message).lower():
                    filtered_breadcrumbs.append(b)
            event["breadcrumbs"] = filtered_breadcrumbs
    except Exception as exc:  # Defensive: never break Sentry sending due to filtering
        logger.error(
            "sentry.filter_error",
            message="Error while filtering sensitive data from Sentry event",
            error=str(exc),
        )
        # Return event as-is if filtering fails
        return event

    return event
