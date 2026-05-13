"""Logging setup."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with a single stderr handler.

    Idempotent — re-running does not duplicate handlers.
    """
    root = logging.getLogger()
    if getattr(root, "_mcp_kraken_configured", False):
        root.setLevel(level.upper())
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    root._mcp_kraken_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
