"""
Pytest plugin for capturing and displaying logs only on test failures.

This plugin integrates with structlog-config's file logging to capture logs per-test
and display them only when tests fail, keeping output clean for passing tests.

Usage:
    1. Install the plugin (automatically registered via entry point):
       pip install structlog-config[fastapi]

    2. Enable in pytest.ini or pyproject.toml:
       [tool.pytest.ini_options]
       addopts = ["--capture-logs-on-fail"]

    Or enable for a single test run:
       pytest --capture-logs-on-fail

How it works:
    - Sets PYTHON_LOG_PATH to a unique temp file for each test
    - Logs are written to /tmp/<project-name>-pytest-logs-*/test_name.log
    - On test failure, prints captured logs to stdout
    - Cleans up temp files after each test
    - Automatically disabled if PYTHON_LOG_PATH is already set

Example output on failure:
    --- Captured logs for failed test: tests/test_foo.py::test_bar ---
    2025-10-31 23:30:00 [info] Starting test
    2025-10-31 23:30:01 [error] Something went wrong
"""

import logging
import os
import re
import shutil
import tempfile

import pytest

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Replace non-filename-safe characters with underscores.

    Args:
        name: The filename to sanitize (typically a pytest nodeid).

    Returns:
        A filesystem-safe filename string.
    """
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def pytest_addoption(parser):
    """Register the --capture-logs-on-fail command line option.

    Args:
        parser: The pytest parser to add options to.
    """
    parser.addoption(
        "--capture-logs-on-fail",
        action="store_true",
        default=False,
        help="Capture logs to a temp file and dump them to stdout on test failure.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Configure the plugin at pytest startup.

    Stores configuration state on the config object for use by fixtures and hooks.

    Args:
        config: The pytest config object.
    """
    config._capture_logs_on_fail_enabled = config.getoption("--capture-logs-on-fail")
    config._capture_logs_project_name = os.path.basename(str(config.rootdir))


@pytest.fixture(autouse=True)
def capture_logs_on_fail(request):
    """Set up per-test log capture to a temporary file.

    This fixture runs automatically for every test when --capture-logs-on-fail is enabled.
    It sets PYTHON_LOG_PATH to redirect logs to a unique temp file, then cleans up after.

    Args:
        request: The pytest request fixture providing test context.

    Yields:
        Control back to the test, then handles cleanup after test completion.
    """
    config = request.config
    if not getattr(config, "_capture_logs_on_fail_enabled", False):
        yield
        return

    if "PYTHON_LOG_PATH" in os.environ:
        logger.warning(
            "PYTHON_LOG_PATH is already set; pytest-capture-logs-on-fail plugin is disabled for this test."
        )
        yield
        return

    project_name = getattr(config, "_capture_logs_project_name", "pytest")
    tmpdir = tempfile.mkdtemp(prefix=f"{project_name}-pytest-logs-")
    test_name = sanitize_filename(request.node.nodeid)
    log_file = os.path.join(tmpdir, f"{test_name}.log")
    os.environ["PYTHON_LOG_PATH"] = log_file

    logger.info(f"Logs for test '{request.node.nodeid}' will be stored at: {log_file}")

    yield

    setattr(request.node, "_pytest_log_file", log_file)
    del os.environ["PYTHON_LOG_PATH"]
    shutil.rmtree(tmpdir, ignore_errors=True)


def pytest_runtest_makereport(item, call):
    """Hook called after each test phase to create test reports.

    On test failure, reads and prints the captured log file to stdout.

    Args:
        item: The test item being reported on.
        call: The call object containing execution info and any exception.
    """
    config = item.config
    if not getattr(config, "_capture_logs_on_fail_enabled", False):
        return

    if call.when == "call" and call.excinfo is not None:
        log_file = getattr(item, "_pytest_log_file", None)
        if log_file and os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = f.read()
            print(f"\n--- Captured logs for failed test: {item.nodeid} ---\n{logs}\n")
