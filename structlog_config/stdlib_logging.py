"""
Redirect all stdlib loggers to use the structlog configuration.
"""

import logging
import sys
from pathlib import Path

import structlog
from decouple import config

from .constants import PYTHONASYNCIODEBUG
from .env_config import get_custom_logger_config
from .environments import is_production, is_staging
from .levels import (
    compare_log_levels,
    get_environment_log_level_as_string,
)


def reset_stdlib_logger(
    logger_name: str, default_structlog_handler: logging.Handler, level_override: str
):
    std_logger = logging.getLogger(logger_name)
    std_logger.propagate = False
    std_logger.handlers = []
    std_logger.addHandler(default_structlog_handler)
    std_logger.setLevel(level_override)


def redirect_stdlib_loggers(json_logger: bool):
    """
    Redirect all standard logging module loggers to use the structlog configuration.

    - json_loggers determines if logs are rendered as JSON or not
    - The stdlib log stream is used to write logs to the output device (normally, stdout)

    Inspired by: https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
    """
    from structlog.stdlib import ProcessorFormatter

    global_log_level = get_environment_log_level_as_string()

    # TODO I don't understand why we can't use a processor stack as-is here. Need to investigate further.

    # TODO why are we importing this here?
    # Use ProcessorFormatter to format log records using structlog processors
    from .__init__ import get_default_processors

    default_processors = get_default_processors(json_logger=json_logger)

    formatter = ProcessorFormatter(
        processors=[
            # required to strip extra keys that the structlog stdlib bindings add in
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            default_processors[-1]
            if not is_production() and not is_staging()
            # don't use ORJSON here, as the stdlib formatter chain expects a str not a bytes
            else structlog.processors.JSONRenderer(sort_keys=True),
        ],
        # processors unique to stdlib logging
        foreign_pre_chain=[
            # logger names are not supported when not using structlog.stdlib.LoggerFactory
            # https://github.com/hynek/structlog/issues/254
            structlog.stdlib.add_logger_name,
            # omit the renderer so we can implement our own
            *default_processors[:-1],
        ],
    )

    def handler_for_path(path: str) -> logging.FileHandler:
        path_obj = Path(path)
        # Create parent directories if they don't exist
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path)
        file_handler.setFormatter(formatter)
        return file_handler

    python_log_path = config("PYTHON_LOG_PATH", default=None)

    # if json_logger and python_log_path:

    default_handler = (
        logging.FileHandler(python_log_path)
        if python_log_path
        else logging.StreamHandler(sys.stdout)
    )
    default_handler.setLevel(global_log_level)
    default_handler.setFormatter(formatter)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(global_log_level)
    root_logger.handlers = [default_handler]

    # Disable propagation to avoid duplicate logs
    root_logger.propagate = True

    # TODO there is a JSON-like format that can be used to configure loggers instead :/
    #      we should probably transition to using that format instead of this customized mapping
    std_logging_configuration = {
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
                handler_for_logger = handler_for_path(env_config["path"])

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
            handler_for_logger = handler_for_path(logger_config["path"])

        reset_stdlib_logger(
            logger_name,
            handler_for_logger,
            logger_config.get("level", global_log_level),
        )

    # TODO do i need to setup exception overrides as well?
    # https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e#file-custom_logging-py-L114-L128
    # if sys.excepthook != sys.__excepthook__:
    #     logging.getLogger(__name__).warning("sys.excepthook has been overridden.")
