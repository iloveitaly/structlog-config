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
"""

import os
import re
import shutil
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
import structlog
from pytest_plugin_utils import (
    get_artifact_dir,
    get_pytest_option,
    set_artifact_dir_option,
    set_pytest_option,
)

logger = structlog.get_logger(logger_name=f"{__package__}.pytest")


@dataclass
class CapturedTestFailure:
    # "path/to/test.py:42" — from the innermost traceback entry
    location: str
    # directory containing the stdout/stderr/exception capture files for this test
    artifact_dir: Path
    # one-line summary from ExceptionInfo.exconly(): type + message, no traceback
    exception_summary: str | None
    # duration of the test's call phase in seconds
    duration: float | None = None


CAPTURE_KEY = pytest.StashKey[dict]()
"Stash key for the plugin's config dict on pytest.Config."

CAPTURED_TESTS_KEY = pytest.StashKey[list[CapturedTestFailure]]()
"Stash key for the list of failed tests that had output captured."

SLOW_THRESHOLD_KEY = pytest.StashKey[float | None]()
"Stash key for the slow test threshold in seconds; None means slow reporting is disabled."

PLUGIN_NAMESPACE: str = __package__ or "structlog_config"
"Namespace used when registering options and artifact dirs with pytest-plugin-utils."

SUBPROCESS_CAPTURE_ENV = "STRUCTLOG_CAPTURE_DIR"
"Env var set per-test so spawned subprocesses know which artifact directory to write into."

PERSIST_FAILED_ONLY = True
"When True, artifact directories are deleted for passing tests."

CAPTURE_ENABLED_KEY = "enabled"
"Key in the CAPTURE_KEY stash dict that indicates whether the plugin is active."

CAPTURE_OUTPUT_DIR_KEY = "output_dir"
"Key in the CAPTURE_KEY stash dict that holds the root output directory path."

_subprocess_capture_configured = False
"Guard flag so configure_subprocess_capture() is idempotent within a single process."

_subprocess_stdout_file = None
"Open file handle for the current subprocess's stdout capture file."

_subprocess_stderr_file = None
"Open file handle for the current subprocess's stderr capture file."

set_pytest_option(
    PLUGIN_NAMESPACE,
    "structlog_output",
    default=None,
    help="Enable output capture on test failure and write to DIR",
    available=None,
    type_hint=Path,
)

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


@dataclass
class CapturedOutput:
    """Container for captured output from a test phase."""

    stdout: str
    stderr: str
    exception: str | None = None


class SimpleCapture:
    """Captures via sys.stdout/sys.stderr replacement. No subprocess support.

    This works similarly to pytest's built-in capture (which we disable with -s).
    It replaces sys.stdout and sys.stderr with StringIO objects, capturing any
    Python code that writes to these streams (print(), logging, etc.).

    Limitations:
    - Does NOT capture subprocess output (subprocesses inherit file descriptors,
      not Python sys.stdout/stderr objects)
    - Does NOT capture direct file descriptor writes (os.write(1, ...))
    - Only captures output from the current Python process

    For subprocess output capture, use configure_subprocess_capture() instead.
    """

    def __init__(self):
        self._stdout_capture = None
        self._stderr_capture = None
        self._orig_stdout = None
        self._orig_stderr = None

    def start(self):
        """Start capturing stdout and stderr."""
        import io
        import logging

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        self._stdout_capture = io.StringIO()
        self._stderr_capture = io.StringIO()
        sys.stdout = self._stdout_capture
        sys.stderr = self._stderr_capture

        # Update any existing logging handlers that point to the old stdout/stderr
        # This ensures stdlib loggers created before capture started will output
        # to our StringIO objects instead of the original streams
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                if handler.stream == self._orig_stdout:
                    handler.setStream(self._stdout_capture)  # type: ignore[arg-type]
                elif handler.stream == self._orig_stderr:
                    handler.setStream(self._stderr_capture)  # type: ignore[arg-type]

    def stop(self) -> CapturedOutput:
        """Stop capturing and return captured output."""
        import logging

        # Restore logging handlers to original streams
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                if handler.stream == self._stdout_capture:
                    handler.setStream(self._orig_stdout)  # type: ignore[arg-type]
                elif handler.stream == self._stderr_capture:
                    handler.setStream(self._orig_stderr)  # type: ignore[arg-type]

        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr

        stdout = self._stdout_capture.getvalue() if self._stdout_capture else ""
        stderr = self._stderr_capture.getvalue() if self._stderr_capture else ""

        return CapturedOutput(stdout=stdout, stderr=stderr)


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


def _accumulate_captured_output(
    item: pytest.Item, phase_output: CapturedOutput
) -> None:
    """Append per-phase captured output to item's accumulated full output."""
    if not hasattr(item, "_full_captured_output"):
        item._full_captured_output = CapturedOutput(stdout="", stderr="")  # type: ignore[attr-defined]

    existing: CapturedOutput = item._full_captured_output  # type: ignore[attr-defined]
    existing.stdout += phase_output.stdout
    existing.stderr += phase_output.stderr


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


def _write_output_files(item: pytest.Item):
    """Write captured output to files on failure."""
    config = item.config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})
    if not config[CAPTURE_ENABLED_KEY]:
        return

    test_dir = get_artifact_dir(PLUGIN_NAMESPACE, item)

    if hasattr(item, "_full_captured_output"):
        output = item._full_captured_output  # type: ignore[attr-defined]
    else:
        output = CapturedOutput(stdout="", stderr="")

    # Each phase (setup/call/teardown) can fail independently, so excinfo is a list
    exception_parts = []
    first_excinfo = None
    if hasattr(item, "_excinfo"):
        for _when, excinfo in item._excinfo:  # type: ignore[attr-defined]
            if first_excinfo is None:
                first_excinfo = excinfo
            exception_parts.append(str(excinfo.getrepr(style="long")))

    output.exception = "\n\n".join(exception_parts) if exception_parts else None

    files_written = False

    if output.stdout:
        (test_dir / "stdout.txt").write_text(_strip_ansi(output.stdout))
        files_written = True

    if output.stderr:
        (test_dir / "stderr.txt").write_text(_strip_ansi(output.stderr))
        files_written = True

    if output.exception:
        (test_dir / "exception.txt").write_text(_strip_ansi(output.exception))
        files_written = True

    # Only register the test in the summary if files were actually written for a failure
    will_persist = files_written and (
        not PERSIST_FAILED_ONLY or hasattr(item, "_excinfo")
    )
    if not will_persist:
        return

    if first_excinfo is not None:
        # traceback[-1] is the innermost frame — where the assertion/error actually fired
        tb_entry = first_excinfo.traceback[-1]
        # lineno is 0-indexed; +1 converts to the 1-indexed line number editors show
        location = f"{tb_entry.path}:{tb_entry.lineno + 1}"
        # exconly() returns "ExceptionType: message" without the full traceback
        exception_summary = first_excinfo.exconly()
    else:
        location = item.nodeid
        exception_summary = None

    captured_tests = item.config.stash.get(CAPTURED_TESTS_KEY, [])
    captured_tests.append(
        CapturedTestFailure(
            location=location,
            artifact_dir=test_dir,
            exception_summary=exception_summary,
            duration=getattr(item, "_test_duration", None),
        )
    )


def configure_subprocess_capture() -> None:
    """Redirect child process stdout/stderr into per-test capture files.

    This is intended for subprocess entrypoints when using the spawn start method,
    where child processes do not inherit the parent's fd redirection. The parent
    sets STRUCTLOG_CAPTURE_DIR to the per-test artifact directory via the
    --structlog-output option; this function creates subprocess-<pid>-stdout.txt
    and subprocess-<pid>-stderr.txt there.

    If STRUCTLOG_CAPTURE_DIR is not set, this is a no-op.
    """
    global _subprocess_capture_configured
    global _subprocess_stdout_file
    global _subprocess_stderr_file

    # Guard against being called more than once in the same subprocess
    if _subprocess_capture_configured:
        return

    # The parent process sets this env var to the per-test artifact directory
    output_dir = os.getenv(SUBPROCESS_CAPTURE_ENV)
    if not output_dir:
        logger.error("subprocess capture env not set", env_var=SUBPROCESS_CAPTURE_ENV)
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Include PID in filenames so concurrent subprocesses don't overwrite each other
    pid = os.getpid()
    stdout_path = output_path / f"subprocess-{pid}-stdout.txt"
    stderr_path = output_path / f"subprocess-{pid}-stderr.txt"

    _subprocess_stdout_file = open(stdout_path, "a", encoding="utf-8")
    _subprocess_stderr_file = open(stderr_path, "a", encoding="utf-8")

    # Redirect OS-level fds so all writes (including from C extensions) go to the files
    os.dup2(_subprocess_stdout_file.fileno(), 1)
    os.dup2(_subprocess_stderr_file.fileno(), 2)

    # Reopen Python's sys.stdout/stderr to match the redirected fds
    sys.stdout = open(1, "w", encoding="utf-8", errors="replace", closefd=False)
    sys.stderr = open(2, "w", encoding="utf-8", errors="replace", closefd=False)

    # Flush on every newline so output isn't lost if the subprocess exits unexpectedly
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    _subprocess_capture_configured = True


def _clean_artifact_dir(path: Path) -> None:
    if not path.exists():
        return

    for entry in path.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
            continue

        entry.unlink()


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


def _collect_slow_reports(terminalreporter, threshold: float) -> list:
    slow = []
    for report in terminalreporter.stats.get("passed", []):
        if report.when == "call" and report.duration >= threshold:
            slow.append(report)
    return sorted(slow, key=lambda r: r.duration, reverse=True)


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    """Called once after all tests finish, just before pytest exits; used here to print the capture summary."""
    capture_config = config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})
    slow_threshold = config.stash.get(SLOW_THRESHOLD_KEY, None)

    captured_tests = config.stash.get(CAPTURED_TESTS_KEY, [])
    if capture_config[CAPTURE_ENABLED_KEY] and captured_tests:
        terminalreporter.write_sep("=", "structlog output captured")
        for failure in captured_tests:
            terminalreporter.write("[failed]", red=True, bold=True)
            duration_str = f" {failure.duration:.2f}s" if failure.duration is not None else ""
            terminalreporter.write_line(f"{duration_str} {failure.location}")
            terminalreporter.write_line(f"  logs: {failure.artifact_dir}/")
            if failure.exception_summary:
                terminalreporter.write_line(f"  {failure.exception_summary}")
            terminalreporter.write_line("")

    if slow_threshold is not None:
        slow_reports = _collect_slow_reports(terminalreporter, slow_threshold)
        if slow_reports:
            terminalreporter.write_sep("=", "slow tests")
            for report in slow_reports:
                terminalreporter.write("[slow]", yellow=True)
                terminalreporter.write_line(f" {report.duration:.2f}s {report.nodeid}")
