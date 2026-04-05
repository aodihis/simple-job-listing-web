"""
Structured logging configuration using structlog.

This is the ONLY file to change when swapping log sinks or output format.

Dev:  ConsoleRenderer (colorized, human-readable)
Prod: JSONRenderer (structured JSON for log ingestion)

To add a file sink, remote sink (Loki, Datadog, etc.), or sampling,
add processors or a custom logger factory here.
"""
from __future__ import annotations

import logging
import sys

import structlog

_configured = False


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure structlog. Call once at application startup in main.py.

    Args:
        log_level: Python log level name (DEBUG, INFO, WARNING, ERROR).
        json_logs: If True, emit JSON lines instead of colorized console output.
                   Set to True in production for structured log ingestion.
    """
    global _configured
    if _configured:
        return

    # Route stdlib logging through structlog so third-party libs appear in our logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    if json_logs:
        # Structured JSON — suitable for Loki, Datadog, CloudWatch, etc.
        # To change the sink: swap PrintLoggerFactory for a custom factory here.
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Human-readable colorized output for local development
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configured = True


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Return a bound logger for the given module name.

    Usage:
        from app.logging.config import get_logger
        log = get_logger(__name__)
        log.info("job.created", job_id=job.public_id, posted_by=user.email)
    """
    return structlog.get_logger(name)
