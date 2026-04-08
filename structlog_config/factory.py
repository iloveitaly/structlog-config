import sys
from pathlib import Path
from typing import BinaryIO, Literal, TextIO, cast

import structlog

from .env import get_env


# TODO I'm skeptical about this LazyStream implementation, I'd like to see if we can special case the testing case and remove this in the future
class LazyStream:
    """Defers resolution of sys.stdout/stderr to write time.

    This is critical when tests redirect sys.stdout per-phase (pytest's capture resets
    sys.stdout between fixture-setup and test-call phases), so we must not capture
    the stream at configure time.
    """

    def __init__(self, name: str):
        self.name = name

    def write(self, data):
        getattr(sys, self.name).write(data)

    def flush(self):
        getattr(sys, self.name).flush()

    def isatty(self):
        return getattr(sys, self.name).isatty()


# TODO same here: skeptical that we can't eliminate the need for these...
class LazyBuffer:
    """Binary version of LazyStream for BytesLoggerFactory."""

    def __init__(self, name: str):
        self.name = name

    def write(self, data):
        getattr(sys, self.name).buffer.write(data)

    def flush(self):
        getattr(sys, self.name).buffer.flush()


def _open_python_log_path_directory(python_log_path: str) -> Path:
    """Ensure the configured log path is writable before either logger stack opens it.

    Structlog and stdlib logging both derive file destinations from PYTHON_LOG_PATH,
    so the parent directory needs to exist regardless of whether we later open the
    file in binary mode for JSON logging or text mode for console logging.
    """
    path = Path(python_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    return path


def _open_python_log_path_binary(python_log_path: str) -> BinaryIO:
    """Open PYTHON_LOG_PATH for JSON logging.

    The JSON pipeline uses orjson, which renders bytes, so BytesLoggerFactory needs
    a binary file handle instead of the text handle used by PrintLoggerFactory.
    """
    path = _open_python_log_path_directory(python_log_path)

    return cast(BinaryIO, path.open("ab"))


def _open_python_log_path_text(python_log_path: str) -> TextIO:
    """Open PYTHON_LOG_PATH for non-JSON logging.

    Console logging renders text, so PrintLoggerFactory expects a text file handle.
    This stays separate from the binary helper to keep the logger factory wiring and
    typing explicit.
    """
    path = _open_python_log_path_directory(python_log_path)

    return cast(TextIO, path.open("a", encoding="utf-8"))


def python_log_stream_name(
    python_log_path: str | None,
) -> Literal["stderr", "stdout"] | None:
    """Return the reserved stream name for PYTHON_LOG_PATH, if one was requested.

    The values `stdout` and `stderr` are treated as symbolic stream destinations
    rather than literal filesystem paths so env-based routing can reuse the same
    lazy stream handling as explicit logger factories.
    """
    if not python_log_path:
        return None

    stream_name = python_log_path.lower()
    if stream_name == "stdout" or stream_name == "stderr":
        return stream_name

    return None


def get_logger_factory(json_logger: bool):
    """Build the default structlog logger factory for the current environment.

    PYTHON_LOG_PATH can target either a real file path or the reserved stream
    names `stdout` and `stderr`. JSON mode requires bytes output, while console
    mode requires text output.
    """

    # avoid a constant for this ENV so we can mutate within tests
    python_log_path = get_env("PYTHON_LOG_PATH")

    # determine if the user specified one of the magic std stream names
    std_stream_name = python_log_stream_name(python_log_path)

    # json_logger requires a BytesLoggerFactory
    if json_logger:
        if std_stream_name:
            return structlog.BytesLoggerFactory(
                file=cast(BinaryIO, LazyBuffer(std_stream_name))
            )

        if python_log_path:
            python_log = _open_python_log_path_binary(python_log_path)
            return structlog.BytesLoggerFactory(file=python_log)

        # JSON mode requires binary stream for high-performance orjson serialization
        return structlog.BytesLoggerFactory(file=cast(BinaryIO, LazyBuffer("stdout")))

    if std_stream_name:
        return structlog.PrintLoggerFactory(
            file=cast(TextIO, LazyStream(std_stream_name))
        )

    if python_log_path:
        python_log = _open_python_log_path_text(python_log_path)
        return structlog.PrintLoggerFactory(file=python_log)

    return structlog.PrintLoggerFactory(file=cast(TextIO, LazyStream("stdout")))
