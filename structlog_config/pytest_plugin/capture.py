import sys
from dataclasses import dataclass


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
