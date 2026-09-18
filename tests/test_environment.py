import logging
import os
from unittest import mock

from structlog_config import configure_logger, tee_logs
from tests.utils import temp_env_var


def test_empty_environment():
    """Test that no special logger configuration happens with an empty environment"""
    with mock.patch.dict(os.environ, {}, clear=True):
        # Configure the logger system
        configure_logger()

        # Get a standard logger - it should have default configuration
        logger = logging.getLogger("httpx")

        # By default, this logger should be at WARNING level in our config
        assert logger.level == logging.WARNING


def test_logger_level_config():
    """Test that LOG_LEVEL_* environment variables set the logger level"""
    with temp_env_var({"LOG_LEVEL_HTTPX": "DEBUG"}):
        # Configure the logger system
        configure_logger()

        # Get the logger through the standard logging library
        logger = logging.getLogger("httpx")

        # The logger should now be at DEBUG level
        assert logger.level == logging.DEBUG

        # Test that a logger can log at DEBUG level
        with mock.patch.object(logger, "debug") as mock_debug:
            logger.debug("Test debug")
            mock_debug.assert_called_once_with("Test debug")


def test_logger_path_config(tmp_path):
    """Test that LOG_PATH_* environment variables set up file handlers"""
    log_path = tmp_path / "httpx.log"
    mirror_path = tmp_path / "scope.log"

    with temp_env_var({"LOG_PATH_HTTPX": str(log_path)}):
        configure_logger()
        logger = logging.getLogger("httpx")
        with tee_logs(mirror_path):
            logger.warning("file destination event")

    assert "file destination event" in log_path.read_text()
    assert mirror_path.read_bytes() == log_path.read_bytes()


def test_multiple_custom_loggers(tmp_path):
    """Test that multiple custom logger configurations are applied correctly"""
    env_vars = {
        "LOG_LEVEL_HTTPX": "DEBUG",
        "LOG_PATH_HTTPX": str(tmp_path / "httpx.log"),
        "LOG_LEVEL_ASYNCIO": "WARNING",
        "LOG_PATH_CUSTOM_LOGGER": str(tmp_path / "custom.log"),
    }

    with temp_env_var(env_vars):
        configure_logger()
        httpx_logger = logging.getLogger("httpx")
        asyncio_logger = logging.getLogger("asyncio")
        custom_logger = logging.getLogger("custom.logger")

        assert httpx_logger.level == logging.DEBUG
        assert asyncio_logger.level == logging.WARNING

        with tee_logs(tmp_path / "scope.log"):
            httpx_logger.debug("httpx destination event")
            custom_logger.warning("custom destination event")

    httpx_output = (tmp_path / "httpx.log").read_bytes()
    custom_output = (tmp_path / "custom.log").read_bytes()
    assert b"httpx destination event" in httpx_output
    assert b"custom destination event" not in httpx_output
    assert b"custom destination event" in custom_output
    assert b"httpx destination event" not in custom_output
    assert (tmp_path / "scope.log").read_bytes() == httpx_output + custom_output


def test_logger_name_formatting():
    """Test that logger names with underscores are correctly converted to dots"""
    with temp_env_var({"LOG_LEVEL_AZURE_CORE_PIPELINE": "INFO"}):
        configure_logger()

        # The logger name should be converted from azure_core_pipeline to azure.core.pipeline
        logger = logging.getLogger("azure.core.pipeline")
        assert logger.level == logging.INFO


def test_env_override_defaults():
    "test environment variables override default adjustments"

    with temp_env_var({"LOG_LEVEL_HTTPX": "DEBUG"}):
        configure_logger()

        logger = logging.getLogger("httpx")

        assert logger.level == logging.DEBUG


def test_sys_log_level_is_overwritten_if_higher():
    """Test that reconfiguring the logger uses the latest environment variables"""

    with temp_env_var({"LOG_LEVEL": "INFO"}):
        configure_logger()
        logger = logging.getLogger("httpx")

        assert logger.level == logging.WARNING, (
            "httpx logger should be WARNING by default, as per std_logging_configuration."
        )


def test_sys_log_level_is_skipped_if_not_lower():
    "test that a lower global level is used instead of static overrides"

    with temp_env_var({"LOG_LEVEL": "DEBUG"}):
        configure_logger()
        logger = logging.getLogger("httpx")

        assert logger.level == logging.DEBUG, (
            "httpx logger should be WARNING by default, as per std_logging_configuration."
        )


def test_reconfigure_uses_latest_env_vars():
    """Test that reconfiguring the logger uses the latest environment variables"""

    with temp_env_var({"LOG_LEVEL": ""}):
        configure_logger()
        logger = logging.getLogger("httpx")
        assert logger.level == logging.WARNING, (
            "httpx logger should be WARNING by default, as per std_logging_configuration."
        )

        with temp_env_var({"LOG_LEVEL": "DEBUG"}):
            configure_logger()
            logger = logging.getLogger("httpx")
            assert logger.level == logging.DEBUG, (
                "httpx logger should be DEBUG when LOG_LEVEL=DEBUG, "
                "even though std_logging_configuration would set it to WARNING for INFO."
            )
