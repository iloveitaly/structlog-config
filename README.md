# Opinionated Defaults for Structlog

Logging is really important. Getting logging to work well in python feels like black magic: there's a ton of configuration
across structlog, warnings, std loggers, fastapi + celery context, JSON logging in production, etc that requires lots of
fiddling and testing to get working. I finally got this working for me in my [project template](https://github.com/iloveitaly/python-starter-template) and extracted this out into a nice package.

Here are the main goals:

* High performance JSON logging in production
* All loggers, even plugin or system loggers, should route through the same formatter
* Structured logging everywhere
* Pytest plugin to easily capture logs and dump to a directory on failure. This is really important for LLMs so they can
  easily consume logs and context for each test and handle them sequentially.
* Ability to easily set thread-local log context
* Nice log formatters for stack traces, ORM ([ActiveModel/SQLModel](https://github.com/iloveitaly/activemodel)), etc
* Ability to log level and output (i.e. file path) *by logger* for easy development debugging
* If you are using fastapi, structured logging for access logs
* [Improved exception logging with beautiful-traceback](https://github.com/iloveitaly/beautiful-traceback)

## Installation

```bash
uv add structlog-config
```

## Usage

```python
from structlog_config import configure_logger

log = configure_logger()

log.info("the log", key="value")

# named logger just like stdlib, but with a different syntax
custom_named_logger = structlog.get_logger(logger_name="test")
```

## JSON Logging in Production

JSON logging is automatically enabled in production and staging environments (`PYTHON_ENV=production` or `PYTHON_ENV=staging`):

```python
from structlog_config import configure_logger

# Automatic JSON logging in production
log = configure_logger()
log.info("User login", user_id="123", action="login")
# Output: {"action":"login","event":"User login","level":"info","timestamp":"2025-09-24T18:03:00Z","user_id":"123"}

# Force JSON logging regardless of environment
log = configure_logger(json_logger=True)

# Force console logging regardless of environment
log = configure_logger(json_logger=False)
```

JSON logs use [orjson](https://github.com/ijl/orjson) for performance, include sorted keys and ISO timestamps, and serialize exceptions cleanly.

Note that `PYTHON_LOG_PATH` is ignored with JSON logging (stdout only).

## TRACE Logging Level

This package adds support for a custom `TRACE` logging level (level 5) that's even more verbose than `DEBUG`.

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

## Custom Formatters

This package includes several custom formatters that automatically clean up log output:

### Path Prettifier

Automatically formats `pathlib.Path` and `PosixPath` objects to show relative paths when possible, removing the wrapper class names:

```python
from pathlib import Path
log.info("Processing file", file_path=Path.cwd() / "data" / "users.csv")
# Output: file_path=data/users.csv (instead of PosixPath('/home/user/data/users.csv'))
```

### Whenever Datetime Formatter

Formats [whenever](https://github.com/ariebovenberg/whenever) datetime objects without their class wrappers for cleaner output:

```python
from whenever import ZonedDateTime

log.info("Event scheduled", event_time=ZonedDateTime(2025, 11, 2, 0, 0, 0, tz="UTC"))
# Output: event_time=2025-11-02T00:00:00+00:00[UTC]
# Instead of: event_time=ZonedDateTime("2025-11-02T00:00:00+00:00[UTC]")
```

Supports all whenever datetime types: `ZonedDateTime`, `Instant`, `LocalDateTime`, `PlainDateTime`, etc.

### ActiveModel Object Formatter

Automatically converts [ActiveModel](https://github.com/iloveitaly/activemodel) BaseModel instances to their ID representation and TypeID objects to strings:

```python
from activemodel import BaseModel

user = User(id="user_123", name="Alice")
log.info("User action", user=user)
# Output: user_id=user_123 (instead of full object representation)
```

### FastAPI Context

Automatically includes all context data from [starlette-context](https://github.com/tomwojcik/starlette-context) in your logs, useful for request tracing:

```python
# Context data (request_id, correlation_id, etc.) automatically included in all logs
log.info("Processing request")
# Output includes: request_id=abc-123 correlation_id=xyz-789 ...
```

All formatters are optional and automatically enabled when their respective dependencies are installed. They work seamlessly in both development (console) and production (JSON) logging modes.

## FastAPI Access Logger

**Note:** Requires `pip install structlog-config[fastapi]` for FastAPI dependencies.

Structured, simple access log with request timing to replace the default fastapi access log. Why?

1. It's less verbose
2. Uses structured logging params instead of string interpolation
3. debug level logs any static assets

Here's how to use it:

1. [Disable fastapi's default logging.](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/main.py#L55-L56)
2. [Add the middleware to your FastAPI app.](https://github.com/iloveitaly/python-starter-template/blob/f54cb47d8d104987f2e4a668f9045a62e0d6818a/app/routes/middleware/__init__.py#L63-L65)

## Pytest Plugin: Capture Output on Failure

A pytest plugin that captures stdout, stderr, and exceptions from failing tests and writes them to organized output files. This is useful for debugging test failures, especially in CI/CD environments where you need to inspect output after the fact.

### Features

- Captures stdout, stderr, and exception tracebacks for failing tests
- Only creates output for failing tests (keeps directories clean)
- Separate files for each output type (stdout.txt, stderr.txt, exception.txt)
- Captures all test phases (setup, call, teardown)
- Optional fd-level capture for subprocess output

### Usage

Enable the plugin with the `--structlog-output` flag and `-s` (to disable pytest's built-in capture):

```bash
pytest --structlog-output=./test-output -s
```

The `--structlog-output` flag both enables the plugin and specifies where output files should be written.

**Recommended:** Also disable pytest's logging plugin with `-p no:logging` to avoid duplicate/interfering capture:

```bash
pytest --structlog-output=./test-output -s -p no:logging
```

While the plugin works without this flag, disabling pytest's logging capture ensures cleaner output and avoids any potential conflicts between the two capture mechanisms.

### Output Structure

Each failing test gets its own directory with separate files:

```
test-output/
    test_module__test_name/
        stdout.txt      # stdout from test (includes setup, call, and teardown phases)
        stderr.txt      # stderr from test (includes setup, call, and teardown phases)
        exception.txt   # exception traceback
```

### Advanced: fd-level Capture

For tests that spawn subprocesses or write directly to file descriptors, you can enable fd-level capture. This is useful for integration tests that run external processes (such a server which replicates a production environment).

#### Add fixture to function signature

Great for a single single test:

```python
def test_with_subprocess(file_descriptor_output_capture):
    # subprocess.run() output will be captured
    subprocess.run(["echo", "hello from subprocess"])

    # multiprocessing.Process output will be captured
    from multiprocessing import Process
    proc = Process(target=lambda: print("hello from process"))
    proc.start()
    proc.join()

    assert False  # Trigger failure to write output files
```

Alternatively, you can use `@pytest.mark.usefixtures("file_descriptor_output_capture")`


#### All tests in directory

Add to `conftest.py`:

```python
import pytest

pytestmark = pytest.mark.usefixtures("file_descriptor_output_capture")
```

### Example

When a test fails:

```python
def test_user_login():
    print("Starting login process")
    print("ERROR: Connection failed", file=sys.stderr)
    assert False, "Login failed"
```

You'll get:

```
test-output/test_user__test_user_login/
    stdout.txt: "Starting login process"
    stderr.txt: "ERROR: Connection failed"
    exception.txt: Full traceback with "AssertionError: Login failed"
```

## Beautiful Traceback Support

Optional support for [beautiful-traceback](https://github.com/iloveitaly/beautiful-traceback) provides enhanced exception formatting with improved readability, smart coloring, path aliasing (e.g., `<pwd>`, `<site>`), and better alignment. Automatically activates when installed:

```bash
uv add beautiful-traceback --group dev
```

No configuration needed - just install and `configure_logger()` will use it automatically.

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
