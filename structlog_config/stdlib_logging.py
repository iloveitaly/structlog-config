import logging
import sys
from pathlib import Path

import structlog
from decouple import config

from structlog_config.env_config import get_custom_logger_configs

from .constants import PYTHONASYNCIODEBUG
from .environments import is_production, is_staging


def get_environment_log_level_as_string() -> str:
    return config("LOG_LEVEL", default="INFO", cast=str).upper()


def string_to_log_level(level: str) -> int:
    return logging.getLevelNamesMapping()[level]


def get_environment_log_level():
    return logging.getLevelNamesMapping()[get_environment_log_level_as_string()]


def reset_stdlib_logger(
    logger_name: str,
    default_structlog_handler: logging.Handler,
    level_override: str | None = None,
):
    std_logger = logging.getLogger(logger_name)
    std_logger.propagate = False
    std_logger.handlers = []
    std_logger.addHandler(default_structlog_handler)

    if level_override:
        std_logger.setLevel(level_override)


def redirect_stdlib_loggers(json_logger: bool):
    """
    Redirect all standard logging module loggers to use the structlog configuration.

    Inspired by: https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
    """
    from structlog.stdlib import ProcessorFormatter

    level = get_environment_log_level()

    # TODO I don't understand why we can't use a processor stack as-is here. Need to investigate further.

    # Use ProcessorFormatter to format log records using structlog processors
    from .__init__ import get_default_processors

    processors = get_default_processors(json_logger=json_logger)

    formatter = ProcessorFormatter(
        processors=[
            # required to strip extra keys that the structlog stdlib bindings add in
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            processors[-1]
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
            *processors[:-1],
        ],
    )

    def handler_for_path(path: str) -> logging.FileHandler:
        path_obj = Path(path)
        # Create parent directories if they don't exist
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path)
        file_handler.setFormatter(formatter)
        return file_handler

    # Create a handler for the root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]  # Replace existing handlers with our handler

    # Disable propagation to avoid duplicate logs
    root_logger.propagate = True

    # TODO there is a JSON-like format that can be used to configure loggers instead :/
    std_logging_configuration = {
        "httpcore": {},
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
    }

    # Merged from silence_loud_loggers - only silence asyncio if not explicitly debugging it
    if not PYTHONASYNCIODEBUG:
        std_logging_configuration["asyncio"] = {"level": "WARNING"}

    """
    These loggers either:

    1. Are way too chatty by default
    2. Setup before our logging is initialized

    This configuration allows us to easily override configuration of various loggers as we add additional complexity
    to the application. The levels map allows us to define specific level mutations based on the current level configuration
    for a set of standard loggers.
    """

    level_as_string = logging.getLevelName(level)
    environment_logger_config = get_custom_logger_configs()

    # now, let's handle some loggers that are probably already initialized with a handler
    for logger_name, logger_config in std_logging_configuration.items():
        level_override = None

        # Check if we have a direct level setting
        if "level" in logger_config:
            level_override = logger_config["level"]
        # Otherwise, check if we have a level mapping for the current log level
        elif "levels" in logger_config and level_as_string in logger_config["levels"]:
            level_override = logger_config["levels"][level_as_string]

        handler_for_logger = handler

        # Override with environment-specific config if available
        if logger_name in environment_logger_config:
            env_config = environment_logger_config[logger_name]

            # if we have a custom path, use that instead
            if "path" in env_config:
                handler_for_logger = handler_for_path(env_config["path"])

            if "level" in env_config:
                level_override = env_config["level"]

        reset_stdlib_logger(
            logger_name,
            handler_for_logger,
            level_override,
        )

    # Handle any additional loggers defined in environment variables
    for logger_name, logger_config in environment_logger_config.items():
        # skip if already configured!
        if logger_name in std_logging_configuration:
            continue

        handler_for_logger = handler

        if "path" in logger_config:
            # if we have a custom path, use that instead
            handler_for_logger = handler_for_path(logger_config["path"])

        reset_stdlib_logger(
            logger_name,
            handler_for_logger,
            logger_config.get("level"),
        )

    # TODO do i need to setup exception overrides as well?
    # https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e#file-custom_logging-py-L114-L128
    # if sys.excepthook != sys.__excepthook__:
    #     logging.getLogger(__name__).warning("sys.excepthook has been overridden.")
