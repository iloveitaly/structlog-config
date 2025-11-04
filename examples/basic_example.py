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
    os.environ.setdefault("PYTHON_ENV", "production" if json_mode else "development")
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
