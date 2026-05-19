"""Structured logging setup for logseq-api-mcp."""

import logging
import logging.handlers
import os
from pathlib import Path

_LOG_NAME = "logseq_mcp"
_LOG_FILE = "server.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3

_root_logger: logging.Logger | None = None


def setup_logging(log_dir: Path | None = None) -> logging.Logger:
    """Configure the root logseq_mcp logger.

    Attempts to log to a rotating file in log_dir (default:
    ~/.cache/logseq-api-mcp/). Falls back to stderr if the directory
    cannot be created. Log level is read from LOGSEQ_LOG_LEVEL
    (default: WARNING).

    Args:
        log_dir: Directory for the log file. Overrides the default cache dir.

    Returns:
        Configured Logger instance.

    Complexity: O(1).
    """
    global _root_logger
    logger = logging.getLogger(_LOG_NAME)

    # Idempotent for production (no explicit log_dir); always reconfigure when called explicitly.
    if logger.handlers and log_dir is None:
        return logger
    for h in logger.handlers[:]:
        logger.removeHandler(h)
        h.close()

    level_name = os.getenv("LOGSEQ_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler: logging.Handler
    try:
        if log_dir is None:
            log_dir = Path.home() / ".cache" / "logseq-api-mcp"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_dir / _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
    except (PermissionError, OSError):
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _root_logger = logger
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the logseq_mcp namespace.

    Args:
        name: Submodule name (e.g. 'tools.get_all_pages').

    Returns:
        Child Logger instance.

    Complexity: O(1).
    """
    return logging.getLogger(f"{_LOG_NAME}.{name}")
