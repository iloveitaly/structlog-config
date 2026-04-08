"""
Redirect all stdlib loggers to use the structlog configuration.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog

from .constants import PYTHONASYNCIODEBUG, package_logger
from .env import get_env
from .env_config import get_custom_logger_config
from .factory import python_log_stream_name
from .levels import (
    compare_log_levels,
    get_environment_log_level_as_string,
)


class _LazyStreamHandler(logging.StreamHandler):
    """StreamHandler that always writes to the current sys.stdout or sys.stderr.

    Storing a direct reference to sys.stdout captures the stream at configure time.
    When pytester runs in-process tests and closes its capture buffer, any handler
    pointing to that buffer will raise "I/O operation on closed file" for subsequent
    tests. This handler resolves the stream lazily at emit time instead.
    """

    def __init__(self, stream_name: str):
        super().__init__()
        self._stream_name = stream_name

    @property  # type: ignore[override]
    def stream(self):
        return getattr(sys, self._stream_name)

    @stream.setter
    def stream(self, value):
        pass


def reset_stdlib_logger(
    logger_name: str, default_structlog_handler: logging.Handler, level_override: str
):
    std_logger = logging.getLogger(logger_name)
    std_logger.propagate = False
    std_logger.handlers = []
    std_logger.addHandler(default_structlog_handler)
    std_logger.setLevel(level_override)


def clear_existing_logger_handlers():
    """
    Clear handlers from all existing loggers so they propagate to the root logger.

    This handles libraries like uvicorn/alembic/gunicorn that could install their own
    handlers before configure_logger() is called.
    """
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            if logger.handlers:
                logger.handlers.clear()
                logger.propagate = True
            # No action needed for handler-less loggers: they're in the normal Python default state.
            # logging.getLogger("name") creates loggers without handlers that propagate to root.
        elif not isinstance(logger, logging.PlaceHolder):
            # warn if loggerDict contains unexpected types, guards against future stdlib API changes
            package_logger.warning(
                "unexpected type in loggerDict",
                type=type(logger).__name__,
            )


def _handler_for_path(path: str, formatter: logging.Formatter) -> logging.FileHandler:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(path)
    file_handler.setFormatter(formatter)
    return file_handler


def _handler_for_stream(
    target_stream: Any, formatter: logging.Formatter
) -> logging.Handler:
    # Detect lazy wrappers (_LazyStream/_LazyBuffer) by name, and resolve raw
    # buffers (e.g. stderr.buffer) to their text equivalents. Use _LazyStreamHandler
    # so the handler never holds a stale reference to a stream that may be closed
    # (e.g. after pytester closes its in-process capture buffer).
    stream_name = getattr(target_stream, "name", None)
    if (
        stream_name == "stderr"
        or target_stream == getattr(sys.stderr, "buffer", None)
        or target_stream == sys.stderr
    ):
        return _LazyStreamHandler("stderr")

    if (
        stream_name == "stdout"
        or target_stream == getattr(sys.stdout, "buffer", None)
        or target_stream == sys.stdout
    ):
        return _LazyStreamHandler("stdout")

    if isinstance(stream_name, str):
        return _handler_for_path(stream_name, formatter)

    return logging.StreamHandler(target_stream)


def _stream_for_logger_factory(logger_factory: Any) -> Any:
    """Extract the output stream from a structlog logger factory.

    Stdlib redirection needs to mirror whatever destination the structlog factory
    is using so both logging systems stay coordinated. Structlog factories expose
    that output via internal `file` or `_file` attributes rather than a stable
    public accessor. The returned object may be a real file handle, sys.stdout /
    sys.stderr, or one of this module's lazy stdout/stderr wrappers, so we
    centralize the introspection here instead of leaking it into configure_logger.
    """
    return getattr(logger_factory, "file", None) or getattr(
        logger_factory, "_file", None
    )


def _default_handler_for_destination(
    *,
    formatter: logging.Formatter,
    logger_factory: Any = None,
) -> logging.Handler:
    """
    There's some code duplication with get_logger_factory, but stdlib logging requires a completely
    different object for handling logs, so there's not a cleaner way to handle this right now.
    """
    
    # if the user specified a struclot logger_factory, attempt to extract a stream reference from it so we can syncronize output
    stream = _stream_for_logger_factory(logger_factory) if logger_factory else None

    # if a logger_factory is present, it was provided by the user, so we prioritize using it
    if stream:
        return _handler_for_stream(stream, formatter)

    python_log_path = get_env("PYTHON_LOG_PATH")
    std_stream_name = python_log_stream_name(python_log_path)

    if std_stream_name:
        return _handler_for_stream(getattr(sys, std_stream_name), formatter)

    if python_log_path:
        return _handler_for_path(python_log_path, formatter)

    return _LazyStreamHandler("stdout")


def redirect_stdlib_loggers(
    json_logger: bool,
    logger_factory: Any = None,
):
    """
    Redirect all standard logging module loggers to use the structlog configuration.

    - json_loggers determines if logs are rendered as JSON or not
    - The stdlib log stream is used to write logs to the output device (normally, stdout)

    Inspired by: https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
    """
    from structlog.stdlib import ProcessorFormatter

    global_log_level = get_environment_log_level_as_string()

    # TODO I don't understand why we can't use a processor stack as-is here. Need to investigate further.

    # importing here to avoid circular imports
    from .__init__ import get_default_processors

    # get the list of processors used for the normal structlog rendering, including JSON or console rendering
    default_processors = get_default_processors(json_logger)

    if json_logger:
        adjusted_processors_for_stdlib = [
            # slice off the orjson-based render, since it outputs bytes, not str
            # note that the ExceptionRenderer (exception object => json dict) is retained
            # NOTE the `-1` does tie this method to the underlying implementation of get_default_processors!
            *default_processors[:-1],
            # TODO do we really need sort_keys? there was some reason I did this back in the day...
            # str-based JSONRenderer: stdlib expects str, not bytes from orjson
            structlog.processors.JSONRenderer(sort_keys=True),
        ]
    else:
        adjusted_processors_for_stdlib = default_processors

    # ProcessorFormatter converts LogRecords (stdlib structures) to a structlog event dict
    formatter = ProcessorFormatter(
        # for stdlib records, runs first
        foreign_pre_chain=[
            # logger names are not supported when not using structlog.stdlib.LoggerFactory
            # https://github.com/hynek/structlog/issues/254
            structlog.stdlib.add_logger_name,
        ],
        # once we have the structlog event dict, render it using the final processors
        processors=[
            # It strips structlog’s internal metadata keys (_record, _from_structlog) from the event dict so they don't show up in output.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *adjusted_processors_for_stdlib,
        ],
    )

    default_handler = _default_handler_for_destination(
        formatter=formatter,
        logger_factory=logger_factory,
    )

    default_handler.setLevel(global_log_level)
    default_handler.setFormatter(formatter)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(global_log_level)
    root_logger.handlers = [default_handler]

    # Clear handlers from all existing loggers in case they were initialized before the call to configure_logger
    clear_existing_logger_handlers()

    # TODO there is a JSON-like format that can be used to configure loggers instead :/
    #      we should probably transition to using that format instead of this customized mapping
    std_logging_configuration: dict[str, dict[str, Any]] = {
        "httpx": {
            "levels": {
                "INFO": "WARNING",
            }
        },
        "azure.core.pipeline.policies.http_logging_policy": {
            "levels": {
                "INFO": "WARNING",
            }
        },
        # stripe INFO logs are pretty noisy by default
        "stripe": {
            "levels": {
                "INFO": "WARNING",
            }
        },
    }
    """
    These loggers either:

    1. Are way too chatty by default
    2. Setup before our logging is initialized

    This configuration allows us to easily override configuration of various loggers as we add additional complexity
    to the application. The levels map allows us to define specific level mutations based on the current level configuration
    for a set of standard loggers.
    """

    # TODO do we need this? could be AI slop

    if not PYTHONASYNCIODEBUG:
        std_logging_configuration["asyncio"] = {"level": "WARNING"}

    environment_logger_config = get_custom_logger_config()

    # now, let's handle some loggers that are probably already initialized with a handler
    for logger_name, logger_config in std_logging_configuration.items():
        level_override = None

        # if we have a level override, use that
        if "level" in logger_config:
            level_override = logger_config["level"]
            assert isinstance(level_override, str), (
                f"Expected level override for {logger_name} to be a string, got {type(level_override)}"
            )
        # Check if we have a level mapping for the current log level
        elif "levels" in logger_config and global_log_level in logger_config["levels"]:
            level_override = logger_config["levels"][global_log_level]

        # if a static override exists, only use it if it is lower than the global log level
        if level_override and (
            compare_log_levels(
                level_override,
                global_log_level,
            )
            < 0
        ):
            level_override = None

        handler_for_logger = default_handler

        # Override with environment-specific config if available
        if logger_name in environment_logger_config:
            env_config = environment_logger_config[logger_name]

            # if we have a custom path, use that instead
            # right now this is the only handler override type we support
            if "path" in env_config:
                handler_for_logger = _handler_for_path(env_config["path"], formatter)

            # if the level is set via dynamic config, always use that
            if "level" in env_config:
                level_override = env_config["level"]

        reset_stdlib_logger(
            logger_name,
            handler_for_logger,
            level_override or global_log_level,
        )

    # Handle any additional loggers defined in environment variables
    for logger_name, logger_config in environment_logger_config.items():
        # skip if already configured via the above loop
        if logger_name in std_logging_configuration:
            continue

        handler_for_logger = default_handler

        if "path" in logger_config:
            # if we have a custom path, use that instead
            handler_for_logger = _handler_for_path(logger_config["path"], formatter)

        reset_stdlib_logger(
            logger_name,
            handler_for_logger,
            logger_config.get("level", global_log_level),
        )
