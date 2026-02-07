from pathlib import Path

import structlog

from structlog_config import configure_logger
from tests.utils import mock_package_not_included, temp_env_var


def test_basic_logging(capsys):
    """Test that basic logging works and includes expected fields"""
    log = configure_logger()
    log.info("Test message", test_key="test_value")

    log_output = capsys.readouterr()

    assert "Test message" in log_output.out
    assert "test_key=test_value" in log_output.out


def test_context_manager(capsys):
    """Test that the context manager binds and clears context"""
    log = configure_logger()

    # Test context manager
    with log.context(request_id="abc123"):
        log.info("Within context")

    log.info("Outside context")

    log_output = capsys.readouterr()

    assert "Within context" in log_output.out
    assert "request_id" in log_output.out
    assert "abc123" in log_output.out
    assert "Outside context" in log_output.out
    # Verify context was cleared
    assert "request_id" not in log_output.out.split("Outside context")[1]


def test_local_and_clear(capsys):
    """Test that local binding and clearing work properly"""
    log = configure_logger()

    # Test local binding
    log.local(user_id="user123")
    log.info("With local context")

    # Test clear
    log.clear()
    log.info("After clear")

    log_output = capsys.readouterr()
    assert "With local context" in log_output.out
    assert "user_id" in log_output.out
    assert "user123" in log_output.out
    assert "After clear" in log_output.out
    # Verify context was cleared
    assert "user_id" not in log_output.out.split("After clear")[1]


def test_path_prettifier(capsys):
    """Test that Path objects are correctly formatted"""
    log = configure_logger()

    test_path = Path.cwd() / "test" / "file.txt"
    log.info("Path test", file_path=test_path)

    log_output = capsys.readouterr().out
    # Path should be relative to CWD
    assert "PosixPath" not in log_output
    assert "test/file.txt" in log_output


def test_log_level_filtering(capsys):
    """Test that log level filtering works as expected"""

    with temp_env_var({"LOG_LEVEL": "INFO"}):
        log = configure_logger()
        log.debug("Debug message")  # Should be filtered out
        log.info("Info message")  # Should appear

    log_output = capsys.readouterr().out

    assert "Info message" in log_output
    assert "Debug message" not in log_output


def test_logger_name(capsys):
    """Test that logger_name processor works"""
    configure_logger()

    named_log = structlog.get_logger(logger_name="custom_logger")
    named_log.info("Named logger test")

    log_output = capsys.readouterr().out
    assert "Named logger test" in log_output
    assert "custom_logger" in log_output


def test_nested_context(capsys):
    """Test that nested contexts work as expected"""
    log = configure_logger()

    with log.context(outer="value"):
        log.info("Outer context")
        with log.context(inner="nested"):
            log.info("Nested context")
        log.info("Back to outer")

    log_output = capsys.readouterr().out

    # Check outer context
    assert "Outer context" in log_output
    assert "outer=value" in log_output

    # Check nested context
    assert "Nested context" in log_output
    assert "inner=nested" in log_output
    assert "outer=value" in log_output

    # Check back to outer
    assert "Back to outer" in log_output
    # Make sure "inner" doesn't appear in the last log message
    last_part = log_output.split("Back to outer")[1]
    assert "inner" not in last_part


def test_console_exception_with_beautiful_traceback(capsys, monkeypatch):
    """Test that beautiful-traceback is used for console exception formatting when available"""
    # Mock beautiful_traceback as available
    import structlog_config.packages as packages

    original_beautiful_traceback = packages.beautiful_traceback

    try:
        # Ensure beautiful_traceback is marked as available
        import beautiful_traceback

        monkeypatch.setattr(packages, "beautiful_traceback", beautiful_traceback)

        log = configure_logger()

        try:
            raise ValueError("Test exception for beautiful traceback")
        except ValueError:
            log.exception("Exception with beautiful traceback")

        log_output = capsys.readouterr().out

        # Verify exception was logged
        assert "Exception with beautiful traceback" in log_output
        assert "ValueError" in log_output
        assert "Test exception for beautiful traceback" in log_output

        # Beautiful traceback includes "Traceback (most recent call last):"
        assert "Traceback (most recent call last):" in log_output

    except ImportError:
        # If beautiful_traceback is not installed, skip this test
        import pytest

        pytest.skip("beautiful_traceback not installed")
    finally:
        # Restore original state
        monkeypatch.setattr(
            packages, "beautiful_traceback", original_beautiful_traceback
        )


def test_console_exception_without_beautiful_traceback(capsys, monkeypatch):
    """Test that fallback formatter is used when beautiful-traceback is not available"""
    # Mock beautiful_traceback as not available
    mock_package_not_included(monkeypatch, "beautiful_traceback")

    log = configure_logger()

    try:
        raise RuntimeError("Test exception without beautiful traceback")
    except RuntimeError:
        log.exception("Exception without beautiful traceback")

    log_output = capsys.readouterr().out

    # Verify exception was logged with default formatter
    assert "Exception without beautiful traceback" in log_output
    assert "RuntimeError" in log_output
    assert "Test exception without beautiful traceback" in log_output

    # Traceback should still be present (using structlog's default formatter)
    assert "Traceback" in log_output
