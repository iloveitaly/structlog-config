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

    3. Optional: Persist all logs to a directory:
       pytest --capture-logs-dir=/path/to/logs

How it works:
    - Sets PYTHON_LOG_PATH to a unique temp file for each test
    - Logs are written to /tmp/<project-name>-pytest-logs-*/test_name.log
    - On test failure, prints captured logs to stdout
    - Cleans up temp files after each test (unless --capture-logs-dir is set)
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
from pathlib import Path
from typing import Generator

import pytest

logger = logging.getLogger(__name__)

PLUGIN_KEY = pytest.StashKey[dict]()
SESSION_TMPDIR_KEY = "session_tmpdir"


def sanitize_filename(name: str) -> str:
    """Replace non-filename-safe characters with underscores.

    Args:
        name: The filename to sanitize (typically a pytest nodeid).

    Returns:
        A filesystem-safe filename string.
    """
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def pytest_addoption(parser: pytest.Parser) -> None:
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
    parser.addoption(
        "--capture-logs-dir",
        action="store",
        default=None,
        help="Directory to persist all test logs (disables automatic cleanup).",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Configure the plugin at pytest startup.

    Stores configuration state on the config object for use by fixtures and hooks.

    Args:
        config: The pytest config object.
    """
    logs_dir = config.getoption("--capture-logs-dir")
    enabled = config.getoption("--capture-logs-on-fail") or logs_dir is not None

    plugin_config = {
        "enabled": enabled,
        "logs_dir": logs_dir,
        "project_name": os.path.basename(str(config.rootdir)),  # type: ignore
    }
    config.stash[PLUGIN_KEY] = plugin_config


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Create a session-level temp directory for log files."""

    config = session.config
    plugin_config = config.stash.get(PLUGIN_KEY, {})

    if not plugin_config.get("enabled"):
        return

    logs_dir = plugin_config.get("logs_dir")
    if logs_dir:
        tmpdir = Path(logs_dir)
        tmpdir.mkdir(parents=True, exist_ok=True)
    else:
        project_name = plugin_config.get("project_name", "pytest")
        tmpdir = Path(tempfile.mkdtemp(prefix=f"{project_name}-pytest-logs-"))

    plugin_config[SESSION_TMPDIR_KEY] = tmpdir
    config.stash[PLUGIN_KEY] = plugin_config


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    """Clean up session-level temp directory unless --capture-logs-dir was used.

    Args:
        session: The pytest session object.
    """
    config = session.config
    plugin_config = config.stash.get(PLUGIN_KEY, {})

    if not plugin_config.get("enabled"):
        return

    logs_dir = plugin_config.get("logs_dir")
    tmpdir = plugin_config.get(SESSION_TMPDIR_KEY)

    if tmpdir and not logs_dir:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(autouse=True)
def capture_logs_on_fail(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Set up per-test log capture to a temporary file.

    This fixture runs automatically for every test when --capture-logs-on-fail is enabled.
    It sets PYTHON_LOG_PATH to redirect logs to a unique temp file, then cleans up after.

    Args:
        request: The pytest request fixture providing test context.

    Yields:
        Control back to the test, then handles cleanup after test completion.
    """
    config = request.config
    plugin_config = config.stash.get(PLUGIN_KEY, {})

    if not plugin_config.get("enabled"):
        yield
        return

    if "PYTHON_LOG_PATH" in os.environ:
        logger.warning(
            "PYTHON_LOG_PATH is already set; pytest-capture-logs-on-fail plugin is disabled for this test."
        )
        yield
        return

    tmpdir = plugin_config.get(SESSION_TMPDIR_KEY)
    if not tmpdir:
        logger.warning("Session temp directory not initialized")
        yield
        return

    test_name = sanitize_filename(request.node.nodeid)
    log_file = tmpdir / f"{test_name}.log"

    original_log_path = os.environ.get("PYTHON_LOG_PATH")
    os.environ["PYTHON_LOG_PATH"] = str(log_file)

    logger.info(f"Logs for test '{request.node.nodeid}' will be stored at: {log_file}")

    yield

    setattr(request.node, "_pytest_log_file", str(log_file))

    if original_log_path is not None:
        os.environ["PYTHON_LOG_PATH"] = original_log_path
    else:
        del os.environ["PYTHON_LOG_PATH"]


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Hook called after each test phase to create test reports.

    On test failure, reads and prints the captured log file to stdout.
    Handles failures in setup, call, and teardown phases.

    Args:
        item: The test item being reported on.
        call: The call object containing execution info and any exception.
    """
    config = item.config
    plugin_config = config.stash.get(PLUGIN_KEY, {})

    if not plugin_config.get("enabled"):
        return

    if call.excinfo is not None:
        log_file = getattr(item, "_pytest_log_file", None)
        if log_file and os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = f.read()

            if logs.strip():
                phase = call.when
                print(
                    f"\n--- Captured logs for failed test ({phase}): {item.nodeid} ---\n{logs}\n"
                )
