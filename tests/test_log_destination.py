import logging
import warnings

from structlog_config import configure_logger
from tests.utils import temp_env_var


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
