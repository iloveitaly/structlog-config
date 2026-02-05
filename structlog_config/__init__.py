from contextlib import _GeneratorContextManager
from typing import Protocol

import orjson
import structlog
import structlog.dev
from decouple import config
from structlog.processors import ExceptionRenderer
from structlog.tracebacks import ExceptionDictTransformer
from structlog.typing import FilteringBoundLogger

from structlog_config.formatters import (
    PathPrettifier,
    WheneverFormatter,
    add_fastapi_context,
    beautiful_traceback_exception_formatter,
    logger_name,
    simplify_activemodel_objects,
)

from . import (
    hook,
    packages,
    trace,  # noqa: F401 (import has side effects for trace level setup)
)
from .constants import NO_COLOR, package_logger
from .environments import is_pytest
from .levels import get_environment_log_level_as_string
from .stdlib_logging import (
    redirect_stdlib_loggers,
)
from .trace import setup_trace
from .warnings import redirect_showwarnings


def log_processors_for_mode(json_logger: bool) -> list[structlog.types.Processor]:
    if json_logger:

        def orjson_dumps_sorted(value, *args, **kwargs):
            "sort_keys=True is not supported, so we do it manually"

            # kwargs includes a default fallback json formatter
            return orjson.dumps(
                value,
                # starlette-context includes non-string keys (enums), which is why we need to set the options in this way
                # TODO do we need to sort the keys here? this will cost us in CPU time :/
                option=orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS,
                **kwargs,
            )

        return [
            # omit `structlog.processors.format_exc_info` so we can use structured logging for exceptions
            # simple, short exception rendering in prod since sentry is in place
            # https://www.structlog.org/en/stable/exceptions.html this is a customized version of dict_tracebacks
            ExceptionRenderer(
                ExceptionDictTransformer(
                    show_locals=False,
                    use_rich=False,
                    # number of frames is completely arbitrary
                    max_frames=5,
                    # TODO `suppress`?
                )
            ),
            # in prod, we want logs to be rendered as JSON payloads
            structlog.processors.JSONRenderer(serializer=orjson_dumps_sorted),
        ]

    # Passing None skips the ConsoleRenderer default, so use the explicit dev default.
    exception_formatter = structlog.dev.default_exception_formatter

    # if we have beautiful traceback installed, use it
    if packages.beautiful_traceback:
        exception_formatter = beautiful_traceback_exception_formatter

    return [
        structlog.dev.ConsoleRenderer(
            colors=not NO_COLOR,
            exception_formatter=exception_formatter,
        )
    ]


def get_default_processors(json_logger) -> list[structlog.types.Processor]:
    """
    Return the default list of processors for structlog configuration.
    """
    processors = [
        # although this is stdlib, it's needed, although I'm not sure entirely why
        structlog.stdlib.add_log_level,
        structlog.contextvars.merge_contextvars,
        logger_name,
        add_fastapi_context if packages.starlette_context else None,
        simplify_activemodel_objects
        if packages.activemodel and packages.typeid
        else None,
        PathPrettifier(),
        WheneverFormatter() if packages.whenever else None,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # add `stack_info=True` to a log and get a `stack` attached to the log
        structlog.processors.StackInfoRenderer(),
        *log_processors_for_mode(json_logger),
    ]

    return [processor for processor in processors if processor is not None]


def _logger_factory(json_logger: bool):
    """
    Allow dev users to redirect logs to a file using PYTHON_LOG_PATH

    In production, optimized for speed (https://www.structlog.org/en/stable/performance.html)
    """

    # avoid a constant for this ENV so we can mutate within tests
    python_log_path = config("PYTHON_LOG_PATH", default=None)

    if json_logger:
        # TODO I guess we could support this, but the assumption is stdout is going to be used in prod environments
        if python_log_path:
            package_logger.warning(
                "PYTHON_LOG_PATH is not supported with a JSON logger, forcing stdout"
            )
        return structlog.BytesLoggerFactory()

    if python_log_path:
        python_log = open(python_log_path, "a", encoding="utf-8")
        return structlog.PrintLoggerFactory(file=python_log)

    # Default case
    return structlog.PrintLoggerFactory()


class LoggerWithContext(FilteringBoundLogger, Protocol):
    """
    A customized bound logger class that adds easy-to-remember methods for adding context.

    We don't use a real subclass because `make_filtering_bound_logger` has some logic we don't
    want to replicate.
    """

    def context(self, *args, **kwargs) -> _GeneratorContextManager[None, None, None]:
        "context manager to temporarily set and clear logging context"
        ...

    def local(self, *args, **kwargs) -> None:
        "set thread-local context"
        ...

    def clear(self) -> None:
        "clear thread-local context"
        ...

    def trace(self, *args, **kwargs) -> None:  # noqa: F811
        "trace level logging"
        ...


# TODO this may be a bad idea, but I really don't like how the `bound` stuff looks and how to access it, way too ugly
def add_simple_context_aliases(log) -> LoggerWithContext:
    log.context = structlog.contextvars.bound_contextvars
    log.local = structlog.contextvars.bind_contextvars
    log.clear = structlog.contextvars.clear_contextvars

    return log


def configure_logger(
    *,
    json_logger: bool = False,
    logger_factory=None,
    install_exception_hook: bool = False,
) -> LoggerWithContext:
    """
    Create a struct logger with some special additions:

    >>> with log.context(key=value):
    >>>    log.info("some message")

    >>> log.local(key=value)
    >>> log.info("some message")
    >>> log.clear()

    Args:
        json_logger: Flag to use JSON logging. Defaults to False.
        logger_factory: Optional logger factory to override the default
        install_exception_hook: Optional flag to install a global exception hook
            that logs uncaught exceptions using structlog. Defaults to False.
    """
    setup_trace()

    # Reset structlog configuration to make sure we're starting fresh
    # This is important for tests where configure_logger might be called multiple times
    structlog.reset_defaults()

    if install_exception_hook:
        hook.install_exception_hook(json_logger)

    redirect_stdlib_loggers(json_logger)
    redirect_showwarnings()

    structlog.configure(
        # Don't cache the loggers during tests, it makes it hard to capture them
        cache_logger_on_first_use=not is_pytest(),
        wrapper_class=structlog.make_filtering_bound_logger(
            get_environment_log_level_as_string()
        ),
        logger_factory=logger_factory or _logger_factory(json_logger),
        processors=get_default_processors(json_logger),
    )

    log = structlog.get_logger()
    log = add_simple_context_aliases(log)

    return log
