#!/usr/bin/env python3
"""
Example demonstrating uncaught exception logging with structlog-config.

This example shows how to use the new exception hook functionality to
automatically log uncaught exceptions in JSON format in production
environments, while maintaining nice formatting in development.
"""

import sys
import os

# For demo purposes, add current directory to path
sys.path.insert(0, '/home/runner/work/structlog-config/structlog-config')

from structlog_config import configure_logger


def demonstrate_exception_logging():
    """Demonstrate different modes of exception logging."""
    
    print("=== Uncaught Exception Logging Demo ===\n")
    
    # Example 1: Production mode with JSON logging and exception hook
    print("1. Production mode (JSON logging with exception hook):")
    print("   This shows how uncaught exceptions are logged as JSON in production")
    
    try:
        log = configure_logger(json_logger=True, setup_exception_logging=True)
        log.info("Application starting in production mode")
        
        # Simulate an application error
        def divide_by_zero():
            return 1 / 0
        
        divide_by_zero()  # This will raise an exception
        
    except ZeroDivisionError:
        # For demo purposes, we catch and re-raise through the hook
        exc_type, exc_value, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_value, exc_tb)
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Development mode with console logging and exception hook
    print("2. Development mode (console logging with exception hook):")
    print("   This shows how uncaught exceptions are logged with rich formatting")
    
    try:
        log = configure_logger(json_logger=False, setup_exception_logging=True)
        log.info("Application starting in development mode")
        
        # Simulate an application error
        def access_invalid_key():
            data = {"valid_key": "value"}
            return data["invalid_key"]
        
        access_invalid_key()  # This will raise an exception
        
    except KeyError:
        # For demo purposes, we catch and re-raise through the hook
        exc_type, exc_value, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_value, exc_tb)
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Disabled exception logging
    print("3. Exception logging disabled:")
    print("   Normal exception handling without logging through structlog")
    
    try:
        log = configure_logger(json_logger=True, setup_exception_logging=False)
        log.info("Application with exception logging disabled")
        
        raise ValueError("This exception won't be logged by structlog")
        
    except ValueError as e:
        print(f"Caught exception normally: {e}")
    
    print("\n" + "="*60 + "\n")


def demonstrate_real_uncaught_exception():
    """Demonstrate with a real uncaught exception (warning: this will exit)."""
    
    print("4. Real uncaught exception demo (will exit with code 1):")
    print("   This shows what happens with a real uncaught exception")
    
    # Configure for production
    log = configure_logger(json_logger=True, setup_exception_logging=True)
    log.info("About to demonstrate real uncaught exception")
    
    # This will be caught by our exception hook and logged as JSON
    raise RuntimeError("This is a real uncaught exception that will be logged")


def main():
    """Run the demonstration."""
    demonstrate_exception_logging()
    
    # Ask user if they want to see real uncaught exception
    choice = input("Do you want to see a real uncaught exception? (y/N): ").lower()
    if choice in ['y', 'yes']:
        print("\nRunning real uncaught exception demo...\n")
        demonstrate_real_uncaught_exception()
    else:
        print("\nDemo completed! Key takeaways:")
        print("- Use setup_exception_logging=True to enable automatic exception logging")
        print("- In production (json_logger=True), exceptions are logged as JSON")
        print("- In development (json_logger=False), exceptions are logged with rich formatting")
        print("- KeyboardInterrupt is handled specially (not logged as an exception)")
        print("- The hook chains to existing exception hooks (like Ubuntu's apport)")


if __name__ == "__main__":
    main()