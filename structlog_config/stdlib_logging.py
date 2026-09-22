"""
Redirect all stdlib loggers to use the structlog configuration.
"""

import logging
import sys
from io import BufferedIOBase, RawIOBase
from pathlib import Path
from typing import Any, BinaryIO

import structlog

from .constants import PYTHONASYNCIODEBUG, package_logger
from .env import get_env
from .env_config import get_custom_logger_config
from .factory import LazyStream, python_log_stream_name
from .levels import (
    compare_log_levels,
    get_environment_log_level_as_string,
)
from .tee import _TeeFileHandler, _TeeStreamHandler


class _Utf8TextStream:
    """
    Let a text-writing stdlib handler use a caller-owned binary stream.

    BytesLoggerFactory can send structlog's already-encoded JSON to BytesIO or
    another binary destination. Stdlib formatters still return str, even in JSON
    mode, and StreamHandler writes that text plus a terminator. Writing it directly
    to the same binary destination would raise TypeError.

    This adapter only encodes text as UTF-8 and forwards flushes. Formatting,
    terminators, errors, and optional teeing stay with the handler. It neither adds
    buffering nor takes ownership of the underlying stream.
    """

    def __init__(self, stream: BinaryIO):
        self._stream = stream

    def write(self, text: str) -> int:
        self._stream.write(text.encode("utf-8"))
        return len(text)

    def flush(self) -> None:
        self._stream.flush()


def _is_binary_stream(stream: object) -> bool:
    # check IOBase for in-memory streams like BytesIO; check mode for file wrappers
    if isinstance(stream, (RawIOBase, BufferedIOBase)):
        return True

    mode = getattr(stream, "mode", None)
    return isinstance(mode, str) and "b" in mode


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


def _destination_for_stream(target_stream):
    """
    Resolve a factory's stream to a lazy standard stream, path, or supplied stream.

    Storing stdout/stderr directly captures them at configuration time. Pytester's
    in-process tests can close those capture buffers, so reuse LazyStream to look
    up the current stream on every write and flush. Resolution is independent of
    whether the resulting handler will tee records.
    """

    # Detect lazy wrappers (_LazyStream/_LazyBuffer) by name, and resolve raw
    # buffers (e.g. stderr.buffer) to their text equivalents. Use LazyStream
    # so the handler never holds a stale reference to a stream that may be closed
    # (e.g. after pytester closes its in-process capture buffer).
    stream_name = getattr(target_stream, "name", None)
    if (
        stream_name == "stderr"
        or target_stream == getattr(sys.stderr, "buffer", None)
        or target_stream == sys.stderr
    ):
        return LazyStream("stderr")

    if (
        stream_name == "stdout"
        or target_stream == getattr(sys.stdout, "buffer", None)
        or target_stream == sys.stdout
    ):
        return LazyStream("stdout")

    if isinstance(stream_name, str):
        return Path(stream_name)

    return target_stream


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


def _default_destination(logger_factory=None):
    """
    Resolve the primary destination without choosing a handler or enabling teeing.

    An explicit factory takes precedence over PYTHON_LOG_PATH; absent either,
    stdlib output follows stdout lazily. Named file streams retain path-based
    handling, while anonymous streams are used directly.
    """

    # if the user specified a struclot logger_factory, attempt to extract a stream reference from it so we can syncronize output
    stream = _stream_for_logger_factory(logger_factory) if logger_factory else None

    # if a logger_factory is present, it was provided by the user, so we prioritize using it
    if stream:
        return _destination_for_stream(stream)

    python_log_path = get_env("PYTHON_LOG_PATH")
    std_stream_name = python_log_stream_name(python_log_path)

    if std_stream_name:
        return LazyStream(std_stream_name)

    if python_log_path:
        return Path(python_log_path)

    return LazyStream("stdout")


def _create_handler(
    destination, formatter: logging.Formatter, *, enable_tee: bool
) -> logging.Handler:
    """
    Construct a formatted handler after destination resolution.

    Tee selection happens only here. Binary streams use the same text adapter
    with either handler; paths retain FileHandler's ownership and cleanup.
    """

    if isinstance(destination, Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_handler_class = _TeeFileHandler if enable_tee else logging.FileHandler
        handler = file_handler_class(destination)
    else:
        stream = (
            _Utf8TextStream(destination)
            if _is_binary_stream(destination)
            else destination
        )
        stream_handler_class = (
            _TeeStreamHandler if enable_tee else logging.StreamHandler
        )
        handler = stream_handler_class(stream)

    # apply console/JSON formatting once, regardless of the selected primary destination
    handler.setFormatter(formatter)
    return handler


def redirect_stdlib_loggers(
    json_logger: bool,
    logger_factory: Any = None,
    *,
    enable_tee: bool = False,
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

    default_handler = _create_handler(
        _default_destination(logger_factory),
        formatter,
        enable_tee=enable_tee,
    )

    default_handler.setLevel(global_log_level)

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
                handler_for_logger = _create_handler(
                    Path(env_config["path"]), formatter, enable_tee=enable_tee
                )

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
            handler_for_logger = _create_handler(
                Path(logger_config["path"]), formatter, enable_tee=enable_tee
            )

        reset_stdlib_logger(
            logger_name,
            handler_for_logger,
            logger_config.get("level", global_log_level),
        )
