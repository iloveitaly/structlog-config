"""
Adapted from:
- https://github.com/willmcgugan/httpx/blob/973d1ed4e06577d928061092affe8f94def03331/httpx/_utils.py#L231
- https://github.com/vladmandic/sdnext/blob/d5d857aa961edbc46c9e77e7698f2e60011e7439/installer.py#L154

TODO this is not fully integrated into the codebase
"""

import logging
import typing
from functools import partial, partialmethod

from structlog_config.constants import TRACE_LOG_LEVEL

# Track if setup has already been called
_setup_called = False


# Stub for type checkers.
class Logger(logging.Logger):
    def trace(
        self, message: str, *args: typing.Any, **kwargs: typing.Any
    ) -> None: ...  # pragma: nocover


# def trace(self, message: str, *args: typing.Any, **kwargs: typing.Any) -> None:
#     if self.isEnabledFor(TRACE_LOG_LEVEL):
#         self._log(TRACE_LOG_LEVEL, message, args, **kwargs)


def setup_trace() -> None:
    """Setup TRACE logging level. Safe to call multiple times."""
    global _setup_called

    if _setup_called:
        return

    logging.TRACE = TRACE_LOG_LEVEL
    logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")

    if hasattr(logging.Logger, "trace"):
        logging.warning("Logger.trace method already exists, not overriding it")
    else:
        logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)

    # Check if trace function already exists in logging module
    if hasattr(logging, "trace"):
        logging.warning("logging.trace function already exists, overriding it")
    else:
        logging.trace = partial(logging.log, logging.TRACE)

    _setup_called = True
