"""
Request-scoped and execution-context log teeing.

``with tee_logs(path):`` copies logs emitted in that execution context to a file
while retaining the configured primary output. Hooks installed by configure_logger
read a ContextVar at emission time, so existing loggers can serve concurrent
requests without mixing their capture files or replacing sys.stdout. Structlog
printers and stdlib handlers mirror already-rendered records after primary output
succeeds, preserving filtering and formatting without running processors twice.
Inherited contexts share each sink, which stops accepting writes when its block
exits even if a child task continues running.
"""

import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import partialmethod
from io import TextIOBase
from pathlib import Path
from typing import Any, BinaryIO

import structlog
from structlog._output import BytesLogger, PrintLogger


class ScopeSink:
    """
    Tracks the capture destination for one `with tee_logs(path):` block.

    This is the additional file or stream receiving copies of logs, such as
    operation.log, not the logger's normal output destination.

    asyncio.create_task() copies the parent's context by default. The copied
    _ACTIVE_SINKS value contains references to the same ScopeSink objects, not
    copies of their files. Resetting the parent's ContextVar does not update the
    child's context. On scope exit, close() therefore disables this shared object
    so a child that continues running cannot write through it. Only files opened
    by tee_logs are closed; caller-provided streams remain open.
    """

    def __init__(
        self, file: TextIOBase | BinaryIO, *, close_file: bool
    ) -> None:
        self.file: TextIOBase | BinaryIO | None = file
        self.close_file = close_file
        self.lock = threading.Lock()

    def write(self, payload: str | bytes) -> None:
        # serialize writers with close so the file cannot close mid-record
        with self.lock:
            # inherited contexts can retain this sink after its scope closes
            if self.file is None:
                return

            if isinstance(self.file, TextIOBase):
                # text streams require decoding JSON bytes, but do not re-render records
                text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
                self.file.write(text)
            else:
                # encode console/stdlib text; preserve orjson's UTF-8 bytes unchanged
                data = payload.encode("utf-8") if isinstance(payload, str) else payload
                self.file.write(data)
            self.file.flush()

    def close(self) -> None:
        # wait for pending writes and check state under the same lock as write
        with self.lock:
            if self.file is None:
                return

            file_to_close = self.file
            # disable inherited references even if flushing during close fails
            self.file = None
            if self.close_file:
                file_to_close.close()
            else:
                file_to_close.flush()


# each execution context has its own tuple of capture files; nesting adds a sink
# child contexts inherit the same sink objects so scope exit disables their writes too
_ACTIVE_SINKS: ContextVar[tuple[ScopeSink, ...]] = ContextVar(
    "_ACTIVE_SINKS", default=()
)


def emit_to_sinks(payload: str | bytes) -> None:
    """Mirror a rendered log record payload to all sinks active in the current context."""
    sinks = _ACTIVE_SINKS.get()
    if not sinks:
        return
    for sink in sinks:
        sink.write(payload)


def _emit_with_tee(
    handler: logging.StreamHandler,
    record: logging.LogRecord,
    write_fn: Callable[[str], object],
) -> None:
    """
    Format one stdlib log record, write it normally, then copy it to active sinks.

    A handler sends records to an output destination; its formatter turns each
    LogRecord into text. The formatter installed by redirect_stdlib_loggers uses
    our structlog processors to produce console or JSON text. We format once and
    include the handler's terminator (normally a newline), so both destinations
    receive the same text without running the processors a second time.

    write_fn supplies the stream-specific or file-specific write operation.
    Primary formatting/write/flush errors use stdlib's handleError policy, while
    recursion errors are re-raised. Mirroring happens only after primary output
    succeeds; capture destination errors propagate to the caller.
    """
    try:
        payload = handler.format(record) + handler.terminator
        write_fn(payload)
        handler.flush()
    except RecursionError:
        raise
    except Exception:  # noqa: BLE001
        handler.handleError(record)
        return

    emit_to_sinks(payload)


class _TeeStreamHandler(logging.StreamHandler):
    """
    Send stdlib records to a stream and copy them to active capture files.

    Stdlib logs bypass _TeePrinter, so redirect_stdlib_loggers installs this
    handler for stream destinations. _LazyStreamHandler also inherits this emit
    method while resolving stdout/stderr at emission time. _emit_with_tee handles
    formatting and mirroring; the callback writes to the current primary stream.
    """

    def emit(self, record: logging.LogRecord) -> None:
        _emit_with_tee(
            self,
            record,
            lambda payload: self.stream.write(payload),
        )


class _TeeFileHandler(logging.FileHandler):
    """
    Send stdlib records to a configured primary file and active capture files.

    redirect_stdlib_loggers uses this handler for file destinations, including
    per-logger path overrides. An ordinary FileHandler would write only to its
    primary file and bypass tee capture. This subclass retains FileHandler's file
    setup and cleanup, opens the stream if needed, and delegates formatting and
    mirroring to _emit_with_tee. The primary file is separate from scope files.
    """

    def emit(self, record: logging.LogRecord) -> None:
        def _write(payload: str) -> None:
            if self.stream is None:
                self.stream = self._open()
            self.stream.write(payload)

        _emit_with_tee(self, record, _write)


class _TeePrinter:
    """
    Copy structlog's rendered output without changing its normal destination.

    Structlog calls this object after its processors have produced console text
    or JSON bytes. Unlike stdlib records, these messages need no formatting here.
    Each logging method delegates to the original printer, then sends the same
    rendered message to the context's capture files through emit_to_sinks.
    """

    def __init__(
        self,
        original_printer: PrintLogger | BytesLogger,
    ) -> None:
        self._original_printer = original_printer

    def _emit(self, method_name: str, message: str | bytes) -> None:
        # 1. Primary output: call original printer method unchanged
        method = getattr(
            self._original_printer, method_name, self._original_printer.msg
        )
        method(message)

        # 2. Mirror to active execution context sinks
        # the original printer adds a newline; reproduce it using the message's type
        payload = message + b"\n" if isinstance(message, bytes) else message + "\n"
        emit_to_sinks(payload)

    # preserve named backend methods without repeating the forwarding function
    # partialmethod binds the method name, so info(message) calls _emit("info", message)
    msg = partialmethod(_emit, "msg")
    log = partialmethod(_emit, "log")
    debug = partialmethod(_emit, "debug")
    info = partialmethod(_emit, "info")
    warn = partialmethod(_emit, "warn")
    warning = partialmethod(_emit, "warning")
    err = partialmethod(_emit, "err")
    error = partialmethod(_emit, "error")
    failure = partialmethod(_emit, "failure")
    fatal = partialmethod(_emit, "fatal")
    critical = partialmethod(_emit, "critical")
    exception = partialmethod(_emit, "exception")
    trace = partialmethod(_emit, "trace")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original_printer, name)


# these are the two output factories selected by this package's default configuration
_SUPPORTED_FACTORY_CLASSES = (
    structlog.PrintLoggerFactory,
    structlog.BytesLoggerFactory,
)


class _TeeLoggerFactory:
    """
    Wrap each printer created by structlog with _TeePrinter.

    configure_logger installs this callable as structlog's logger_factory.
    Structlog calls it when constructing a logger, and the original factory still
    selects the primary destination. The wrapper checks active sinks on every
    emission, so a logger created before a tee_logs block can capture inside it.
    """

    def __init__(
        self,
        original_factory: structlog.PrintLoggerFactory | structlog.BytesLoggerFactory,
    ) -> None:
        self._original_factory = original_factory

    def __call__(self, *args: Any, **kwargs: Any) -> _TeePrinter:
        printer = self._original_factory(*args, **kwargs)
        return _TeePrinter(printer)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original_factory, name)


def wrap_logger_factory_for_tee(factory: Any) -> Any:
    """
    Add tee support to PrintLoggerFactory and BytesLoggerFactory, once only.

    Other factories are left unchanged for ordinary logging, but tee_logs rejects
    them. This includes WriteLoggerFactory and structlog.stdlib.LoggerFactory;
    the latter routes structlog itself through stdlib handlers, a different
    pipeline from the direct printers wrapped here.
    """
    if isinstance(factory, _TeeLoggerFactory):
        return factory
    if isinstance(factory, _SUPPORTED_FACTORY_CLASSES):
        return _TeeLoggerFactory(factory)
    return factory


def is_tee_configured() -> bool:
    """Check whether the active structlog configuration includes tee support."""
    if not structlog.is_configured():
        return False
    config = structlog.get_config()
    factory = config.get("logger_factory")
    return isinstance(factory, _TeeLoggerFactory)


@contextmanager
def tee_logs(path: str | Path | TextIOBase | BinaryIO) -> Iterator[None]:
    """
    Copy logs emitted in the active execution context to a file or stream.

    All enabled records emitted through configured structlog loggers and stdlib loggers
    during this scope (including concurrent tasks inheriting this context) are appended
    to the capture destination. Primary output destinations remain unchanged.

    Args:
        path: A str or Path opened in binary append mode and closed on scope exit,
            or a writable text/binary stream such as StringIO, BytesIO, or an open
            file. Supplied streams are flushed but never closed or repositioned.
            Text streams must inherit io.TextIOBase; JSON bytes are decoded as
            UTF-8 before writing. Binary streams receive UTF-8 bytes unchanged.
    """
    if not is_tee_configured():
        raise RuntimeError(
            "tee_logs requires structlog-config to be configured with tee support; "
            "call configure_logger() first with a supported logger_factory."
        )

    if isinstance(path, (str, Path)):
        sink = ScopeSink(file=Path(path).open("ab"), close_file=True)
    else:
        sink = ScopeSink(file=path, close_file=False)

    current_sinks = _ACTIVE_SINKS.get()
    token = _ACTIVE_SINKS.set((*current_sinks, sink))

    try:
        yield
    finally:
        try:
            _ACTIVE_SINKS.reset(token)
        finally:
            sink.close()
