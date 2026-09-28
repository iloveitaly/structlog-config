# structlog_config.tee

Request-scoped and execution-context log teeing.

with tee_logs(path): copies logs emitted in that execution context to a file
while retaining the configured primary output. Hooks installed by configure_logger
read a ContextVar at emission time, so existing loggers can serve concurrent
requests without mixing their capture files or replacing sys.stdout. Structlog
printers and stdlib handlers mirror already-rendered records after primary output
succeeds, preserving filtering and formatting without running processors twice.
Inherited contexts share each sink, which stops accepting writes when its block
exits even if a child task continues running.

## Classes

| [`ScopeSink`](#structlog_config.tee.ScopeSink)   | Tracks the capture destination for one with tee_logs(path): block.   |
|--------------------------------------------------------------|----------------------------------------------------------------------|

## Functions

| [`emit_to_sinks`](#structlog_config.tee.emit_to_sinks)(→ None)                      | Mirror a rendered log record payload to all sinks active in the current context                                 |
|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| [`wrap_logger_factory_for_tee`](#structlog_config.tee.wrap_logger_factory_for_tee)(→ Any)         | Add tee support to PrintLoggerFactory and BytesLoggerFactory, once only. This is run from the entrypoint to the |
| [`is_tee_configured`](#structlog_config.tee.is_tee_configured)(→ bool)                  | Check whether the active structlog configuration includes tee support                                           |
| [`tee_logs`](#structlog_config.tee.tee_logs)(→ collections.abc.Iterator[None]) | Primary user-facing context manager to mirror logs to a file or stream.                                         |

## Module Contents

### *class* structlog_config.tee.ScopeSink(file: [io.TextIOBase](https://docs.python.org/3/library/io.html#io.TextIOBase) | BinaryIO, , close_file: [bool](https://docs.python.org/3/builtins/functions.html#bool))

Tracks the capture destination for one with tee_logs(path): block.

This is the additional file or stream receiving copies of logs, such as
operation.log, not the logger’s normal output destination.

asyncio.create_task() copies the parent’s context by default. The copied
\_ACTIVE_SINKS value contains references to the same ScopeSink objects, not
copies of their files. Resetting the parent’s ContextVar does not update the
child’s context. On scope exit, close() therefore disables this shared object
so a child that continues running cannot write through it. Only files opened
by tee_logs are closed; caller-provided streams remain open.

#### file *: [io.TextIOBase](https://docs.python.org/3/library/io.html#io.TextIOBase) | BinaryIO | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### close_file

#### lock

#### write(payload: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [bytes](https://docs.python.org/3/builtins/stdtypes.html#bytes)) → [None](https://docs.python.org/3/builtins/constants.html#None)

#### close() → [None](https://docs.python.org/3/builtins/constants.html#None)

### structlog_config.tee.emit_to_sinks(payload: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [bytes](https://docs.python.org/3/builtins/stdtypes.html#bytes)) → [None](https://docs.python.org/3/builtins/constants.html#None)

Mirror a rendered log record payload to all sinks active in the current context

### structlog_config.tee.wrap_logger_factory_for_tee(factory: Any) → Any

Add tee support to PrintLoggerFactory and BytesLoggerFactory, once only. This is run from the entrypoint to the
logging configuration.

Other factories are left unchanged for ordinary logging, but tee_logs rejects
them. This includes WriteLoggerFactory and structlog.stdlib.LoggerFactory;
the latter routes structlog itself through stdlib handlers, a different
pipeline from the direct printers wrapped here.

### structlog_config.tee.is_tee_configured() → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Check whether the active structlog configuration includes tee support

### structlog_config.tee.tee_logs(path: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [pathlib.Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [io.TextIOBase](https://docs.python.org/3/library/io.html#io.TextIOBase) | BinaryIO) → [collections.abc.Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[None](https://docs.python.org/3/builtins/constants.html#None)]

Primary user-facing context manager to mirror logs to a file or stream.

All enabled records emitted through configured structlog loggers and stdlib loggers
during this scope (including concurrent tasks inheriting this context) are appended
to the capture destination. Primary output destinations remain unchanged.

* **Parameters:**
  **path** – A str or Path opened in binary append mode and closed on scope exit,
  or a writable text/binary stream such as StringIO, BytesIO, or an open
  file. Supplied streams are flushed but never closed or repositioned.
  Text streams must inherit io.TextIOBase; JSON bytes are decoded as
  UTF-8 before writing. Binary streams receive UTF-8 bytes unchanged.
