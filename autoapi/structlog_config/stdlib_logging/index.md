# structlog_config.stdlib_logging

Redirect all stdlib loggers to use the structlog configuration.

## Functions

| [`reset_stdlib_logger`](#structlog_config.stdlib_logging.reset_stdlib_logger)(logger_name, ...)                       |                                                                                  |
|--------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`clear_existing_logger_handlers`](#structlog_config.stdlib_logging.clear_existing_logger_handlers)()                            | Clear handlers from all existing loggers so they propagate to the root logger.   |
| [`redirect_stdlib_loggers`](#structlog_config.stdlib_logging.redirect_stdlib_loggers)(json_logger[, logger_factory, ...]) | Redirect all standard logging module loggers to use the structlog configuration. |

## Module Contents

### structlog_config.stdlib_logging.reset_stdlib_logger(logger_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str), default_structlog_handler: [logging.Handler](https://docs.python.org/3/library/logging.html#logging.Handler), level_override: [str](https://docs.python.org/3/builtins/stdtypes.html#str))

### structlog_config.stdlib_logging.clear_existing_logger_handlers()

Clear handlers from all existing loggers so they propagate to the root logger.

This handles libraries like uvicorn/alembic/gunicorn that could install their own
handlers before configure_logger() is called.

### structlog_config.stdlib_logging.redirect_stdlib_loggers(json_logger: [bool](https://docs.python.org/3/builtins/functions.html#bool), logger_factory: Any = None, , enable_tee: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False)

Redirect all standard logging module loggers to use the structlog configuration.

- json_loggers determines if logs are rendered as JSON or not
- The stdlib log stream is used to write logs to the output device (normally, stdout)

Inspired by: [https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e](https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e)
