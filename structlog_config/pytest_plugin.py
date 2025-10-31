"""
* Adds a --capture-logs-on-fail pytest option to enable log capture per test.
* For each test, sets PYTHON_LOG_PATH to a unique temp file in a temp directory named after the project root.
* Logs the path where logs will be stored for each test.
* If PYTHON_LOG_PATH is already set, logs a warning and disables log capture for that test.
* On test failure, prints the captured log file to stdout.
* Cleans up temp files after each test.
"""

import logging
import os
import re
import shutil
import tempfile

import pytest

logger = logging.getLogger(__name__)


def sanitize_filename(name):
    # Replace non-filename-safe chars with underscores
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def pytest_addoption(parser):
    parser.addoption(
        "--capture-logs-on-fail",
        action="store_true",
        default=False,
        help="Capture logs to a temp file and dump them to stdout on test failure.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    config._capture_logs_on_fail_enabled = config.getoption("--capture-logs-on-fail")
    # Dynamically determine project name from rootdir
    config._capture_logs_project_name = os.path.basename(str(config.rootdir))


@pytest.fixture(autouse=True)
def capture_logs_on_fail(request):
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

    # Use a temp dir based on the dynamically determined project name
    project_name = getattr(config, "_capture_logs_project_name", "pytest")
    tmpdir = tempfile.mkdtemp(prefix=f"{project_name}-pytest-logs-")
    # Use the test nodeid for the log file name
    test_name = sanitize_filename(request.node.nodeid)
    log_file = os.path.join(tmpdir, f"{test_name}.log")
    os.environ["PYTHON_LOG_PATH"] = log_file

    logger.info(f"Logs for test '{request.node.nodeid}' will be stored at: {log_file}")

    yield

    setattr(request.node, "_pytest_log_file", log_file)
    del os.environ["PYTHON_LOG_PATH"]
    shutil.rmtree(tmpdir, ignore_errors=True)


def pytest_runtest_makereport(item, call):
    config = item.config
    if not getattr(config, "_capture_logs_on_fail_enabled", False):
        return

    if call.when == "call" and call.excinfo is not None:
        log_file = getattr(item, "_pytest_log_file", None)
        if log_file and os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = f.read()
            print(f"\n--- Captured logs for failed test: {item.nodeid} ---\n{logs}\n")
