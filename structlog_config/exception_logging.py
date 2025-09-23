"""
Exception logging configuration for structlog.

This module provides functionality to automatically log uncaught exceptions
using structlog, ensuring that exceptions are logged in the same format as
other log messages, including proper JSON formatting in production environments.
"""

import sys
import structlog

from .constants import package_logger


def setup_exception_hook() -> None:
    """
    Set up a custom sys.excepthook to log uncaught exceptions using structlog.
    
    This ensures that uncaught exceptions are logged in the same format as other
    log messages, including proper JSON formatting in production environments.
    
    Warns if an existing exception hook is already in place.
    """
    # Check if there's already a custom exception hook in place
    if sys.excepthook != sys.__excepthook__:
        package_logger.warning(
            "An existing exception hook is already installed. "
            "This may interfere with exception logging functionality. "
            f"Existing hook: {sys.excepthook}"
        )
    
    def log_uncaught_exception(exc_type, exc_value, exc_tb):
        """Custom exception hook that logs uncaught exceptions."""
        # Don't log KeyboardInterrupt as an exception
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
            
        # Get a logger and log the exception using the exception name as the event
        logger = structlog.get_logger()
        logger.error(
            exc_type.__name__,
            exc_info=(exc_type, exc_value, exc_tb)
        )
    
    # Set our custom hook
    sys.excepthook = log_uncaught_exception