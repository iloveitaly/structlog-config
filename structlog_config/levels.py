import logging

from decouple import config

from .constants import TRACE_LOG_LEVEL, package_logger


def get_environment_log_level_as_string() -> str:
    level = config("LOG_LEVEL", default="INFO", cast=str).upper()

    if not level.strip():
        level = "INFO"

    return level


def compare_log_levels(left: str, right: str) -> int:
    """
    Compare log levels using logging.getLevelNamesMapping for accurate int values.

    Example:
    >>> compare_log_levels("DEBUG", "INFO")
    -1  # DEBUG is less than INFO

    Asks the question "Is INFO higher than DEBUG?"
    """
    left_level = _resolve_level_name(left)
    right_level = _resolve_level_name(right)

    if left_level is None or right_level is None:
        raise ValueError(
            f"Invalid log level comparison: {left} ({left_level}) vs {right} ({right_level})"
        )

    return left_level - right_level


def _resolve_level_name(level_name: str) -> int | None:
    """Translate a log level name to its numeric value."""
    level_map = logging.getLevelNamesMapping()
    resolved = level_map.get(level_name)

    if isinstance(resolved, int):
        return resolved

    if level_name == "TRACE":
        return getattr(logging, "TRACE", TRACE_LOG_LEVEL)

    try:
        return int(level_name)
    except (TypeError, ValueError):
        return None


def is_debug_level() -> bool:
    """
    Return True when the global logger is configured for DEBUG or TRACE verbosity.

    Helpful for enabling `debug` flags on various 3rd party libraries. This makes it easy to turn
    on debug modes globally via LOG_LEVEL environment variable.
    """
    root_logger = logging.getLogger()
    current_level = root_logger.getEffectiveLevel()

    if current_level == logging.NOTSET:
        # Root loggers default to NOTSET until configured. In that state logging falls back to
        # environment configuration, so resolve the env value manually to avoid treating it as INFO.
        package_logger.warning(
            "Detected root logger level logging.NOTSET; falling back to LOG_LEVEL env value."
        )
        env_level = _resolve_level_name(get_environment_log_level_as_string())
        if env_level is None:
            return False
        current_level = env_level

    debug_level = _resolve_level_name("DEBUG") or logging.DEBUG

    return current_level <= debug_level
