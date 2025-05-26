import logging

from decouple import config


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
    level_map = logging.getLevelNamesMapping()
    left_level = level_map.get(left, left)
    right_level = level_map.get(right, right)

    # TODO should more gracefully fail here, but let's see what happens
    if not isinstance(left_level, int) or not isinstance(right_level, int):
        raise ValueError(
            f"Invalid log level comparison: {left} ({type(left_level)}) vs {right} ({type(right_level)})"
        )

    return left_level - right_level
