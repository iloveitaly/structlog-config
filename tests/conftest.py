import io
import warnings

import pytest
import structlog

from structlog_config import configure_logger
from structlog_config import warnings as structlog_warning
from tests.capture_utils import CaptureStdout

pytest_plugins = ["structlog_config.pytest_plugin", "structlog_config.pytest_output_capture"]

# TODO this didn't get registered and work for some reason?
# @hookimpl(wrapper=True)
# def pytest_load_initial_conftests(early_config: Config):
#     breakpoint()
#     early_config.known_args_namespace.capture = "no"
#     yield


# @hookimpl(wrapper=False, tryfirst=True)
# def pytest_load_initial_conftests(early_config: Config):
#     # early_config.option.plugins = ["no:logging"]

#     # early_config.option.capture = "no"
#     early_config.known_args_namespace.capture = "no"

#     # breakpoint()
#     print("noooooo")
#     # import pdbr

#     # pdbr.set_trace()


# def pytest_configure(config: Config):


@pytest.fixture
def stdout_capture():
    """
    Fixture that yields a context manager for capturing stdout.

    Example:
        def test_example(stdout_capture):
            with stdout_capture as capture:
                print("Hello")
                assert "Hello" in capture.getvalue()
                # You can keep capturing more output
                print("World")
                assert "Hello" in capture.getvalue()
                assert "World" in capture.getvalue()
    """
    with CaptureStdout() as capture:
        yield capture


# TODO we should move this to the pytest plugin
@pytest.fixture
def capture_logs():
    """
    Fixture that provides a logger and access to its output.
    Returns a tuple of (log, capture).
    """
    # Reset structlog to ensure clean state
    structlog.reset_defaults()

    # Create output file and capture object
    output = io.StringIO()
    capture = CaptureStdout()

    with capture:
        # Configure logger with custom logger factory
        log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=output))

        # Clear any context from previous tests
        log.clear()

        # Helper function to get combined output (both stdout and direct file output)
        def get_output():
            return capture.getvalue() + output.getvalue()

        # Add the helper function to the capture object
        capture.get_combined = get_output

        yield log, capture


@pytest.fixture
def capture_prod_logs(monkeypatch):
    """
    Fixture that provides a logger configured for production and access to its output.
    Returns a tuple of (log, capture).
    """
    # Reset structlog to ensure clean state
    structlog.reset_defaults()

    # Create output file and capture object
    output = io.StringIO()
    capture = CaptureStdout()

    with capture:
        # Mock production environment
        monkeypatch.setattr("structlog_config.environments.is_production", lambda: True)
        monkeypatch.setattr("structlog_config.environments.is_staging", lambda: False)

        # Configure logger with custom logger factory
        log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=output))

        # Clear any context from previous tests
        log.clear()

        # Helper function to get combined output (both stdout and direct file output)
        def get_output():
            return capture.getvalue() + output.getvalue()

        # Add the helper function to the capture object
        capture.get_combined = get_output

        yield log, capture


@pytest.fixture(autouse=True)
def reset_warnings_showwarning():
    """
    Autouse fixture to reset warnings.showwarning to its original state before each test.
    """
    orig = warnings.showwarning

    yield

    warnings.showwarning = orig
    structlog_warning._original_warnings_showwarning = None


@pytest.fixture(autouse=True)
def disable_color_output(monkeypatch):
    """Force colorized output off so string assertions stay stable."""
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr("structlog_config.constants.NO_COLOR", True, raising=False)
    monkeypatch.setattr("structlog_config.NO_COLOR", True, raising=False)
    yield


# @pytest.hookimpl(tryfirst=True)
# def pytest_sessionstart(session):
#     """
#     Set NO_COLOR=1 before any tests run, as early as possible.
#     """
#     old = os.environ.get("NO_COLOR")
#     os.environ["NO_COLOR"] = "1"
#     session.config._no_color_env_old = old


# @pytest.hookimpl(trylast=True)
# def pytest_sessionfinish(session, exitstatus):
#     """
#     Restore NO_COLOR after all tests finish.
#     """
#     old = getattr(session.config, "_no_color_env_old", None)
#     if old is not None:
#         os.environ["NO_COLOR"] = old
#     else:
#         os.environ.pop("NO_COLOR", None)
