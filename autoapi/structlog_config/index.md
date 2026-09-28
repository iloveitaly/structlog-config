# structlog_config

## Submodules

* [structlog_config.env_config](env_config/index.md)
* [structlog_config.factory](factory/index.md)
* [structlog_config.fastapi_access_logger](fastapi_access_logger/index.md)
* [structlog_config.formatters](formatters/index.md)
* [structlog_config.hook](hook/index.md)
* [structlog_config.levels](levels/index.md)
* [structlog_config.pytest_plugin](pytest_plugin/index.md)
* [structlog_config.stdlib_logging](stdlib_logging/index.md)
* [structlog_config.tee](tee/index.md)
* [structlog_config.trace](trace/index.md)
* [structlog_config.version](version/index.md)
* [structlog_config.warnings](warnings/index.md)

## Classes

| [`LoggerWithContext`](#structlog_config.LoggerWithContext)   | A customized bound logger class that adds easy-to-remember methods for adding context.   |
|----------------------------------------------------------------------|------------------------------------------------------------------------------------------|

## Functions

| [`log_processors_for_mode`](#structlog_config.log_processors_for_mode)(→ list[structlog.types.Processor])   | Determine what the "final" processes in the pipeline should be to render the log to the output device.   |
|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| [`get_default_processors`](#structlog_config.get_default_processors)(→ list[structlog.types.Processor])    | Return the default list of log processors for structlog configuration.                                   |
| [`add_simple_context_aliases`](#structlog_config.add_simple_context_aliases)(→ LoggerWithContext)              |                                                                                                          |
| [`get_logger`](#structlog_config.get_logger)(→ LoggerWithContext)                              | Get a structlog logger with the same context alias methods as the logger returned by configure_logger.   |
| [`configure_logger`](#structlog_config.configure_logger)(→ LoggerWithContext)                        | Create a structlog logger with some special additions:                                                   |

## Package Contents

### structlog_config.log_processors_for_mode(json_logger: [bool](https://docs.python.org/3/builtins/functions.html#bool)) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[structlog.types.Processor]

Determine what the “final” processes in the pipeline should be to render the log to the output device.

- If JSON, then structure exceptions as dicts and render as JSON
- If not JSON, then use the ConsoleRenderer with a nice exception formatter.

### structlog_config.get_default_processors(json_logger: [bool](https://docs.python.org/3/builtins/functions.html#bool)) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[structlog.types.Processor]

Return the default list of log processors for structlog configuration.

This includes any “final” processors to render the log as json or not.

### *class* structlog_config.LoggerWithContext

Bases: [`structlog.typing.FilteringBoundLogger`](https://www.structlog.org/en/stable/api.html#structlog.typing.FilteringBoundLogger), `Protocol`

A customized bound logger class that adds easy-to-remember methods for adding context.

We don’t use a real subclass because make_filtering_bound_logger has some logic we don’t
want to replicate.

#### context(\*args, \*\*kwargs) → contextlib._GeneratorContextManager[[None](https://docs.python.org/3/builtins/constants.html#None), [None](https://docs.python.org/3/builtins/constants.html#None), [None](https://docs.python.org/3/builtins/constants.html#None)]

context manager to temporarily set and clear logging context

#### local(\*args, \*\*kwargs) → [None](https://docs.python.org/3/builtins/constants.html#None)

set thread-local context

#### clear() → [None](https://docs.python.org/3/builtins/constants.html#None)

clear thread-local context

#### trace(\*args, \*\*kwargs) → [None](https://docs.python.org/3/builtins/constants.html#None)

trace level logging

### structlog_config.add_simple_context_aliases(log) → [LoggerWithContext](#structlog_config.LoggerWithContext)

### structlog_config.get_logger(\*args, \*\*kwargs) → [LoggerWithContext](#structlog_config.LoggerWithContext)

Get a structlog logger with the same context alias methods as the logger returned by configure_logger.

This is useful in cases where you want to get a logger without configuring it (e.g. in libraries or in tests).

### structlog_config.configure_logger(, json_logger: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, logger_factory=None, install_exception_hook: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, finalize_configuration: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, enable_tee: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [LoggerWithContext](#structlog_config.LoggerWithContext)

Create a structlog logger with some special additions:

```pycon
>>> with log.context(key=value):
>>>    log.info("some message")
```

```pycon
>>> log.local(key=value)
>>> log.info("some message")
>>> log.clear()
```

* **Parameters:**
  * **json_logger** – Flag to use JSON logging. Defaults to False.
  * **logger_factory** – Optional logger factory to override the default.
  * **install_exception_hook** – Optional flag to install a global exception hook
    that logs uncaught exceptions using structlog. Defaults to False.
  * **finalize_configuration** – If True, any subsequent calls to configure_logger will
    be ignored with a warning. Useful to setup logging and globally and prevent accidental
    reconfiguration by other developers.
  * **enable_tee** – Flag to enable context-scoped log teeing support (tee_logs).
    Defaults to False.
