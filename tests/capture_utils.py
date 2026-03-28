import io
import sys
from contextlib import contextmanager


class CaptureStdout:
    """Context manager that captures stdout and provides access to the captured content."""

    def __init__(self):
        self._stringio = io.StringIO()
        # Mock binary buffer support for BytesLoggerFactory compatibility in tests
        self._buffer = io.BytesIO()
        self._stringio.buffer = self._buffer  # type: ignore[attr-defined]
        self._original_stdout = None

    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = self._stringio
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout

    def getvalue(self):
        """Get the current captured content without ending the capture."""
        # Combine text and decoded binary output to capture both logger types
        val = self._stringio.getvalue()
        val += self._buffer.getvalue().decode("utf-8", errors="replace")
        return val

    def clear(self):
        """Clear captured content but continue capturing."""
        self._stringio.seek(0)
        self._stringio.truncate()
        self._buffer.seek(0)
        self._buffer.truncate()


class CaptureStderr:
    """Context manager that captures stderr and provides access to the captured content."""

    def __init__(self):
        self._stringio = io.StringIO()
        # Mock binary buffer support for BytesLoggerFactory compatibility in tests
        self._buffer = io.BytesIO()
        self._stringio.buffer = self._buffer  # type: ignore[attr-defined]
        self._original_stderr = None

    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = self._stringio
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self._original_stderr

    def getvalue(self):
        """Get the current captured content without ending the capture."""
        # Combine text and decoded binary output to capture both logger types
        val = self._stringio.getvalue()
        val += self._buffer.getvalue().decode("utf-8", errors="replace")
        return val


class CaptureStreams:
    """Context manager that captures both stdout and stderr."""

    def __init__(self):
        self.stdout = CaptureStdout()
        self.stderr = CaptureStderr()

    def __enter__(self):
        self.stdout.__enter__()
        self.stderr.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stdout.__exit__(exc_type, exc_val, exc_tb)
        self.stderr.__exit__(exc_type, exc_val, exc_tb)


@contextmanager
def capture_logger_output():
    """
    Context manager to capture structlog output.

    Returns a tuple of (capture_object, output_file) where output_file can be passed
    to configure_logger and capture_object can be used to get the captured content.

    Example:
        with capture_logger_output() as (capture, output_file):
            log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=output_file))
            log.info("Hello")
            assert "Hello" in capture.getvalue()
    """
    capture = CaptureStdout()
    file = io.StringIO()

    try:
        with capture:
            yield capture, file
    finally:
        # Any cleanup if needed
        pass
