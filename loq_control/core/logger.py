"""
Structured rotating logger for LOQ Control.

Writes to ~/.local/share/loq-control/loq-control.log
Console handler at WARNING level; file handler at DEBUG level.
"""

import logging
import logging.handlers
import os
from pathlib import Path

_LOG_DIR = Path.home() / ".local" / "share" / "loq-control"
_LOG_FILE = _LOG_DIR / "loq-control.log"
_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
_BACKUP_COUNT = 3

_logger: logging.Logger | None = None


def get_logger(name: str = "loq-control") -> logging.Logger:
    """Return the shared application logger, creating it on first call."""
    global _logger
    if _logger is not None:
        return _logger

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on reload
    if not _logger.handlers:
        # File handler — DEBUG level, rotating
        fh = logging.handlers.RotatingFileHandler(
            _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        _logger.addHandler(fh)

        # Console handler — WARNING+ only
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        ch.setFormatter(logging.Formatter(
            "%(levelname)s: %(message)s"
        ))
        _logger.addHandler(ch)

    return _logger
