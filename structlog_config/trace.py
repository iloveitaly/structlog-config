"""
Adapted from:
https://github.com/willmcgugan/httpx/blob/973d1ed4e06577d928061092affe8f94def03331/httpx/_utils.py#L231
"""

import logging
import typing

TRACE_LOG_LEVEL = 5


class Logger(logging.Logger):
    # Stub for type checkers.
    def trace(
        self, message: str, *args: typing.Any, **kwargs: typing.Any
    ) -> None: ...  # pragma: nocover


logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")


def trace(message: str, *args: typing.Any, **kwargs: typing.Any) -> None:
    logger.log(TRACE_LOG_LEVEL, message, *args, **kwargs)


logging.Logger.trace = trace
