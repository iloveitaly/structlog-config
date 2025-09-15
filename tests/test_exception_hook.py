import json
import sys
from contextlib import contextmanager
from unittest.mock import patch

import structlog

from structlog_config import configure_logger


@contextmanager
def capture_exception_hook():
    """Context manager to capture calls to sys.excepthook."""
    original_hook = sys.excepthook
    captured_calls = []
    
    def mock_hook(exc_type, exc_value, exc_tb):
        captured_calls.append((exc_type, exc_value, exc_tb))
        # Call original to maintain behavior
        original_hook(exc_type, exc_value, exc_tb)
    
    sys.excepthook = mock_hook
    try:
        yield captured_calls
    finally:
        sys.excepthook = original_hook


def test_exception_hook_setup():
    """Test that exception hook is properly set up when json_logger=True."""
    original_hook = sys.excepthook
    
    # Test with json_logger=True (should enable exception logging)
    configure_logger(json_logger=True)
    
    # Hook should be replaced
    assert sys.excepthook is not original_hook
    
    # Reset for next test
    sys.excepthook = original_hook


def test_exception_hook_disabled():
    """Test that exception hook is not set up when json_logger=False."""
    original_hook = sys.excepthook
    
    # Test with json_logger=False (should disable exception logging)
    configure_logger(json_logger=False)
    
    # Hook should remain the same
    assert sys.excepthook is original_hook


def test_exception_hook_json_logging(capsysbinary):
    """Test that uncaught exceptions are logged as JSON."""
    # Configure with JSON logging (exception hook automatically enabled)
    log = configure_logger(json_logger=True)
    
    # Log a normal message first
    log.info("Before exception")
    
    # Simulate an uncaught exception by calling the hook directly
    try:
        raise ValueError("Test exception")
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_value, exc_tb)
    
    # Capture the output
    output = capsysbinary.readouterr().out.decode("utf-8")
    lines = output.strip().split("\n")
    
    # Should have at least 2 lines: the normal log and the exception log
    assert len(lines) >= 2
    
    # Parse the first line (normal log)
    normal_log = json.loads(lines[0])
    assert normal_log["event"] == "Before exception"
    assert normal_log["level"] == "info"
    
    # Parse the second line (exception log)
    exception_log = json.loads(lines[1])
    assert exception_log["event"] == "ValueError"
    assert exception_log["level"] == "error"
    assert "exception" in exception_log
    assert "ValueError" in exception_log["exception"]
    assert "Test exception" in exception_log["exception"]


def test_exception_hook_console_logging_disabled():
    """Test that exception hook is not set up in console mode."""
    original_hook = sys.excepthook
    
    # Configure with console logging (exception hook should be disabled)
    log = configure_logger(json_logger=False)
    
    # Hook should remain the same (not replaced)
    assert sys.excepthook is original_hook


def test_exception_hook_keyboard_interrupt():
    """Test that KeyboardInterrupt is not logged as an exception."""
    with capture_exception_hook() as captured_calls:
        # Configure with exception hook (JSON mode)
        configure_logger(json_logger=True)
        
        # Simulate a KeyboardInterrupt
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_tb)
    
    # Should have captured the call to the original hook
    assert len(captured_calls) == 1
    assert captured_calls[0][0] is KeyboardInterrupt


def test_exception_hook_chains_to_original():
    """Test that the exception hook chains to the original hook."""
    original_hook = sys.excepthook
    hook_called = []
    
    def mock_original_hook(exc_type, exc_value, exc_tb):
        hook_called.append((exc_type, exc_value, exc_tb))
    
    # Set a custom hook before configuring the logger
    sys.excepthook = mock_original_hook
    
    try:
        # Configure with exception hook (JSON mode)
        configure_logger(json_logger=True)
        
        # Simulate an uncaught exception
        try:
            raise ValueError("Test exception")
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_tb)
        
        # Original hook should have been called
        assert len(hook_called) == 1
        assert hook_called[0][0] is ValueError
        
    finally:
        # Restore original hook
        sys.excepthook = original_hook


def test_default_exception_logging_behavior():
    """Test that exception logging is enabled with json_logger=True and disabled with json_logger=False."""
    original_hook = sys.excepthook
    
    # Test that json_logger=True enables exception logging
    configure_logger(json_logger=True)
    assert sys.excepthook is not original_hook
    
    # Reset hook
    sys.excepthook = original_hook
    
    # Test that json_logger=False disables exception logging  
    configure_logger(json_logger=False)
    assert sys.excepthook is original_hook