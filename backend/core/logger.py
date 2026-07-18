"""
Core logging configuration for the Route Optimization Agent.
Provides structured logging with file rotation, console output, and JSON formatting.
"""

import logging
import logging.handlers
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from functools import wraps


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for better readability."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
        "RESET": "\033[0m",       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        # Format: [LEVEL] timestamp logger.module:function:line - message
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        log_line = (
            f"{color}[{record.levelname:8}]{reset} "
            f"{timestamp} "
            f"{record.name}.{record.funcName}:{record.lineno} - "
            f"{record.getMessage()}"
        )
        
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        
        return log_line


def setup_logger(
    name: str = "route_optimizer",
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    json_logs: bool = False,
    console_output: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Set up and configure a logger with file rotation and console output.
    
    Args:
        name: Logger name (typically __name__ of the module)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (None = no file logging)
        json_logs: Use JSON format for file logs
        console_output: Enable colored console output
        max_file_size: Max size of each log file in bytes
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with colored output
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(ColoredConsoleFormatter())
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Main log file (all levels)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / f"{name}.log",
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            JSONFormatter() if json_logs else logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(file_handler)
        
        # Error-only log file
        error_handler = logging.handlers.RotatingFileHandler(
            log_path / f"{name}_errors.log",
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            JSONFormatter() if json_logs else logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(error_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance. If not configured, returns a basic logger.
    Use setup_logger() first for full configuration.
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        return self._logger


def log_execution_time(logger: Optional[logging.Logger] = None, level: int = logging.INFO):
    """
    Decorator to log function execution time.
    
    Usage:
        @log_execution_time(logger=my_logger)
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            start_time = datetime.utcnow()
            log.log(level, f"Starting {func.__name__}")
            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                log.log(level, f"Completed {func.__name__} in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                log.error(f"Failed {func.__name__} after {elapsed:.3f}s: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


def log_async_execution_time(logger: Optional[logging.Logger] = None, level: int = logging.INFO):
    """
    Decorator to log async function execution time.
    
    Usage:
        @log_async_execution_time(logger=my_logger)
        async def my_async_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            start_time = datetime.utcnow()
            log.log(level, f"Starting {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                log.log(level, f"Completed {func.__name__} in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                log.error(f"Failed {func.__name__} after {elapsed:.3f}s: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


# Default logger instance for easy importing
default_logger = setup_logger(
    name="route_optimizer",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "logs"),
    json_logs=os.getenv("JSON_LOGS", "false").lower() == "true",
)


# Convenience functions for quick logging
def debug(msg: str, *args, **kwargs):
    default_logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    default_logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    default_logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    default_logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    default_logger.critical(msg, *args, **kwargs)

def exception(msg: str, *args, **kwargs):
    default_logger.exception(msg, *args, **kwargs)


# Context manager for adding extra fields to log records
class LogContext:
    """Context manager to add extra fields to all log records within the block."""
    
    def __init__(self, logger: logging.Logger, **extra_fields):
        self.logger = logger
        self.extra_fields = extra_fields
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.extra_fields = self.extra_fields
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


# Example usage and testing
if __name__ == "__main__":
    # Test the logger
    logger = setup_logger(
        name="test_logger",
        log_level="DEBUG",
        log_dir="logs",
        json_logs=True,
    )
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Test with extra fields
    with LogContext(logger, request_id="req-123", user_id="user-456"):
        logger.info("Message with context")
    
    # Test decorators
    @log_execution_time(logger)
    def sample_function():
        import time
        time.sleep(0.1)
        return "done"
    
    sample_function()
    
    print("\nTest complete. Check logs/ directory for output.")