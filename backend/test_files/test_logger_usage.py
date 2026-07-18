"""
Example: How to use the logger in your project files.
"""

import sys
from pathlib import Path

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# METHOD 1: Quick import (uses default logger)
# ============================================================
from core.logger import info, error, warning, debug, exception

def quick_example():
    info("Application started")
    debug("Debug information", extra={"user_id": 123})
    warning("This is a warning")
    error("Something went wrong")
    
    try:
        1 / 0
    except ZeroDivisionError:
        exception("Division by zero error occurred")


# ============================================================
# METHOD 2: Module-specific logger (recommended)
# ============================================================
from core.logger import setup_logger

# Create a logger for this module
logger = setup_logger(
    name="my_module",           # Logger name (shows in logs)
    log_level="DEBUG",          # Log level
    log_dir="logs",             # Log directory
    json_logs=False,            # Set True for JSON format
)

def module_example():
    logger.info("Module-specific logger initialized")
    logger.debug("Debug details", extra={"request_id": "req-456"})
    logger.warning("Warning from module")
    logger.error("Error from module")


# ============================================================
# METHOD 3: Class-based logging with LoggerMixin
# ============================================================
from core.logger import LoggerMixin

class MyService(LoggerMixin):
    """Service class with built-in logging."""
    
    def process_data(self, data: list):
        self.logger.info(f"Processing {len(data)} items")
        for item in data:
            self.logger.debug(f"Processing item: {item}")
        self.logger.info("Processing complete")
        return {"status": "success", "count": len(data)}
    
    def handle_error(self):
        try:
            raise ValueError("Invalid input")
        except ValueError as e:
            self.logger.error(f"Validation failed: {e}", exc_info=True)


# ============================================================
# METHOD 4: Decorators for timing functions
# ============================================================
from core.logger import log_execution_time, log_async_execution_time

@log_execution_time(logger)
def slow_function():
    import time
    time.sleep(0.5)
    return "done"

@log_async_execution_time(logger)
async def async_slow_function():
    import asyncio
    await asyncio.sleep(0.5)
    return "async done"


# ============================================================
# METHOD 5: Context manager for adding context to logs
# ============================================================
from core.logger import LogContext

def with_context_example():
    logger.info("Before context")
    
    with LogContext(logger, request_id="req-789", user_id="user-123", trace_id="trace-abc"):
        logger.info("Inside context - has request_id, user_id, trace_id")
        logger.warning("Warning with context")
    
    logger.info("After context - no extra fields")


# ============================================================
# Run examples
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("Logger Usage Examples")
    print("=" * 50)
    
    quick_example()
    print()
    
    module_example()
    print()
    
    service = MyService()
    service.process_data(["item1", "item2", "item3"])
    print()
    
    slow_function()
    print()
    
    with_context_example()
    print()
    
    print("Check logs/ directory for output files!")