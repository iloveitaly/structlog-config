"""
Configure custom logger behavior based on environment variables.
"""

import os
import re
from typing import NotRequired, TypedDict

# Regex to match LOG_LEVEL_* and LOG_PATH_* environment variables
LOG_LEVEL_PATTERN = re.compile(r"^LOG_LEVEL_(.+)$")
LOG_PATH_PATTERN = re.compile(r"^LOG_PATH_(.+)$")


class EnvLoggerConfig(TypedDict):
    """Level and path for one logger, taken from ``LOG_LEVEL_*`` and ``LOG_PATH_*``."""

    level: NotRequired[str]
    path: NotRequired[str]


def get_custom_logger_config() -> dict[str, EnvLoggerConfig]:
    """Parse environment variables to extract custom logger configurations.

    Logger names in the variable use underscores instead of dots.
    ``LOG_LEVEL_HTTPX`` and ``LOG_PATH_HTTPX`` configure the ``httpx`` logger.

    Returns:
        Mapping of logger name to ``level`` and ``path`` settings.
    """
    custom_configs = {}

    # Process environment variables in reverse alphabetical order
    # This ensures that HTTP_X will be processed after HTTPX if both exist,
    # making the last one (alphabetically) win
    for env_var in sorted(os.environ.keys(), reverse=True):
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
