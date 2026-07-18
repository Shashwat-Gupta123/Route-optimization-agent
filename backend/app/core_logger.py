"""Thin wrapper around :mod:`core.logger` for the FastAPI app.

Centralizes logger creation so every module logs to the same rotating files
under ``backend/logs/`` with consistent configuration.
"""

from __future__ import annotations

import logging
import os

from core.logger import setup_logger

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
_LOG_DIR = os.getenv("LOG_DIR", "logs")
_JSON_LOGS = os.getenv("JSON_LOGS", "false").lower() == "true"

# Root application logger (configures file + console handlers once).
_root = setup_logger(
    name="route_optimizer",
    log_level=_LOG_LEVEL,
    log_dir=_LOG_DIR,
    json_logs=_JSON_LOGS,
)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the configured ``route_optimizer`` root."""
    return _root.getChild(name)


def get_tool_logger(name: str) -> logging.Logger:
    """Return a logger namespaced for an agent tool."""
    return _root.getChild(f"tools.{name}")
