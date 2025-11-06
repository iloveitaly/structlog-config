# Production-Ready Structured Logging for Python

Getting Python logging right is harder than it should be. You need to wrangle structlog configuration, stdlib loggers, JSON output for production, context propagation through FastAPI or Celery, and a dozen other details. I finally got this working in my [project template](https://github.com/iloveitaly/python-starter-template) and pulled it out into a package.

This gives you production-grade structured logging with minimal setup. Here are the main goals: structured logs everywhere, with smart defaults that work in development and production without fiddling with configuration.

## Installation

```bash
uv add structlog-config
```

For FastAPI support:

```bash
uv add structlog-config[fastapi]
```

## Usage

```python
from structlog_config import configure_logger

log = configure_logger()
log.info("the log", key="value")
```

That's it. In development you get pretty console output. In production (`PYTHON_ENV=production` or `PYTHON_ENV=staging`), you automatically get JSON logs optimized for speed and parsing.

### Context Management

Add context to all logs within a scope:

```python
# Temporary context with a context manager
with log.context(user_id="123", session="abc"):
    log.info("user action")  # includes user_id and session

# Thread-local context that persists
log.local(request_id="xyz")
log.info("processing")  # includes request_id
log.clear()  # remove context
```

### Environment-Based Configuration

Control any logger by name using environment variables:

```bash
# Set level and output path for specific loggers
LOG_LEVEL_HTTPX=DEBUG
LOG_PATH_HTTPX=tmp/httpx.log

# Works for any logger name
LOG_LEVEL_OPENAI=DEBUG
LOG_PATH_OPENAI=tmp/openai.log
```

This is perfect for debugging third-party libraries without touching your code.

## Features

**Core functionality:**
- High-performance JSON logging in production using [orjson](https://github.com/ijl/orjson)
- All stdlib loggers route through structlog for consistent formatting
- Thread-local and scoped context management
- Per-logger level and output path configuration via ENV variables

**Development experience:**
- Pretty console output with colored logs (respects `NO_COLOR`)
- Enhanced traceback formatting with [pretty-traceback](https://github.com/willmcgugan/pretty-traceback)
- Path prettification (shows relative paths from project root)
- TRACE log level for ultra-verbose debugging

**Production features:**
- Automatic JSON output in staging and production environments
- Sorted keys and ISO timestamps
- Structured exception logging (no ugly stack dumps in JSON)
- Stdout-only output (ignores `PYTHON_LOG_PATH` for container compatibility)

**Framework integration:**
- FastAPI access logger with request timing (requires `[fastapi]` extra)
- Automatic integration with [starlette-context](https://github.com/tomwojcik/starlette-context)
- pytest plugin for capturing logs only on test failures

**Special formatters:**
- ActiveModel/SQLModel object serialization (converts ORM objects to IDs)
- TypeID support
- Warning redirection to logging system
- Named logger support via `structlog.get_logger(logger_name="name")`

## TRACE Logging Level

Sometimes DEBUG isn't verbose enough. This package adds a TRACE level (level 5) for extremely detailed debugging:

```python
import logging
from structlog_config import configure_logger

log = configure_logger()

log.trace("ultra verbose message")
logging.trace("works with stdlib too")
```

Set it via environment:

```bash
LOG_LEVEL=TRACE
```

## JSON Logging

JSON logging turns on automatically in production and staging:

```python
from structlog_config import configure_logger

log = configure_logger()
log.info("User login", user_id="123", action="login")
# Output: {"action":"login","event":"User login","level":"info","timestamp":"2025-09-24T18:03:00Z","user_id":"123"}
```

Force JSON mode regardless of environment:

```python
log = configure_logger(json_logger=True)
```

Or force console output in production:

```python
log = configure_logger(json_logger=False)
```

## FastAPI Access Logger

The built-in FastAPI access logger is verbose and uses string interpolation. This package provides a cleaner alternative with structured logging and request timing.

**Setup:**
1. [Disable FastAPI's default logging](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/main.py#L55-L56)
2. [Add the middleware](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/app/routes/middleware/__init__.py#L63-L65)

The middleware logs at debug level for static assets and info level for other requests.

## Pytest Plugin

Capture logs per-test and display them only on failure. This keeps test output clean while preserving debugging info when you need it.

**Enable globally:**

```toml
[tool.pytest.ini_options]
addopts = ["--capture-logs-on-fail"]
```

**Or per-run:**

```bash
pytest --capture-logs-on-fail
```

**Persist logs to directory:**

```bash
pytest --capture-logs-dir=./test-logs
```

When a test fails, you see captured logs:

```
FAILED tests/test_user.py::test_user_login

--- Captured logs for failed test (call): tests/test_user.py::test_user_login ---
2025-11-01 18:30:00 [info] User login started user_id=123
2025-11-01 18:30:01 [error] Database connection failed timeout=5.0
```

Passing tests show no logs, keeping output clean.

## iPython

Update logging level in an iPython session and have all loggers pick it up:

```python
%env LOG_LEVEL=DEBUG
from structlog_config import configure_logger
configure_logger()
```

## Related Projects

- [structlog-pretty](https://github.com/underyx/structlog-pretty)
- [httpx-structlog](https://pypi.org/project/httpx-structlog/)

## References

General logging:
- https://github.com/replicate/cog/blob/main/python/cog/logging.py
- https://github.com/apache/airflow/blob/main/task_sdk/src/airflow/sdk/log.py
- https://github.com/kiwicom/structlog-sentry
- https://github.com/openai/openai-python/blob/main/src/openai/_utils/_logs.py
- https://www.python-httpx.org/logging/

FastAPI access logger:
- https://github.com/iloveitaly/fastapi-logger
- https://github.com/fastapiutils/fastapi-utils/blob/master/fastapi_utils/timing.py
- https://pypi.org/project/fastapi-structlog/
- https://pypi.org/project/asgi-correlation-id/

# [MIT License](LICENSE.md)
