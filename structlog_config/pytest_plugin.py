"""Pytest plugin for capturing test output to files on failure.

This plugin captures stdout, stderr, and exceptions from failing tests and writes
them to organized output directories. It supports both simple capture (via sys.stdout/stderr
replacement) and fd-level capture (for subprocess output).

Relationship to pytest's built-in capture:
    - pytest has built-in output capture that shows output only for failing tests
    - This plugin REPLACES pytest's capture (we require -s to disable it)
    - Instead of showing output inline, we write it to organized files
    - Useful for CI/CD where you need persistent files to inspect later

Capture modes:
    1. SimpleCapture (default): Like pytest's capture, replaces sys.stdout/stderr
       - Captures: print(), logging, most Python output
       - Misses: subprocess output, direct fd writes

    2. FdCapture (opt-in): OS-level file descriptor redirection
       - Captures: everything SimpleCapture does PLUS subprocess output
       - Activate via _fd_capture fixture in conftest.py

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

Enabling fd-level capture (optional):
    To capture subprocess output, you have three options:

    1. Single test - add to function signature:
       def test_foo(file_descriptor_output_capture):
           ...

    2. Single test - use marker decorator:
       @pytest.mark.usefixtures("file_descriptor_output_capture")
       def test_foo():
           ...

    3. All tests in directory - add to conftest.py:
       import pytest
       pytestmark = pytest.mark.usefixtures("file_descriptor_output_capture")
"""

import os
import re
import shutil
import sys
import tempfile
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

CAPTURE_KEY = pytest.StashKey[dict]()
CAPTURED_TESTS_KEY = pytest.StashKey[list[str]]()
PLUGIN_NAMESPACE: str = __package__ or "structlog_config"
SUBPROCESS_CAPTURE_ENV = "STRUCTLOG_CAPTURE_DIR"
PERSIST_FAILED_ONLY = True

_subprocess_capture_configured = False
_subprocess_stdout_file = None
_subprocess_stderr_file = None

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

    This is the default capture mode and works for most tests. Use FdCapture
    (via the _fd_capture fixture) if you need to capture subprocess output.
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


class FdCapture:
    """Captures at file descriptor level. Supports subprocess output.

    This provides deeper capture than SimpleCapture by redirecting at the OS level.
    Instead of just replacing Python's sys.stdout/stderr objects, it redirects
    the actual file descriptors (1=stdout, 2=stderr) that the OS uses.

    How it works:
    1. Backup original file descriptors using os.dup(1) and os.dup(2)
    2. Create temporary files to receive the output
    3. Use os.dup2() to redirect fd 1 and 2 to point to the temp files
    4. Reopen sys.stdout/stderr to match the new file descriptors
    5. All writes to fd 1/2 now go to temp files (including from subprocesses!)
    6. On stop(), restore original fds, read temp file contents, cleanup

    What this captures:
    - Everything SimpleCapture captures (print(), logging, etc.)
    - Subprocess output (when subprocess inherits stdout/stderr)
    - Direct file descriptor writes (os.write(1, ...))
    - C extension output that writes directly to fds

    Comparison to pytest's built-in capture:
    - pytest's -s flag disables pytest's capture (which is SimpleCapture-like)
    - This plugin works INSTEAD of pytest's capture, writing to files rather
      than showing output inline in test results
    - FdCapture is more comprehensive than pytest's default capture

    Note: Opt-in only via _fd_capture fixture due to added complexity.
    """

    def __init__(self):
        self._stdout_fd: int | None = None
        self._stderr_fd: int | None = None
        self._stdout_file: tempfile._TemporaryFileWrapper | None = None
        self._stderr_file: tempfile._TemporaryFileWrapper | None = None
        self._orig_stdout_fd: int | None = None
        self._orig_stderr_fd: int | None = None
        self._orig_stdout = None
        self._orig_stderr = None

    def start(self):
        """Start capturing stdout and stderr at the file descriptor level."""
        sys.stdout.flush()
        sys.stderr.flush()

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        self._orig_stdout_fd = os.dup(1)
        self._orig_stderr_fd = os.dup(2)

        self._stdout_file = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
        self._stderr_file = tempfile.NamedTemporaryFile(mode="w+b", delete=False)

        os.dup2(self._stdout_file.fileno(), 1)
        os.dup2(self._stderr_file.fileno(), 2)

        sys.stdout = open(1, "w", encoding="utf-8", errors="replace", closefd=False)
        sys.stderr = open(2, "w", encoding="utf-8", errors="replace", closefd=False)

    def stop(self) -> CapturedOutput:
        """Stop capturing and return captured output."""
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            os.fsync(1)
            os.fsync(2)

            assert self._orig_stdout_fd is not None
            assert self._orig_stderr_fd is not None
            assert self._stdout_file is not None
            assert self._stderr_file is not None

            os.dup2(self._orig_stdout_fd, 1)
            os.dup2(self._orig_stderr_fd, 2)
            os.close(self._orig_stdout_fd)
            os.close(self._orig_stderr_fd)

            sys.stdout = self._orig_stdout
            sys.stderr = self._orig_stderr

            self._stdout_file.flush()
            self._stderr_file.flush()
            self._stdout_file.seek(0)
            self._stderr_file.seek(0)
            stdout = self._stdout_file.read().decode("utf-8", errors="replace")
            stderr = self._stderr_file.read().decode("utf-8", errors="replace")

            self._stdout_file.close()
            self._stderr_file.close()

            os.unlink(self._stdout_file.name)
            os.unlink(self._stderr_file.name)

            return CapturedOutput(stdout=stdout, stderr=stderr)
        except Exception:
            sys.stdout = self._orig_stdout
            sys.stderr = self._orig_stderr
            raise


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
    """Add command line options for output capture."""
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


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config):
    """Configure the plugin."""
    # User explicitly disabled the plugin
    if config.getoption("--no-structlog", False):
        config.stash[CAPTURE_KEY] = {"enabled": False}
        return

    # Disable when interactive debugger is active (--pdb, --trace) to avoid interfering with debugger I/O
    if config.getvalue("usepdb") or config.getvalue("trace"):
        logger.info("structlog output capture disabled due to interactive debugger flags")
        config.stash[CAPTURE_KEY] = {"enabled": False}
        return

    set_artifact_dir_option(PLUGIN_NAMESPACE, "structlog_output")
    output_dir_str = get_pytest_option(
        PLUGIN_NAMESPACE, config, "structlog_output", type_hint=Path
    )

    # No output directory specified, nothing to capture
    if not output_dir_str:
        logger.info("structlog output capture disabled, no output directory specified")
        config.stash[CAPTURE_KEY] = {"enabled": False}
        return

    # Config validation failed (e.g., conflicting capture modes)
    if not _validate_pytest_config(config):
        logger.info("structlog output capture disabled due to invalid configuration")
        config.stash[CAPTURE_KEY] = {"enabled": False}
        return

    config.stash[CAPTURE_KEY] = {
        "enabled": True,
        "output_dir": str(output_dir_str),
    }
    config.stash[CAPTURED_TESTS_KEY] = []

    logger.info(
        "structlog output capture enabled",
        output_directory=str(output_dir_str),
    )


@pytest.fixture
def file_descriptor_output_capture(request):
    """Activates fd-level capture for a test.

    This fixture can be used in three ways:

    1. Single test - add to function signature:
       def test_foo(file_descriptor_output_capture):
           ...

    2. Single test - use marker decorator:
       @pytest.mark.usefixtures("file_descriptor_output_capture")
       def test_foo():
           ...

    3. All tests in directory - add to conftest.py:
       pytestmark = pytest.mark.usefixtures("file_descriptor_output_capture")

    Notes:
        - This only captures output from the current process and any subprocesses
          that inherit file descriptors (e.g., forked processes or subprocess.run
          with inherited stdout/stderr).
        - For multiprocessing with the spawn start method, child processes do NOT
          inherit fd redirection. Call configure_subprocess_capture() inside the
          subprocess entrypoint to capture their stdout/stderr.
    """
    request.node._fd_capture_active = True
    logger.info(
        "starting output capture",
        test_id=request.node.nodeid,
        capture_mode="file_descriptor",
    )
    capture = FdCapture()
    capture.start()
    yield
    output = capture.stop()
    request.node._fd_captured_output = output


def _is_fd_capture_active(item: pytest.Item) -> bool:
    """Check if the fd-level capture fixture is active for this test."""
    return getattr(item, "_fd_capture_active", False)


def _write_output_files(item: pytest.Item):
    """Write captured output to files on failure."""
    config = item.config.stash.get(CAPTURE_KEY, {"enabled": False})
    if not config["enabled"]:
        return

    test_dir = get_artifact_dir(PLUGIN_NAMESPACE, item)

    if hasattr(item, "_full_captured_output"):
        output = item._full_captured_output  # type: ignore[attr-defined]
    elif _is_fd_capture_active(item) and hasattr(item, "_fd_captured_output"):
        output = item._fd_captured_output  # type: ignore[attr-defined]
    else:
        output = CapturedOutput(stdout="", stderr="")

    exception_parts = []
    if hasattr(item, "_excinfo"):
        for _when, excinfo in item._excinfo:  # type: ignore[attr-defined]
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

    will_persist = files_written and (
        not PERSIST_FAILED_ONLY or hasattr(item, "_excinfo")
    )
    if will_persist:
        captured_tests = item.config.stash.get(CAPTURED_TESTS_KEY, [])
        captured_tests.append(item.nodeid)


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

    if _subprocess_capture_configured:
        return

    output_dir = os.getenv(SUBPROCESS_CAPTURE_ENV)
    if not output_dir:
        logger.error("subprocess capture env not set", env_var=SUBPROCESS_CAPTURE_ENV)
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pid = os.getpid()
    stdout_path = output_path / f"subprocess-{pid}-stdout.txt"
    stderr_path = output_path / f"subprocess-{pid}-stderr.txt"

    _subprocess_stdout_file = open(stdout_path, "a", encoding="utf-8")
    _subprocess_stderr_file = open(stderr_path, "a", encoding="utf-8")

    os.dup2(_subprocess_stdout_file.fileno(), 1)
    os.dup2(_subprocess_stderr_file.fileno(), 2)

    sys.stdout = open(1, "w", encoding="utf-8", errors="replace", closefd=False)
    sys.stderr = open(2, "w", encoding="utf-8", errors="replace", closefd=False)

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
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ARG001
    """Capture output for entire test lifecycle including makereport phases."""
    config = item.config.stash.get(CAPTURE_KEY, {"enabled": False})

    if not config["enabled"]:
        return (yield)

    artifact_dir = get_artifact_dir(PLUGIN_NAMESPACE, item)
    _clean_artifact_dir(artifact_dir)
    os.environ[SUBPROCESS_CAPTURE_ENV] = str(artifact_dir)

    try:
        if _is_fd_capture_active(item):
            return (yield)

        logger.info(
            "starting output capture", test_id=item.nodeid, capture_mode="simple"
        )
        capture = SimpleCapture()
        capture.start()
        try:
            result = yield
            return result
        finally:
            output = capture.stop()
            item._full_captured_output = output  # type: ignore[attr-defined]
    finally:
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
    """Track exception info for failed tests."""
    # Filter out skipped tests - they should be treated as successful
    if call.excinfo is not None and not call.excinfo.errisinstance(pytest.skip.Exception):
        if not hasattr(item, "_excinfo"):
            item._excinfo = []  # type: ignore[attr-defined]
        item._excinfo.append((call.when, call.excinfo))  # type: ignore[attr-defined]


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    """Display summary of captured test output."""
    capture_config = config.stash.get(CAPTURE_KEY, {"enabled": False})
    if not capture_config["enabled"]:
        return

    captured_tests = config.stash.get(CAPTURED_TESTS_KEY, [])
    if not captured_tests:
        return

    output_dir = capture_config["output_dir"]
    terminalreporter.write_sep("=", "structlog output captured")
    terminalreporter.write_line(
        f"{len(captured_tests)} failed test(s) captured to: {output_dir}"
    )
