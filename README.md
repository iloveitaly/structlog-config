# Structlog Configuration

Logging is really important:

* High performance JSON logging in production
* All loggers, even plugin or system loggers, should route through the same formatter
* Structured logging everywhere
* Ability to easily set thread-local log context

## Stdib Log Management

Note that `{LOGGER_NAME}` is the name of the system logger assigned via `logging.getLogger(__name__)`:

* `OPENAI_LOG_LEVEL`
* `OPENAI_LOG_PATH`. Ignored in production.

## FastAPI Access Logger

Structured, simple access log with request timing to replace the default fastapi access log. Why?

1. It's less verbose
2. Uses structured logging params instead of string interpolation
3. debug level logs any static assets

Here's how to use it:

1. [Disable fastapi's default logging.](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/main.py#L55-L56)
2. [Add the middleware to your FastAPI app.](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/app/routes/middleware/__init__.py#L63-L65)

Adapted from:

- https://github.com/iloveitaly/fastapi-logger/blob/main/fastapi_structlog/middleware/access_log.py#L70
- https://github.com/fastapiutils/fastapi-utils/blob/master/fastapi_utils/timing.py
- https://pypi.org/project/fastapi-structlog/
- https://pypi.org/project/asgi-correlation-id/
- https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
- https://github.com/sharu1204/fastapi-structlog/blob/master/app/main.py

## Related Projects

* https://github.com/underyx/structlog-pretty
* https://pypi.org/project/httpx-structlog/

## References

- https://github.com/replicate/cog/blob/2e57549e18e044982bd100e286a1929f50880383/python/cog/logging.py#L20
- https://github.com/apache/airflow/blob/4280b83977cd5a53c2b24143f3c9a6a63e298acc/task_sdk/src/airflow/sdk/log.py#L187
- https://github.com/kiwicom/structlog-sentry
- https://github.com/jeremyh/datacube-explorer/blob/b289b0cde0973a38a9d50233fe0fff00e8eb2c8e/cubedash/logs.py#L40C21-L40C42
