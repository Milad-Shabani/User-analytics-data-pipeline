"""Centralized logging configuration.

Every module in the package gets a consistently formatted logger instead of
sprinkling `print()` calls through the pipeline, which makes the tool usable
both interactively and as a scheduled/orchestrated job (cron, Airflow, etc.).
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging once, safely callable multiple times."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. re-entrant calls in tests) — just update level.
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
