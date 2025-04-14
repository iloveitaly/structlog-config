"""
Configure custom logger behavior based on environment variables.
"""

import os
import re

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
