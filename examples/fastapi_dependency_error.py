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

import os

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from structlog_config import configure_logger

# force PYTHON_ENV=production for json logging
os.environ["PYTHON_ENV"] = "production"

log = configure_logger()
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
