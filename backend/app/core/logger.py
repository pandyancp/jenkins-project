"""
Structured Logging
===================
Sets up JSON-structured logging for the trading platform.
Logs to both console and file.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from backend.app.core.config import settings, BASE_DIR


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""

    logger = logging.getLogger("algotrader")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Log format
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler with safe UTF-8 encoding
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / "algotrader.log", encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.info(f"Logger initialized | Level={settings.LOG_LEVEL}")
    return logger


# Singleton logger
logger = setup_logging()
