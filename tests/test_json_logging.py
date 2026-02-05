import logging

from structlog_config import configure_logger
from tests.utils import read_jsonl


def test_json_logging(capsysbinary):
    """Test that JSON logging works in production environment"""

    log = configure_logger(json_logger=True)
    log.info("JSON test", key="value")

    log_output = capsysbinary.readouterr().out.decode("utf-8")

    log_entries = read_jsonl(log_output)
    assert len(log_entries) == 1

    log_data = log_entries[0]

    assert log_data["event"] == "JSON test"
    assert log_data["key"] == "value"
    assert "timestamp" in log_data


def test_exception_formatting(capsys):
    """Test that exceptions are properly formatted"""
    log = configure_logger(json_logger=True)

    try:
        raise ValueError("Test exception")
    except ValueError:
        log.exception("An error occurred")

    log_output = capsys.readouterr().out
    log_entries = read_jsonl(log_output)
    assert log_entries
    log_data = log_entries[-1]

    assert log_data["event"] == "An error occurred"

    exception_payload = log_data["exception"]
    assert isinstance(exception_payload, list)
    assert exception_payload

    first_exception = exception_payload[0]
    assert first_exception["exc_type"] == "ValueError"
    assert first_exception["exc_value"] == "Test exception"
    assert isinstance(first_exception["frames"], list)
    assert first_exception["frames"]


def test_stdlib_exception_logging(capsys):
    configure_logger(json_logger=True)

    std_logger = logging.getLogger("uvicorn.error")

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        std_logger.error("unhandled", exc_info=True)

    log_output = capsys.readouterr().out
    log_entries = read_jsonl(log_output)
    assert log_entries
    log_data = log_entries[-1]

    assert log_data["event"] == "unhandled"
    assert log_data["level"] == "error"

    exception_payload = log_data["exception"]
    assert isinstance(exception_payload, list)
    assert exception_payload[0]["exc_type"] == "RuntimeError"
    assert exception_payload[0]["exc_value"] == "boom"


def test_managed_logger_handler_replacement_json_mode(capsys):
    """Verify loggers with pre-existing handlers are cleared and propagate to root"""
    # Create a stdlib logger with a custom handler before configure_logger
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    custom_handler = logging.StreamHandler()
    uvicorn_error_logger.addHandler(custom_handler)

    # Configure with JSON logging
    configure_logger(json_logger=True)

    # Verify handlers were cleared and logger propagates to root
    assert len(uvicorn_error_logger.handlers) == 0
    assert uvicorn_error_logger.propagate is True

    # Verify output is valid JSON via propagation to root
    uvicorn_error_logger.info("test message from uvicorn")

    log_output = capsys.readouterr().out
    log_entries = read_jsonl(log_output)
    assert log_entries
    log_data = log_entries[-1]

    assert log_data["event"] == "test message from uvicorn"
    assert log_data["logger"] == "uvicorn.error"


def test_placeholder_loggers_handled_correctly(capsys):
    """Verify PlaceHolder instances in loggerDict don't cause errors"""
    # Create a deeply nested logger to force PlaceHolder creation for parents
    child_logger = logging.getLogger("some.deeply.nested.logger.name")
    child_logger.addHandler(logging.StreamHandler())

    # Verify PlaceHolder exists for parent (internal detail, but validates our test setup)
    assert "some" in logging.Logger.manager.loggerDict
    assert "some.deeply" in logging.Logger.manager.loggerDict

    # This should not raise AttributeError when encountering PlaceHolder instances
    configure_logger(json_logger=True)

    # Verify child logger still works correctly
    child_logger.info("message from nested logger")

    log_output = capsys.readouterr().out
    log_entries = read_jsonl(log_output)
    assert log_entries
    log_data = log_entries[-1]

    assert log_data["event"] == "message from nested logger"
    assert log_data["logger"] == "some.deeply.nested.logger.name"
