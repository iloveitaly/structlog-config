import logging
import warnings

from structlog_config import configure_logger
from tests.capture_utils import CaptureStreams
from tests.utils import read_jsonl, temp_env_var


def test_log_destination_writes_to_file(tmp_path):
    """Test that both stdlib and structlog logs go to PYTHON_LOG_PATH file"""
    log_file = tmp_path / "log_output.log"
    log_path = str(log_file)

    with temp_env_var({"PYTHON_LOG_PATH": log_path}):
        # Configure structlog and stdlib logging
        logger = configure_logger()
        std_logger = logging.getLogger("test_stdlib")

        # Log with structlog
        logger.info("structlog message", foo="bar")

        # Log with stdlib
        std_logger.warning("stdlib warning message")

        # Emit a Python warning
        warnings.warn("this is a python warning", UserWarning)

    # Read the log file
    with open(log_file, "r") as f:
        log_contents = f.read()

    assert "structlog message" in log_contents
    assert (
        "foo=bar" in log_contents or '"foo": "bar"' in log_contents
    )  # support for JSON or key=value
    assert "stdlib warning message" in log_contents
    assert "this is a python warning" in log_contents
    # Optionally, check logger name or other fields if needed


def test_json_log_destination_writes_to_file(tmp_path):
    log_file = tmp_path / "log_output.jsonl"
    log_path = str(log_file)

    with temp_env_var({"PYTHON_LOG_PATH": log_path}):
        with CaptureStreams() as capture:
            logger = configure_logger(json_logger=True)
            std_logger = logging.getLogger("test_stdlib_json")

            logger.info("structlog message", foo="bar")
            std_logger.warning("stdlib warning message")
            warnings.warn("this is a python warning", UserWarning)

        assert capture.stdout.getvalue() == ""
        assert capture.stderr.getvalue() == ""

    log_contents = log_file.read_text()
    log_entries = read_jsonl(log_contents)

    assert any(
        entry["event"] == "structlog message" and entry["foo"] == "bar"
        for entry in log_entries
    )
    assert any(
        entry["event"] == "stdlib warning message" and entry["level"] == "warning"
        for entry in log_entries
    )
    assert any(
        "this is a python warning" in entry.get("event", "") for entry in log_entries
    )


def test_json_log_destination_serializes_exceptions_to_file(tmp_path):
    log_file = tmp_path / "log_exceptions.jsonl"
    log_path = str(log_file)

    with temp_env_var({"PYTHON_LOG_PATH": log_path}):
        logger = configure_logger(json_logger=True)
        std_logger = logging.getLogger("test_stdlib_json_exceptions")

        try:
            raise ValueError("structlog boom")
        except ValueError:
            logger.exception("structlog exception")

        try:
            raise RuntimeError("stdlib boom")
        except RuntimeError:
            std_logger.error("stdlib exception", exc_info=True)

    log_contents = log_file.read_text()
    log_entries = read_jsonl(log_contents)

    structlog_entry = next(
        entry for entry in log_entries if entry["event"] == "structlog exception"
    )
    stdlib_entry = next(
        entry for entry in log_entries if entry["event"] == "stdlib exception"
    )

    assert "exception" in structlog_entry
    assert "exception" in stdlib_entry


def test_log_destination_stdout_special_value():
    with temp_env_var({"PYTHON_LOG_PATH": "stdout"}):
        with CaptureStreams() as capture:
            logger = configure_logger()
            std_logger = logging.getLogger("test_stdlib_stdout_env")

            logger.info("structlog stdout env")
            std_logger.warning("stdlib stdout env")
            warnings.warn("warning stdout env", UserWarning)

        stdout_out = capture.stdout.getvalue()
        stderr_out = capture.stderr.getvalue()

    assert "structlog stdout env" in stdout_out
    assert "stdlib stdout env" in stdout_out
    assert "warning stdout env" in stdout_out
    assert "structlog stdout env" not in stderr_out
    assert "stdlib stdout env" not in stderr_out
    assert "warning stdout env" not in stderr_out


def test_log_destination_stderr_special_value():
    with temp_env_var({"PYTHON_LOG_PATH": "stderr"}):
        with CaptureStreams() as capture:
            logger = configure_logger()
            std_logger = logging.getLogger("test_stdlib_stderr_env")

            logger.info("structlog stderr env")
            std_logger.warning("stdlib stderr env")
            warnings.warn("warning stderr env", UserWarning)

        stdout_out = capture.stdout.getvalue()
        stderr_out = capture.stderr.getvalue()

    assert "structlog stderr env" in stderr_out
    assert "stdlib stderr env" in stderr_out
    assert "warning stderr env" in stderr_out
    assert "structlog stderr env" not in stdout_out
    assert "stdlib stderr env" not in stdout_out
    assert "warning stderr env" not in stdout_out


def test_json_log_destination_stdout_special_value():
    with temp_env_var({"PYTHON_LOG_PATH": "stdout"}):
        with CaptureStreams() as capture:
            logger = configure_logger(json_logger=True)
            std_logger = logging.getLogger("test_stdlib_json_stdout_env")

            logger.info("structlog json stdout env", foo="bar")
            std_logger.warning("stdlib json stdout env")
            warnings.warn("warning json stdout env", UserWarning)

        stdout_out = capture.stdout.getvalue()
        stderr_out = capture.stderr.getvalue()

    log_entries = read_jsonl(stdout_out)

    assert any(
        entry["event"] == "structlog json stdout env" and entry["foo"] == "bar"
        for entry in log_entries
    )
    assert any(entry["event"] == "stdlib json stdout env" for entry in log_entries)
    assert any(
        "warning json stdout env" in entry.get("event", "") for entry in log_entries
    )
    assert stderr_out == ""


def test_json_log_destination_stderr_special_value():
    with temp_env_var({"PYTHON_LOG_PATH": "stderr"}):
        with CaptureStreams() as capture:
            logger = configure_logger(json_logger=True)
            std_logger = logging.getLogger("test_stdlib_json_stderr_env")

            logger.info("structlog json stderr env", foo="bar")
            std_logger.warning("stdlib json stderr env")
            warnings.warn("warning json stderr env", UserWarning)

        stdout_out = capture.stdout.getvalue()
        stderr_out = capture.stderr.getvalue()

    log_entries = read_jsonl(stderr_out)

    assert any(
        entry["event"] == "structlog json stderr env" and entry["foo"] == "bar"
        for entry in log_entries
    )
    assert any(entry["event"] == "stdlib json stderr env" for entry in log_entries)
    assert any(
        "warning json stderr env" in entry.get("event", "") for entry in log_entries
    )
    assert stdout_out == ""
