import sys
from contextlib import _GeneratorContextManager
from typing import Protocol

import orjson
import structlog
import structlog.dev
from decouple import config
from structlog.processors import ExceptionRenderer
from structlog.typing import FilteringBoundLogger

from structlog_config.formatters import (
    PathPrettifier,
    WheneverFormatter,
    add_fastapi_context,
    beautiful_traceback_exception_formatter,
    get_json_exception_formatter,
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

_CONFIGURATION_FINALIZED = False


def log_processors_for_mode(json_logger: bool) -> list[structlog.types.Processor]:
    """
    Determine what the "final" processes in the pipeline should be to render the log to the output device.

    - If JSON, then structure exceptions as dicts and render as JSON
    - If not JSON, then use the ConsoleRenderer with a nice exception formatter.
    """
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

        exception_formatter = get_json_exception_formatter()

        return [
            # ExceptionRenderer transforms the raw `exc_info` tuple into a formatted `exception` field.
            # We omit `structlog.processors.format_exc_info` here to use this structured renderer instead.
            # In production, we keep rendering simple/short since Sentry handles the heavy lifting.
            # https://www.structlog.org/en/stable/exceptions.html
            ExceptionRenderer(exception_formatter),
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


def get_default_processors(json_logger: bool) -> list[structlog.types.Processor]:
    """
    Return the default list of log processors for structlog configuration.

    This includes any "final" processors to render the log as json or not.
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


class _LazyStream:
    """Defers resolution of sys.stdout/stderr to write time.

    This is critical when tests redirect sys.stdout per-phase (pytest's capture resets
    sys.stdout between fixture-setup and test-call phases), so we must not capture
    the stream at configure time.
    """

    def __init__(self, name: str):
        self.name = name

    def write(self, data):
        getattr(sys, self.name).write(data)

    def flush(self):
        getattr(sys, self.name).flush()

    def isatty(self):
        return getattr(sys, self.name).isatty()


class _LazyBuffer:
    """Binary version of _LazyStream for BytesLoggerFactory."""

    def __init__(self, name: str):
        self.name = name

    def write(self, data):
        getattr(sys, self.name).buffer.write(data)

    def flush(self):
        getattr(sys, self.name).buffer.flush()


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

        # JSON mode requires binary stream for high-performance orjson serialization
        return structlog.BytesLoggerFactory(file=_LazyBuffer("stdout"))

    if python_log_path:
        # Redirect all logs to a specific file path if configured via environment
        python_log = open(python_log_path, "a", encoding="utf-8")
        return structlog.PrintLoggerFactory(file=python_log)

    # Explicitly pass stdout so the destination is introspectable during coordination
    return structlog.PrintLoggerFactory(file=_LazyStream("stdout"))


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


def get_logger(*args, **kwargs) -> LoggerWithContext:
    """
    Get a structlog logger with the same context alias methods as the logger returned by `configure_logger`.

    This is useful in cases where you want to get a logger without configuring it (e.g. in libraries or in tests).
    """
    log = structlog.get_logger(*args, **kwargs)
    log = add_simple_context_aliases(log)
    return log


def configure_logger(
    *,
    json_logger: bool = False,
    logger_factory=None,
    install_exception_hook: bool = False,
    finalize_configuration: bool = False,
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
        finalize_configuration: If True, any subsequent calls to configure_logger will
            be ignored with a warning. Useful to setup logging and globally and prevent accidental
            reconfiguration by other developers.
    """
    global _CONFIGURATION_FINALIZED

    # Avoid accidental reinitialization without the correct state (e.g. from multiple components
    # trying to configure logging) by allowing the first caller to "lock" the configuration.
    if _CONFIGURATION_FINALIZED:
        package_logger.warning(
            "configure_logger called after finalized configuration, ignoring",
        )
        return get_logger()

    setup_trace()

    # Reset structlog configuration to make sure we're starting fresh
    # This is important for tests where configure_logger might be called multiple times
    structlog.reset_defaults()

    if install_exception_hook:
        hook.install_exception_hook(json_logger)

    actual_factory = logger_factory or _logger_factory(json_logger)

    # Synchronize the output destination between structlog and the standard library logging system
    # We introspect the factory's internal state (checking both public and private attribute conventions)
    stream = getattr(actual_factory, "file", getattr(actual_factory, "_file", None))
    redirect_stdlib_loggers(json_logger, stream=stream)
    redirect_showwarnings()

    structlog.configure(
        # Don't cache the loggers during tests, it makes it hard to capture them
        cache_logger_on_first_use=not is_pytest(),
        wrapper_class=structlog.make_filtering_bound_logger(
            get_environment_log_level_as_string()
        ),
        logger_factory=actual_factory,
        processors=get_default_processors(json_logger),
    )

    if finalize_configuration:
        _CONFIGURATION_FINALIZED = True

    log = structlog.get_logger()
    log = add_simple_context_aliases(log)

    return log
