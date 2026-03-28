import sys
import logging
import structlog
import pytest
from structlog_config import configure_logger
from tests.capture_utils import CaptureStreams

def test_stream_coordination_stderr():
    """Test that passing a factory pointing to stderr redirects all logs to stderr."""
    with CaptureStreams() as capture:
        # Reset structlog to ensure we're starting fresh
        structlog.reset_defaults()
        
        # Configure with a factory pointing to stderr
        logger = configure_logger(
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr)
        )
        
        # Log with structlog
        logger.info("structlog to stderr")
        
        # Log with stdlib
        stdlib_logger = logging.getLogger("test_stderr_coordination")
        stdlib_logger.info("stdlib to stderr")
        
    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()
    
    assert "structlog to stderr" in stderr_out
    assert "stdlib to stderr" in stderr_out
    assert "structlog to stderr" not in stdout_out
    assert "stdlib to stderr" not in stdout_out

def test_stream_coordination_stdout_explicit():
    """Test that passing a factory pointing to stdout redirects all logs to stdout."""
    with CaptureStreams() as capture:
        structlog.reset_defaults()
        
        # Configure with a factory pointing to stdout
        logger = configure_logger(
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout)
        )
        
        # Log with structlog
        logger.info("structlog to stdout")
        
        # Log with stdlib
        stdlib_logger = logging.getLogger("test_stdout_coordination")
        stdlib_logger.info("stdlib to stdout")
        
    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()
    
    assert "structlog to stdout" in stdout_out
    assert "stdlib to stdout" in stdout_out
    assert "structlog to stdout" not in stderr_out
    assert "stdlib to stdout" not in stderr_out

def test_json_stream_coordination_stderr():
    """Test that passing a BytesLoggerFactory pointing to stderr.buffer redirects all logs to stderr."""
    with CaptureStreams() as capture:
        structlog.reset_defaults()
        
        # In JSON mode, we use BytesLoggerFactory which takes a buffer
        logger = configure_logger(
            json_logger=True,
            logger_factory=structlog.BytesLoggerFactory(file=sys.stderr.buffer)
        )
        
        # Log with structlog
        logger.info("structlog json to stderr")
        
        # Log with stdlib
        stdlib_logger = logging.getLogger("test_json_stderr_coordination")
        stdlib_logger.info("stdlib json to stderr")
        
    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()
    
    assert "structlog json to stderr" in stderr_out
    assert "stdlib json to stderr" in stderr_out
    assert "structlog json to stderr" not in stdout_out
    assert "stdlib json to stderr" not in stdout_out

def test_stream_coordination_default():
    """Test that by default logs go to stdout."""
    with CaptureStreams() as capture:
        structlog.reset_defaults()
        
        # Default configuration
        logger = configure_logger()
        
        # Log with structlog
        logger.info("structlog to default")
        
        # Log with stdlib
        stdlib_logger = logging.getLogger("test_default_coordination")
        stdlib_logger.info("stdlib to default")
        
    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()
    
    assert "structlog to default" in stdout_out
    assert "stdlib to default" in stdout_out
    assert "structlog to default" not in stderr_out
    assert "stdlib to default" not in stderr_out
