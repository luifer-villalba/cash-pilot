"""Structured logging configuration with JSON output and context injection."""

import contextvars
import logging

import structlog

# Context var for request ID (thread-safe for async)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="no-request-id"
)


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set request ID for current context."""
    request_id_var.set(request_id)


def configure_logging() -> None:
    """Configure structlog with JSON output for production."""
    structlog.configure(
        processors=[
            # Inject request ID into every log
            structlog.contextvars.merge_contextvars,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add log level
            structlog.processors.add_log_level,
            # Format exceptions properly
            structlog.processors.format_exc_info,
            # JSON output
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(),
                },
            },
            "handlers": {
                "default": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": "DEBUG",
                    "propagate": True,
                }
            },
        }
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structlog logger with request ID already bound."""
    return structlog.get_logger(name).bind(request_id=get_request_id())
