"""Tests for trace logging functionality."""

import io
import logging
from io import StringIO
from unittest.mock import patch

import structlog

from structlog_config import configure_logger, trace
from structlog_config.constants import TRACE_LOG_LEVEL
from tests.utils import temp_env_var


def remove_trace():
    """Remove trace from logging and structlog."""
    if hasattr(logging.Logger, "trace"):
        delattr(logging.Logger, "trace")
    if hasattr(logging, "trace"):
        delattr(logging, "trace")
    if hasattr(logging, "TRACE"):
        delattr(logging, "TRACE")

    # Clean up structlog patches
    from structlog._log_levels import NAME_TO_LEVEL
    from structlog._native import LEVEL_TO_FILTERING_LOGGER

    NAME_TO_LEVEL.pop("trace", None)
    LEVEL_TO_FILTERING_LOGGER.pop(TRACE_LOG_LEVEL, None)


class TestTraceLevel:
    """Test TRACE logging level functionality."""

    def setup_method(self):
        """Reset trace setup state before each test."""
        # Reset the setup state to allow testing multiple setups
        trace._setup_called = False

        remove_trace()

    def test_env_var_sets_trace_level(self, monkeypatch):
        """Test that setting LOG_LEVEL=TRACE sets root logger to TRACE."""
        monkeypatch.setenv("LOG_LEVEL", "TRACE")
        from structlog_config import configure_logger

        trace._setup_called = False
        remove_trace()

        logger = configure_logger()

        # After configure_logger, TRACE should be set up and root logger should be TRACE
        assert trace._setup_called
        assert hasattr(logging, "TRACE")
        assert logging.getLogger().level == TRACE_LOG_LEVEL

    def test_trace_includes_debug_logs(self):
        """Test that TRACE level includes all DEBUG logs."""
        trace.setup_trace()
        logger = logging.getLogger("test_logger_trace_debug")
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(TRACE_LOG_LEVEL)
        formatter = logging.Formatter("%(levelname)s:%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(TRACE_LOG_LEVEL)
        # Log both TRACE and DEBUG
        logger.trace("trace message")  # type: ignore
        logger.debug("debug message")
        log_output = log_capture.getvalue()
        assert "trace message" in log_output
        assert "debug message" in log_output
        assert "TRACE" in log_output
        assert "DEBUG" in log_output

    def test_trace_level_constant(self):
        """Test that TRACE_LOG_LEVEL is correctly defined."""
        assert TRACE_LOG_LEVEL == 5
        assert TRACE_LOG_LEVEL < logging.DEBUG

    def test_setup_trace_first_time(self):
        """Test initial setup of trace logging."""
        trace.setup_trace()

        # Verify logging module has TRACE level
        assert hasattr(logging, "TRACE")
        assert logging.TRACE == TRACE_LOG_LEVEL  # type: ignore

        # Verify level name is registered
        assert logging.getLevelName(TRACE_LOG_LEVEL) == "TRACE"

        # Verify Logger class has trace method
        assert hasattr(logging.Logger, "trace")

        # Verify module-level trace function exists
        assert hasattr(logging, "trace")
        assert callable(logging.trace)  # type: ignore

    def test_setup_trace_idempotent(self):
        """Test that setup_trace can be called multiple times safely."""
        trace.setup_trace()
        trace.setup_trace()
        trace.setup_trace()

        # Should still work correctly
        assert hasattr(logging, "TRACE")
        assert hasattr(logging.Logger, "trace")
        assert hasattr(logging, "trace")

    def test_logger_trace_method(self):
        """Test that logger instances have working trace method."""
        trace.setup_trace()

        logger = logging.getLogger("test_logger")

        # Set up string buffer to capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(TRACE_LOG_LEVEL)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(TRACE_LOG_LEVEL)

        # Test trace method exists and works
        assert hasattr(logger, "trace")
        logger.trace("Test trace message")  # type: ignore

        # Verify output
        log_output = log_capture.getvalue()
        assert "Test trace message" in log_output
        assert "TRACE" in log_output

    def test_module_level_trace_function(self):
        """Test that module-level logging.trace function works."""
        trace.setup_trace()

        # Set up root logger to capture trace messages
        root_logger = logging.getLogger()
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(TRACE_LOG_LEVEL)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(TRACE_LOG_LEVEL)

        # Test module-level trace function
        logging.trace("Module level trace message")  # type: ignore

        # Verify output
        log_output = log_capture.getvalue()
        assert "Module level trace message" in log_output
        assert "TRACE" in log_output

    def test_trace_level_filtering(self):
        """Test that trace messages are filtered based on log level."""
        trace.setup_trace()

        logger = logging.getLogger("test_logger")
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(TRACE_LOG_LEVEL)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set logger level above TRACE - should not log trace messages
        logger.setLevel(logging.DEBUG)
        logger.trace("This should not appear")  # type: ignore

        # Set logger level to TRACE - should log trace messages
        logger.setLevel(TRACE_LOG_LEVEL)
        logger.trace("This should appear")  # type: ignore

        log_output = log_capture.getvalue()
        assert "This should not appear" not in log_output
        assert "This should appear" in log_output

    @patch("logging.warning")
    def test_existing_trace_method_warning(self, mock_warning):
        """Test warning when trace method already exists."""
        # Manually add a trace method to test collision detection
        logging.Logger.trace = lambda self, msg: None  # type: ignore

        trace.setup_trace()

        # Should have warned about existing method
        mock_warning.assert_called_with(
            "Logger.trace method already exists, not overriding it"
        )

    @patch("logging.warning")
    def test_existing_trace_function_warning(self, mock_warning):
        """Test warning when trace function already exists."""
        # Manually add a trace function to test collision detection
        logging.trace = lambda msg: None  # type: ignore

        trace.setup_trace()

        # Should have warned about existing function
        mock_warning.assert_called_with(
            "logging.trace function already exists, overriding it"
        )

    @patch("logging.warning")
    def test_name_to_level_already_patched_warning(self, mock_warning):
        """Test warning when NAME_TO_LEVEL already contains trace."""
        from structlog._log_levels import NAME_TO_LEVEL

        # Manually add trace to NAME_TO_LEVEL to simulate already patched state
        NAME_TO_LEVEL["trace"] = TRACE_LOG_LEVEL

        trace.setup_trace()

        # Should have warned about existing trace key
        mock_warning.assert_any_call(
            "NAME_TO_LEVEL already contains 'trace' key, this may indicate "
            "the code has already been patched or structlog now supports trace natively"
        )

    @patch("logging.warning")
    def test_level_to_filtering_logger_already_patched_warning(self, mock_warning):
        """Test warning when LEVEL_TO_FILTERING_LOGGER already contains TRACE_LOG_LEVEL."""
        from structlog._native import LEVEL_TO_FILTERING_LOGGER

        # Manually add TRACE_LOG_LEVEL to simulate already patched state
        # Use a dummy value since we just want to test the warning
        LEVEL_TO_FILTERING_LOGGER[TRACE_LOG_LEVEL] = object()

        trace.setup_trace()

        # Should have warned about existing trace level
        mock_warning.assert_any_call(
            f"LEVEL_TO_FILTERING_LOGGER already contains {TRACE_LOG_LEVEL} level, "
            "this may indicate the code has already been patched or structlog now supports trace natively"
        )

    def test_trace_with_args_and_kwargs(self):
        """Test trace logging with arguments and keyword arguments."""
        trace.setup_trace()

        logger = logging.getLogger("test_logger")
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(TRACE_LOG_LEVEL)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(TRACE_LOG_LEVEL)

        # Test with positional arguments
        logger.trace("Test message with args: %s %d", "hello", 42)  # type: ignore

        # Test with keyword arguments
        logger.trace("Test message", extra={"custom_field": "value"})  # type: ignore

        log_output = log_capture.getvalue()
        assert "Test message with args: hello 42" in log_output
        assert "Test message" in log_output
        assert "TRACE" in log_output

    def test_trace_level_name_registration(self):
        """Test that TRACE level name is properly registered."""
        trace.setup_trace()

        assert logging.getLevelName(TRACE_LOG_LEVEL) == "TRACE"
        assert logging.getLevelName("TRACE") == TRACE_LOG_LEVEL

    def test_setup_called_flag(self):
        """Test that _setup_called flag works correctly."""
        assert not trace._setup_called

        trace.setup_trace()
        assert trace._setup_called

        # Reset and test again
        trace._setup_called = False
        assert not trace._setup_called

        trace.setup_trace()
        assert trace._setup_called


class TestTraceIntegration:
    """Test trace integration with structlog_config."""

    def test_trace_imported_in_init(self):
        """Test that trace module is imported in __init__.py."""
        from structlog_config import trace as imported_trace

        assert imported_trace is not None

    def test_setup_trace_imported(self):
        """Test that setup_trace function is importable."""
        from structlog_config.trace import setup_trace

        assert callable(setup_trace)

    def test_configure_logger_sets_up_trace(self):
        """Test that configure_logger calls setup_trace."""
        # Reset trace state
        trace._setup_called = False

        configure_logger()

        # Should have set up trace
        assert trace._setup_called
        assert hasattr(logging, "TRACE")
        assert hasattr(logging.Logger, "trace")

    def test_configure_logger_supports_trace(self):
        """Test that structlog logger exposes the trace method."""
        output = StringIO()

        with temp_env_var({"LOG_LEVEL": "TRACE"}):
            log = configure_logger(
                logger_factory=structlog.PrintLoggerFactory(file=output)
            )
            log.trace("This is trace")

        log_output = output.getvalue()
        assert "This is trace" in log_output

    def test_configure_logger_supports_stdlib_trace(self):
        """Test that stdlib loggers expose trace after configuration."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setLevel(TRACE_LOG_LEVEL)
        formatter = logging.Formatter("%(levelname)s:%(message)s")
        handler.setFormatter(formatter)

        with temp_env_var({"LOG_LEVEL": "TRACE"}):
            configure_logger()
            logger = logging.getLogger("test_logger_trace")
            logger.setLevel(TRACE_LOG_LEVEL)
            logger.addHandler(handler)
            logger.trace("stdlib trace message")  # type: ignore

        log_output = output.getvalue()
        assert "stdlib trace message" in log_output
        assert "TRACE" in log_output

    def test_trace_print_logger_output(self):
        output = StringIO()

        with temp_env_var({"LOG_LEVEL": "TRACE"}):
            log = configure_logger(
                logger_factory=structlog.PrintLoggerFactory(file=output)
            )
            log.trace("print trace")

        assert "print trace" in output.getvalue()

    def test_trace_write_logger_output(self):
        output = StringIO()

        with temp_env_var({"LOG_LEVEL": "TRACE"}):
            log = configure_logger(
                logger_factory=structlog.WriteLoggerFactory(file=output)
            )
            log.trace("write trace")

        assert "write trace" in output.getvalue()

    def test_trace_bytes_logger_output(self):
        output = io.BytesIO()

        with temp_env_var({"LOG_LEVEL": "TRACE"}):
            log = configure_logger(
                logger_factory=structlog.BytesLoggerFactory(file=output),
                json_logger=True,
            )
            log.trace("bytes trace")

        assert b"bytes trace" in output.getvalue()


class TestTraceStub:
    """Test the Logger stub class for type checking."""

    def test_logger_stub_exists(self):
        """Test that Logger stub class exists."""
        assert hasattr(trace, "Logger")
        assert issubclass(trace.Logger, logging.Logger)

    def test_logger_stub_has_trace_method(self):
        """Test that Logger stub has trace method signature."""
        logger_stub = trace.Logger("test")
        assert hasattr(logger_stub, "trace")

        # Should be able to call it (though it's a no-op stub)
        logger_stub.trace("test message")
