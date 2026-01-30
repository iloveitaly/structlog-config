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
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest
import structlog

logger = structlog.get_logger(logger_name=__name__)

CAPTURE_KEY = pytest.StashKey[dict]()


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

        self._stdout_file = tempfile.NamedTemporaryFile(
            mode="w+b", delete=False
        )
        self._stderr_file = tempfile.NamedTemporaryFile(
            mode="w+b", delete=False
        )

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
        type=str,
        default=None,
        metavar="DIR",
        help="Enable output capture on test failure and write to DIR",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config):
    """Configure the plugin."""
    output_dir_str = config.option.structlog_output

    if not output_dir_str:
        config.stash[CAPTURE_KEY] = {"enabled": False}
        return

    if not _validate_pytest_config(config):
        config.stash[CAPTURE_KEY] = {"enabled": False}
        return

    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    config.stash[CAPTURE_KEY] = {
        "enabled": True,
        "output_dir": str(output_dir),
    }

    logger.info(
        "structlog output capture enabled",
        output_directory=str(output_dir),
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
    """
    request.node._fd_capture_active = True
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

    if not hasattr(item, "_excinfo"):
        return

    output_dir_value = config["output_dir"]
    if not isinstance(output_dir_value, (str, Path)):
        return
    output_dir = Path(output_dir_value)

    test_name = item.nodeid.replace("::", "__").replace("/", "_")
    test_dir = output_dir / test_name
    test_dir.mkdir(parents=True, exist_ok=True)

    if hasattr(item, "_full_captured_output"):
        output = item._full_captured_output  # type: ignore[attr-defined]
    elif _is_fd_capture_active(item) and hasattr(item, "_fd_captured_output"):
        output = item._fd_captured_output  # type: ignore[attr-defined]
    else:
        output = CapturedOutput(stdout="", stderr="")

    exception_parts = []
    for _when, excinfo in item._excinfo:  # type: ignore[attr-defined]
        exception_parts.append(str(excinfo.getrepr(style="long")))

    output.exception = "\n\n".join(exception_parts) if exception_parts else None

    if output.stdout:
        (test_dir / "stdout.txt").write_text(output.stdout)

    if output.stderr:
        (test_dir / "stderr.txt").write_text(output.stderr)

    if output.exception:
        (test_dir / "exception.txt").write_text(output.exception)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ARG001
    """Capture output for entire test lifecycle including makereport phases."""
    config = item.config.stash.get(CAPTURE_KEY, {"enabled": False})

    if not config["enabled"] or _is_fd_capture_active(item):
        return (yield)

    capture = SimpleCapture()
    capture.start()
    try:
        result = yield
        return result
    finally:
        output = capture.stop()
        item._full_captured_output = output  # type: ignore[attr-defined]
        _write_output_files(item)


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Track exception info for failed tests."""
    if call.excinfo is not None:
        if not hasattr(item, "_excinfo"):
            item._excinfo = []  # type: ignore[attr-defined]
        item._excinfo.append((call.when, call.excinfo))  # type: ignore[attr-defined]
