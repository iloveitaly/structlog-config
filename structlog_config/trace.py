"""
Adapted from:
https://github.com/willmcgugan/httpx/blob/973d1ed4e06577d928061092affe8f94def03331/httpx/_utils.py#L231
"""

import logging
import typing

TRACE_LOG_LEVEL = 5


logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")


class Logger(logging.Logger):
    # Stub for type checkers.
    def trace(
        self, message: str, *args: typing.Any, **kwargs: typing.Any
    ) -> None: ...  # pragma: nocover


def trace(self, message: str, *args: typing.Any, **kwargs: typing.Any) -> None:
    if self.isEnabledFor(TRACE_LOG_LEVEL):
        self._log(TRACE_LOG_LEVEL, message, args, **kwargs)


logging.Logger.trace = trace

# Add module-level trace function
logging.trace = lambda message, *args, **kwargs: logging.getLogger().trace(
    message, *args, **kwargs
)
