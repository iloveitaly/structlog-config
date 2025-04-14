import logging
import os
from unittest import mock

from structlog_config import configure_logger
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


def test_logger_path_config():
    """Test that LOG_PATH_* environment variables set up file handlers"""
    log_path = "/var/log/httpx.log"

    with temp_env_var({"LOG_PATH_HTTPX": log_path}):
        # Save the original FileHandler class before patching
        original_file_handler = logging.FileHandler

        # Patch FileHandler to avoid actually creating files
        with mock.patch("logging.FileHandler") as mock_file_handler:
            # Configure the logger system
            configure_logger()

            # Get the logger through the standard logging library
            logger = logging.getLogger("httpx")

            # Check that the mock was called with the right path
            mock_file_handler.assert_any_call(log_path)

            # Since we can't use isinstance with the mock, check for the mock in the call args
            found_handler_with_path = False
            for call in mock_file_handler.call_args_list:
                if call.args and call.args[0] == log_path:
                    found_handler_with_path = True
                    break

            assert found_handler_with_path, (
                f"No FileHandler was created with path {log_path}"
            )


def test_multiple_custom_loggers():
    """Test that multiple custom logger configurations are applied correctly"""
    env_vars = {
        "LOG_LEVEL_HTTPX": "DEBUG",
        "LOG_PATH_HTTPX": "/var/log/httpx.log",
        "LOG_LEVEL_ASYNCIO": "WARNING",
        "LOG_PATH_CUSTOM_LOGGER": "/var/log/custom.log",
    }

    with temp_env_var(env_vars):
        # Patch FileHandler to avoid actually creating files
        with mock.patch("logging.FileHandler", autospec=True) as mock_file_handler:
            # Configure the logger system
            configure_logger()

            # Get all the loggers that should be configured
            httpx_logger = logging.getLogger("httpx")
            asyncio_logger = logging.getLogger("asyncio")
            custom_logger = logging.getLogger("custom.logger")

            # Verify logger levels
            assert httpx_logger.level == logging.DEBUG
            assert asyncio_logger.level == logging.WARNING

            # Verify file handlers were created with right paths
            mock_file_handler.assert_any_call("/var/log/httpx.log")
            mock_file_handler.assert_any_call("/var/log/custom.log")


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
