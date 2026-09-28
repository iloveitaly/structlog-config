# structlog_config.factory

## Classes

| [`LazyStream`](#structlog_config.factory.LazyStream)   | Defers resolution of sys.stdout/stderr to write time.   |
|---------------------------------------------------------------|---------------------------------------------------------|
| [`LazyBuffer`](#structlog_config.factory.LazyBuffer)   | Binary version of LazyStream for BytesLoggerFactory.    |

## Functions

| [`python_log_stream_name`](#structlog_config.factory.python_log_stream_name)(→ Literal[, ] | None)   | Return the reserved stream name for PYTHON_LOG_PATH, if one was requested.   |
|-------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`get_logger_factory`](#structlog_config.factory.get_logger_factory)(json_logger)                | Build the default structlog logger factory for the current environment.      |

## Module Contents

### *class* structlog_config.factory.LazyStream(name: [str](https://docs.python.org/3/builtins/stdtypes.html#str))

Defers resolution of sys.stdout/stderr to write time.

This is critical when tests redirect sys.stdout per-phase (pytest’s capture resets
sys.stdout between fixture-setup and test-call phases), so we must not capture
the stream at configure time.

#### name

#### write(data)

#### flush()

#### isatty()

### *class* structlog_config.factory.LazyBuffer(name: [str](https://docs.python.org/3/builtins/stdtypes.html#str))

Binary version of LazyStream for BytesLoggerFactory.

#### name

#### write(data)

#### flush()

### structlog_config.factory.python_log_stream_name(python_log_path: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)) → Literal['stderr', 'stdout'] | [None](https://docs.python.org/3/builtins/constants.html#None)

Return the reserved stream name for PYTHON_LOG_PATH, if one was requested.

The values stdout and stderr are treated as symbolic stream destinations
rather than literal filesystem paths so env-based routing can reuse the same
lazy stream handling as explicit logger factories.

### structlog_config.factory.get_logger_factory(json_logger: [bool](https://docs.python.org/3/builtins/functions.html#bool))

Build the default structlog logger factory for the current environment.

PYTHON_LOG_PATH can target either a real file path or the reserved stream
names stdout and stderr. JSON mode requires bytes output, while console
mode requires text output.
