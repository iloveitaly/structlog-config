# Examples

Canonical runnable examples live under [`examples/`](https://github.com/iloveitaly/structlog-config/tree/master/examples) and are included here with `literalinclude` so the docs stay in sync with the scripts.

`just examples` runs the basic example, which exits on its own. The FastAPI scripts start a server, so they are documented here and left out of that recipe.

## Basic logging

Console output, a `TRACE` event, thread-local context, a stdlib logger, and a caught exception:

```python
#!/usr/bin/env -S uv run --script
"""Minimal demonstration of structlog-config capabilities."""

# /// script
# dependencies = [
#   "structlog-config",
# ]
# ///

import argparse
import logging
import os

from structlog_config import configure_logger
from structlog_config.constants import TRACE_LOG_LEVEL


def run_demo(*, json_mode: bool = False) -> None:
    os.environ.setdefault("LOG_LEVEL", "TRACE")

    log = configure_logger(json_logger=json_mode)

    log.info("example boot", feature="basic-example", json_mode=json_mode)
    logging.log(TRACE_LOG_LEVEL, "trace event", extra={"detail": "first-trace"})

    with log.context(session_id="sess-123", user="alice"):
        log.info("structured message", scope="context-manager")

    logging.getLogger("demo.stdlib").info("stdlib message", extra={"context": "stdlib"})

    try:
        raise RuntimeError("example failure")
    except RuntimeError as exc:
        log.error("structlog exception", exc_info=exc, step="structlog")
        logging.getLogger("demo.stdlib").error("stdlib exception", exc_info=True)

    log.info("example complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the structlog basic example")
    parser.add_argument("--json", action="store_true", help="emit logs in JSON format")
    args = parser.parse_args()

    run_demo(json_mode=args.json)


if __name__ == "__main__":
    main()
```

Run it locally:

```bash
just examples
# or: uv run python examples/basic_example.py
# JSON: uv run python examples/basic_example.py --json
```

## FastAPI exception logging

JSON logging around an intentional unhandled exception. This process stays up and serves `http://localhost:8000/`.

```python
#!/usr/bin/env -S uv run --script
"""
FastAPI example server demonstrating structured logging with exceptions.

This script starts a production-ready FastAPI server with JSON logging enabled.
The root endpoint intentionally raises an exception to demonstrate error logging.
"""

# /// script
# dependencies = [
#   "fastapi",
#   "uvicorn",
#   "structlog-config",
#   "rich",
# ]
# ///

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from structlog_config import configure_logger

configure_logger(json_logger=True)
log = structlog.get_logger()

app = FastAPI()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(
        "unhandled exception",
        path=request.url.path,
        method=request.method,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def root():
    log.info("handling root request")
    raise ValueError("This is an intentional error to demonstrate exception logging!")


@app.get("/health")
def health():
    log.info("health check")
    return {"status": "ok"}


def print_banner():
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(
        Panel.fit(
            "Testing FastAPI structured logging\n\n"
            "Endpoints:\n"
            "• http://localhost:8000/ - throws exception (error logging)\n"
            "• http://localhost:8000/health - healthy response (info logging)",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    import uvicorn

    print_banner()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
    )
```

```bash
uv run --script examples/fastapi_server.py
```

## FastAPI dependency exceptions

The same server shape, with the exception raised from a dependency instead of the route.

```python
#!/usr/bin/env -S uv run --script
"""
FastAPI example demonstrating structured logging with exceptions in dependencies.

This script shows how exceptions raised in FastAPI dependencies are logged.
The dependency injection system is commonly used for auth, database connections, etc.
"""

# /// script
# dependencies = [
#   "fastapi",
#   "uvicorn",
#   "structlog-config",
#   "rich",
# ]
# ///

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from structlog_config import configure_logger

log = configure_logger(json_logger=True)
app = FastAPI()


def get_current_user():
    """Dependency that simulates user authentication but always fails."""
    log.info("attempting to authenticate user")
    raise RuntimeError("Authentication service unavailable!")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(
        "unhandled exception",
        path=request.url.path,
        method=request.method,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def root(user=Depends(get_current_user)):
    """Route that depends on authentication - exception thrown in dependency."""
    log.info("serving protected content")
    return {"message": "This should never be reached"}


@app.get("/health")
def health():
    log.info("health check")
    return {"status": "ok"}


def print_banner():
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(
        Panel.fit(
            "Testing dependency exceptions in FastAPI\n\n"
            "Endpoint: http://localhost:8000/\n"
            "Expected: Authentication exception with JSON logs",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    import uvicorn

    print_banner()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
    )
```

```bash
uv run --script examples/fastapi_dependency_error.py
```
