"""
Configure custom logger behavior based on environment variables.
"""

import logging
import os
import re
from pathlib import Path

# Regex to match LOG_LEVEL_* and LOG_PATH_* environment variables
LOG_LEVEL_PATTERN = re.compile(r"^LOG_LEVEL_(.+)$")
LOG_PATH_PATTERN = re.compile(r"^LOG_PATH_(.+)$")


def get_custom_logger_configs() -> dict[str, dict[str, str]]:
    """
    Parse environment variables to extract custom logger configurations.

    Examples:
        LOG_LEVEL_HTTPX=DEBUG
        LOG_PATH_HTTPX=/var/log/httpx.log

        LOG_LEVEL_MY_CUSTOM_LOGGER=INFO
        LOG_PATH_MY_CUSTOM_LOGGER=/var/log/custom.log

    Returns:
        Dictionary mapping logger names to their configuration.
        Example: {"httpx": {"level": "DEBUG", "path": "/var/log/httpx.log"}}
    """
    custom_configs = {}

    # Process all environment variables
    for env_var in os.environ:
        # Check for level configuration
        if level_match := LOG_LEVEL_PATTERN.match(env_var):
            logger_name = level_match.group(1).lower().replace("_", ".")
            if logger_name not in custom_configs:
                custom_configs[logger_name] = {}
            custom_configs[logger_name]["level"] = os.environ[env_var]

        # Check for path configuration
        elif path_match := LOG_PATH_PATTERN.match(env_var):
            logger_name = path_match.group(1).lower().replace("_", ".")
            if logger_name not in custom_configs:
                custom_configs[logger_name] = {}
            custom_configs[logger_name]["path"] = os.environ[env_var]

    return custom_configs


def setup_custom_loggers(default_handler: logging.Handler) -> None:
    """
    Configure custom loggers based on environment variables.

    Args:
        default_handler: The handler to use for loggers without a custom path.
    """
    custom_configs = get_custom_logger_configs()

    for logger_name, config_dict in custom_configs.items():
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.handlers = []

        # Create custom file handler if path is specified
        if "path" in config_dict:
            path = Path(config_dict["path"])
            path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(path)
            # Use the same formatter as the default handler
            file_handler.setFormatter(default_handler.formatter)
            logger.addHandler(file_handler)
        else:
            # Use default handler if no custom path
            logger.addHandler(default_handler)

        # Set custom level if specified
        if "level" in config_dict:
            level = config_dict["level"].upper()
            if level in logging.getLevelNamesMapping():
                logger.setLevel(logging.getLevelNamesMapping()[level])
