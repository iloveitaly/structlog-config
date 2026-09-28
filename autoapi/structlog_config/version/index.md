# structlog_config.version

Version handling for structlog-config.

## Functions

| [`is_local_source_checkout`](#structlog_config.version.is_local_source_checkout)(→ bool)   | Check if the code is running from a local source checkout.     |
|-------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [`get_version`](#structlog_config.version.get_version)(→ str)                 | Get the version string, appending .dev if running from source. |

## Module Contents

### structlog_config.version.is_local_source_checkout() → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Check if the code is running from a local source checkout.

### structlog_config.version.get_version() → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

Get the version string, appending .dev if running from source.
