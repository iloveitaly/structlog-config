# structlog_config.constants

## Attributes

| [`PYTHONASYNCIODEBUG`](#structlog_config.constants.PYTHONASYNCIODEBUG)   | this is a builtin env var, we check for it to ensure we don't silence this log level   |
|-----------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`NO_COLOR`](#structlog_config.constants.NO_COLOR)             | //no-color.org                                                                         |
| [`package_logger`](#structlog_config.constants.package_logger)       | strange name to not be confused with all of the log-related names floating around      |
| [`TRACE_LOG_LEVEL`](#structlog_config.constants.TRACE_LOG_LEVEL)      | Custom log level for trace logging, lower than DEBUG                                   |

## Module Contents

### structlog_config.constants.PYTHONASYNCIODEBUG *= False*

this is a builtin env var, we check for it to ensure we don’t silence this log level

### structlog_config.constants.NO_COLOR

//no-color.org

* **Type:**
  support NO_COLOR standard https

### structlog_config.constants.package_logger

strange name to not be confused with all of the log-related names floating around

### structlog_config.constants.TRACE_LOG_LEVEL *= 5*

Custom log level for trace logging, lower than DEBUG
