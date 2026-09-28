# structlog_config.levels

## Functions

| [`get_environment_log_level_as_string`](#structlog_config.levels.get_environment_log_level_as_string)(→ str)   |                                                                                |
|-----------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`compare_log_levels`](#structlog_config.levels.compare_log_levels)(→ int)                    | Compare log levels using logging.getLevelNamesMapping for accurate int values. |
| [`resolve_level_name`](#structlog_config.levels.resolve_level_name)(→ int | None)             | Translate a log level name to its numeric value                                |
| [`is_debug_level`](#structlog_config.levels.is_debug_level)(→ bool)                       | Return True when the global logger is configured for DEBUG or TRACE verbosity. |

## Module Contents

### structlog_config.levels.get_environment_log_level_as_string() → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

### structlog_config.levels.compare_log_levels(left: [str](https://docs.python.org/3/builtins/stdtypes.html#str), right: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [int](https://docs.python.org/3/builtins/functions.html#int)

Compare log levels using logging.getLevelNamesMapping for accurate int values.

Example:
>>> compare_log_levels(“DEBUG”, “INFO”)
-1  # DEBUG is less than INFO

Asks the question “Is INFO higher than DEBUG?”

### structlog_config.levels.resolve_level_name(level_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None)

Translate a log level name to its numeric value

### structlog_config.levels.is_debug_level() → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Return True when the global logger is configured for DEBUG or TRACE verbosity.

Helpful for enabling debug flags on various 3rd party libraries. This makes it easy to turn
on debug modes globally via LOG_LEVEL environment variable.
