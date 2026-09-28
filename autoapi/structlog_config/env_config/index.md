# structlog_config.env_config

Configure custom logger behavior based on environment variables.

## Attributes

| [`LOG_LEVEL_PATTERN`](#structlog_config.env_config.LOG_LEVEL_PATTERN)   |    |
|----------------------------------------------------------------------|----|
| [`LOG_PATH_PATTERN`](#structlog_config.env_config.LOG_PATH_PATTERN)    |    |

## Classes

| [`EnvLoggerConfig`](#structlog_config.env_config.EnvLoggerConfig)   | Level and path for one logger, taken from `LOG_LEVEL_*` and `LOG_PATH_*`.   |
|--------------------------------------------------------------------|-----------------------------------------------------------------------------|

## Functions

| [`get_custom_logger_config`](#structlog_config.env_config.get_custom_logger_config)(→ dict[str, EnvLoggerConfig])   | Parse environment variables to extract custom logger configurations.   |
|-----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|

## Module Contents

### structlog_config.env_config.LOG_LEVEL_PATTERN

### structlog_config.env_config.LOG_PATH_PATTERN

### *class* structlog_config.env_config.EnvLoggerConfig

Bases: `TypedDict`

Level and path for one logger, taken from `LOG_LEVEL_*` and `LOG_PATH_*`.

#### level *: NotRequired[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

#### path *: NotRequired[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

### structlog_config.env_config.get_custom_logger_config() → [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [EnvLoggerConfig](#structlog_config.env_config.EnvLoggerConfig)]

Parse environment variables to extract custom logger configurations.

Logger names in the variable use underscores instead of dots.
`LOG_LEVEL_HTTPX` and `LOG_PATH_HTTPX` configure the `httpx` logger.

* **Returns:**
  Mapping of logger name to `level` and `path` settings.
