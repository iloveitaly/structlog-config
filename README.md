# Opinionated Defaults for Structlog

Logging is really important. Getting logging to work well in python feels like black magic: there's a ton of configuration
across structlog, warnings, std loggers, fastapi + celery context, JSON logging in production, etc that requires lots of
fiddling and testing to get working. I finally got this working for me in my [project template](https://github.com/iloveitaly/python-starter-template) and extracted this out into a nice package.

Here are the main goals:

* High performance JSON logging in production
* All loggers, even plugin or system loggers, should route through the same formatter
* Structured logging everywhere
* Ability to easily set thread-local log context
* Nice log formatters for stack traces, ORM ([ActiveModel/SQLModel](https://github.com/iloveitaly/activemodel)), etc
* Ability to log level and output (i.e. file path) *by logger* for easy development debugging
* If you are using fastapi, structured logging for access logs

## Usage

```python
from structlog_config import configure_logger

log = configure_logger()

log.info("the log", key="value")
```

## Exception Logging

Automatically log uncaught exceptions using structured logging. This is especially useful in production environments where you want all exceptions logged as JSON for monitoring and alerting.

```python
from structlog_config import configure_logger

# Enable exception logging (defaults to enabled in production/JSON mode)
log = configure_logger(setup_exception_logging=True)

# Now any uncaught exception will be logged
raise ValueError("This will be logged as JSON in production!")
```

**Key features:**

- **Automatic detection**: Defaults to enabled when `json_logger=True` (production mode)
- **JSON formatting**: Uncaught exceptions are logged as structured JSON in production
- **Rich formatting**: Pretty exception traces in development mode
- **Smart handling**: KeyboardInterrupt is not logged as an exception
- **Chain-friendly**: Works with existing exception hooks (like Ubuntu's apport)

**Example output in production:**
```json
{"event": "Uncaught exception", "exception": "Traceback (most recent call last):\n  File \"app.py\", line 10, in main\n    raise ValueError(\"Something went wrong\")\nValueError: Something went wrong", "level": "error", "timestamp": "2024-01-15T10:30:45.123456Z"}
```

The best pattern for customizing exception logging in production is to use the built-in `setup_exception_logging` parameter, which handles all the complexity of setting up `sys.excepthook` correctly while maintaining compatibility with existing systems.

## TRACE Logging Level

This package adds support for a custom `TRACE` logging level (level 5) that's even more verbose than `DEBUG`. This is useful for extremely detailed debugging scenarios.

The `TRACE` level is automatically set up when you call `configure_logger()`. You can use it like any other logging level:

```python
import logging
from structlog_config import configure_logger

log = configure_logger()

# Using structlog
log.info("This is info")
log.debug("This is debug") 
log.trace("This is trace")  # Most verbose

# Using stdlib logging
logging.trace("Module-level trace message")
logger = logging.getLogger(__name__)
logger.trace("Instance trace message")
```

Set the log level to TRACE using the environment variable:

```bash
LOG_LEVEL=TRACE
```

## Stdlib Log Management

By default, all stdlib loggers are:

1. Given the same global logging level, with some default adjustments for noisy loggers (looking at you, `httpx`)
2. Use a structlog formatter (you get structured logging, context, etc in any stdlib logger calls)
3. The root processor is overwritten so any child loggers created after initialization will use the same formatter

You can customize loggers by name (i.e. the name used in `logging.getLogger(__name__)`) using ENV variables.

For example, if you wanted to [mimic `OPENAI_LOG` functionality](https://github.com/openai/openai-python/blob/de7c0e2d9375d042a42e3db6c17e5af9a5701a99/src/openai/_utils/_logs.py#L16):

* `LOG_LEVEL_OPENAI=DEBUG`
* `LOG_PATH_OPENAI=tmp/openai.log`
* `LOG_LEVEL_HTTPX=DEBUG`
* `LOG_PATH_HTTPX=tmp/openai.log`

## FastAPI Access Logger

Structured, simple access log with request timing to replace the default fastapi access log. Why?

1. It's less verbose
2. Uses structured logging params instead of string interpolation
3. debug level logs any static assets

Here's how to use it:

1. [Disable fastapi's default logging.](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/main.py#L55-L56)
2. [Add the middleware to your FastAPI app.](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/app/routes/middleware/__init__.py#L63-L65)

## iPython

Often it's helpful to update logging level within an iPython session. You can do this and make sure all loggers pick up on it.

```
%env LOG_LEVEL=DEBUG
from structlog_config import configure_logger
configure_logger()
```

## Related Projects

* https://github.com/underyx/structlog-pretty
* https://pypi.org/project/httpx-structlog/

## References

General logging:

- https://github.com/replicate/cog/blob/2e57549e18e044982bd100e286a1929f50880383/python/cog/logging.py#L20
- https://github.com/apache/airflow/blob/4280b83977cd5a53c2b24143f3c9a6a63e298acc/task_sdk/src/airflow/sdk/log.py#L187
- https://github.com/kiwicom/structlog-sentry
- https://github.com/jeremyh/datacube-explorer/blob/b289b0cde0973a38a9d50233fe0fff00e8eb2c8e/cubedash/logs.py#L40C21-L40C42
- https://stackoverflow.com/questions/76256249/logging-in-the-open-ai-python-library/78214464#78214464
- https://github.com/openai/openai-python/blob/de7c0e2d9375d042a42e3db6c17e5af9a5701a99/src/openai/_utils/_logs.py#L16
- https://www.python-httpx.org/logging/

FastAPI access logger:

- https://github.com/iloveitaly/fastapi-logger/blob/main/fastapi_structlog/middleware/access_log.py#L70
- https://github.com/fastapiutils/fastapi-utils/blob/master/fastapi_utils/timing.py
- https://pypi.org/project/fastapi-structlog/
- https://pypi.org/project/asgi-correlation-id/
- https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
- https://github.com/sharu1204/fastapi-structlog/blob/master/app/main.py
