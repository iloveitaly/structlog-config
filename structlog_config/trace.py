"""
Adapted from:
https://github.com/willmcgugan/httpx/blob/973d1ed4e06577d928061092affe8f94def03331/httpx/_utils.py#L231

TODO this is not fully integrated into the codebase
"""

import logging
import typing

from structlog_config.constants import TRACE_LOG_LEVEL

logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")


class Logger(logging.Logger):
    # Stub for type checkers.
    def trace(
        self, message: str, *args: typing.Any, **kwargs: typing.Any
    ) -> None: ...  # pragma: nocover


def trace(self, message: str, *args: typing.Any, **kwargs: typing.Any) -> None:
    if self.isEnabledFor(TRACE_LOG_LEVEL):
        self._log(TRACE_LOG_LEVEL, message, args, **kwargs)


# Check if trace method already exists on Logger class
if hasattr(logging.Logger, "trace"):
    logging.warning("Logger.trace method already exists, overriding it")
else:
    logging.Logger.trace = trace  # type: ignore

# Check if trace function already exists in logging module
if hasattr(logging, "trace"):
    logging.warning("logging.trace function already exists, overriding it")
else:
    # Add module-level trace function
    logging.trace = lambda message, *args, **kwargs: logging.getLogger().trace(  # type: ignore
        message, *args, **kwargs
    )
