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

import os

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
