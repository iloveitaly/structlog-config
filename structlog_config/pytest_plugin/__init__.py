"""Pytest plugin for capturing test output to files on failure.

This plugin captures stdout, stderr, and exceptions from failing tests and writes
them to organized output directories.

Relationship to pytest's built-in capture:
    - pytest has built-in output capture that shows output only for failing tests
    - This plugin REPLACES pytest's capture (we require -s to disable it)
    - Instead of showing output inline, we write it to organized files
    - Useful for CI/CD where you need persistent files to inspect later

Capture:
    SimpleCapture replaces sys.stdout/stderr with StringIO objects.
    - Captures: print(), logging, most Python output
    - Misses: subprocess output, direct fd writes

    For subprocess output capture, call configure_subprocess_capture() at the
    top of your subprocess entrypoint. It reads STRUCTLOG_CAPTURE_DIR (set
    automatically per-test) and redirects the child process's own fds there.

Usage:
    pytest --structlog-output=./test-output -s

Options:
    --structlog-output=DIR      Enable output capture and write to DIR

Requirements:
    - Must use -s (--capture=no) flag to disable pytest's built-in capture

Output Structure:
    DIR/
        test_module__test_name/
            stdout.txt      # stdout from test
            stderr.txt      # stderr from test
            exception.txt   # exception traceback
            exception.json  # structured exception data (requires beautiful_traceback)
"""

import os
import shutil
from contextlib import contextmanager

import pytest
from pytest_plugin_utils import (
    get_artifact_dir,
    set_artifact_dir_option,
    get_pytest_option,
)
from pathlib import Path

from .capture import SimpleCapture
from .constants import (
    CAPTURE_ENABLED_KEY,
    CAPTURE_KEY,
    CAPTURE_OUTPUT_DIR_KEY,
    CAPTURED_TESTS_KEY,
    PERSIST_FAILED_ONLY,
    PLUGIN_NAMESPACE,
    SLOW_THRESHOLD_KEY,
    SUBPROCESS_CAPTURE_ENV,
    logger,
)
from .output import (
    _accumulate_captured_output,
    _clean_artifact_dir,
    _write_output_files,
)
from .reporting import _collect_slow_reports, _write_results_json
from .subprocess_capture import configure_subprocess_capture

__all__ = ["configure_subprocess_capture"]


def _validate_pytest_config(config: pytest.Config) -> bool:
    """Check that -s is enabled. Log error if not.

    Note: We also recommend using -p no:logging to disable pytest's logging plugin,
    but we can't reliably detect if it's enabled. The pluginmanager.has_plugin()
    check doesn't work consistently across pytest versions. The plugin will work
    regardless, but having both logging captures enabled may cause confusion.
    """
    capture_mode = config.option.capture

    if capture_mode != "no":
        logger.error(
            "structlog output capture requires -s flag to disable pytest's built-in capture",
            pytest_capture_mode=capture_mode,
            required_flag="-s or --capture=no",
        )
        return False

    return True


@contextmanager
def _simple_capture_phase(item: pytest.Item):
    """Start/stop SimpleCapture around a single test phase, then accumulate output."""
    config = item.config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})

    if not config[CAPTURE_ENABLED_KEY]:
        yield
        return

    capture = SimpleCapture()
    capture.start()
    try:
        yield
    finally:
        output = capture.stop()
        _accumulate_captured_output(item, output)


def pytest_addoption(parser: pytest.Parser):
    """Called once at startup to register CLI options before any tests are collected."""
    group = parser.getgroup("Structlog Capture")
    group.addoption(
        "--structlog-output",
        action="store",
        default=None,
        metavar="DIR",
        help="Enable output capture on test failure and write to DIR",
    )
    group.addoption(
        "--no-structlog",
        action="store_true",
        default=False,
        help="Disable all structlog pytest capture functionality",
    )
    group.addoption(
        "--slow-test-threshold",
        action="store",
        default=1.0,
        type=float,
        metavar="SECONDS",
        help="Duration threshold in seconds above which passing tests are reported as slow (0 to disable)",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config):
    """Called once at startup after options are parsed; used to enable/disable the plugin."""
    # User explicitly disabled the plugin
    if config.getoption("--no-structlog", False):
        config.stash[CAPTURE_KEY] = {CAPTURE_ENABLED_KEY: False}
        config.stash[SLOW_THRESHOLD_KEY] = None
        return

    # Store slow test threshold (independent of capture; active whenever plugin is not disabled)
    threshold = config.getoption("--slow-test-threshold", default=1.0)
    config.stash[SLOW_THRESHOLD_KEY] = threshold if threshold > 0 else None

    # Disable when interactive debugger is active (--pdb, --trace) to avoid interfering with debugger I/O
    if config.getvalue("usepdb") or config.getvalue("trace"):
        logger.info(
            "structlog output capture disabled due to interactive debugger flags"
        )
        config.stash[CAPTURE_KEY] = {CAPTURE_ENABLED_KEY: False}
        return

    set_artifact_dir_option(PLUGIN_NAMESPACE, "structlog_output")
    output_dir_str = get_pytest_option(
        PLUGIN_NAMESPACE, config, "structlog_output", type_hint=Path
    )

    # No output directory specified, nothing to capture
    if not output_dir_str:
        logger.info("structlog output capture disabled, no output directory specified")
        config.stash[CAPTURE_KEY] = {CAPTURE_ENABLED_KEY: False}
        return

    # Config validation failed (e.g., conflicting capture modes)
    if not _validate_pytest_config(config):
        logger.info("structlog output capture disabled due to invalid configuration")
        config.stash[CAPTURE_KEY] = {CAPTURE_ENABLED_KEY: False}
        return

    config.stash[CAPTURE_KEY] = {
        CAPTURE_ENABLED_KEY: True,
        CAPTURE_OUTPUT_DIR_KEY: str(output_dir_str),
    }
    config.stash[CAPTURED_TESTS_KEY] = []

    logger.info(
        "structlog output capture enabled",
        output_directory=str(output_dir_str),
    )


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_setup(item: pytest.Item):
    """Called before each test to run its fixtures; capture starts here."""
    with _simple_capture_phase(item):
        return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_call(item: pytest.Item):
    """Called to execute the test function body; capture continues here."""
    with _simple_capture_phase(item):
        return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ARG001
    """Called after each test to tear down its fixtures; capture ends here."""
    with _simple_capture_phase(item):
        return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ARG001
    """Wraps the full setup→call→teardown sequence for a single test; used here to manage the artifact dir and subprocess env var."""
    config = item.config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})

    if not config[CAPTURE_ENABLED_KEY]:
        return (yield)

    artifact_dir = get_artifact_dir(PLUGIN_NAMESPACE, item)

    # Wipe stale files from any previous run of this test before starting fresh
    _clean_artifact_dir(artifact_dir)

    # Tell subprocesses where to write their captured output
    os.environ[SUBPROCESS_CAPTURE_ENV] = str(artifact_dir)

    try:
        return (yield)
    finally:
        # Remove env var so it doesn't leak into subsequent tests
        os.environ.pop(SUBPROCESS_CAPTURE_ENV, None)
        _write_output_files(item)

        # Clean up artifacts for successful tests when PERSIST_FAILED_ONLY is enabled
        should_clean = (
            PERSIST_FAILED_ONLY
            and not hasattr(item, "_excinfo")
            and artifact_dir.exists()
        )
        if should_clean:
            shutil.rmtree(artifact_dir)
        elif artifact_dir.exists() and not any(artifact_dir.iterdir()):
            # Remove empty artifact directories
            artifact_dir.rmdir()


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Called once per phase (setup/call/teardown) after it completes; used here to collect exception info for failed tests."""
    if call.when == "call":
        item._test_duration = call.duration  # type: ignore[attr-defined]

    # Filter out skipped tests - they should be treated as successful
    if call.excinfo is not None and not call.excinfo.errisinstance(
        pytest.skip.Exception
    ):
        if not hasattr(item, "_excinfo"):
            item._excinfo = []  # type: ignore[attr-defined]
        item._excinfo.append((call.when, call.excinfo))  # type: ignore[attr-defined]


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    """Called once after all tests finish, just before pytest exits; used here to print the capture summary."""
    capture_config = config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})
    slow_threshold = config.stash.get(SLOW_THRESHOLD_KEY, None)

    captured_tests = config.stash.get(CAPTURED_TESTS_KEY, [])
    if capture_config[CAPTURE_ENABLED_KEY] and captured_tests:
        terminalreporter.write_sep("=", "structlog output captured")
        for failure in captured_tests:
            terminalreporter.write("[failed]", red=True, bold=True)
            duration_str = (
                f" {failure.duration:.2f}s" if failure.duration is not None else ""
            )
            location = (
                f"{failure.file}:{failure.line}"
                if failure.line is not None
                else failure.file
            )
            terminalreporter.write_line(f"{duration_str} {location}")
            terminalreporter.write_line(f"  logs: {failure.artifact_dir}/")
            if failure.exception_summary:
                terminalreporter.write_line(f"  {failure.exception_summary}")
            terminalreporter.write_line("")

        _write_results_json(captured_tests, capture_config[CAPTURE_OUTPUT_DIR_KEY])

    if slow_threshold is not None:
        slow_reports = _collect_slow_reports(terminalreporter, slow_threshold)
        if slow_reports:
            terminalreporter.write_sep("=", "slow tests")
            for report in slow_reports:
                terminalreporter.write("[slow]", yellow=True)
                terminalreporter.write_line(f" {report.duration:.2f}s {report.nodeid}")
