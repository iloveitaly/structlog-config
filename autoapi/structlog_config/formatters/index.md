# structlog_config.formatters

## Classes

| [`PathPrettifier`](#structlog_config.formatters.PathPrettifier)    | A processor for printing paths.                                    |
|--------------------------------------------------------------------|--------------------------------------------------------------------|
| [`RenameField`](#structlog_config.formatters.RenameField)       | A structlog processor that renames fields in the event dictionary. |
| [`WheneverFormatter`](#structlog_config.formatters.WheneverFormatter) | A processor for formatting whenever datetime objects.              |

## Functions

| [`simplify_activemodel_objects`](#structlog_config.formatters.simplify_activemodel_objects)(...)               | Make the following transformations to the logs:                                                          |
|--------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| [`logger_name`](#structlog_config.formatters.logger_name)(→ structlog.typing.EventDict)       | structlog does not have named loggers, so we roll our own                                                |
| [`beautiful_traceback_exception_formatter`](#structlog_config.formatters.beautiful_traceback_exception_formatter)(→ None) | By default, rich and then better-exceptions is used to render exceptions when a ConsoleRenderer is used. |
| [`get_json_exception_formatter`](#structlog_config.formatters.get_json_exception_formatter)()                  | Returns a callable that formats an exception for JSON logging.                                           |
| [`add_fastapi_context`](#structlog_config.formatters.add_fastapi_context)(...)                        | Take all state added to starlette-context and add to the logs                                            |

## Module Contents

### structlog_config.formatters.simplify_activemodel_objects(logger: [logging.Logger](https://docs.python.org/3/library/logging.html#logging.Logger), method_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str), event_dict: [collections.abc.MutableMapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), Any]) → [collections.abc.MutableMapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), Any]

Make the following transformations to the logs:

- Convert keys (‘object’) whose value inherit from activemodel’s BaseModel to object_id=str(object.id)
- Convert TypeIDs to their string representation object=str(object)

What’s tricky about this method, and other structlog processors, is they are run *after* a response
is returned to the user. So, they don’t error out in tests and it doesn’t impact users. They do show up in Sentry.

### structlog_config.formatters.logger_name(logger: Any, method_name: Any, event_dict: structlog.typing.EventDict) → structlog.typing.EventDict

structlog does not have named loggers, so we roll our own

```pycon
>>> structlog.get_logger(logger_name="my_logger_name")
```

### structlog_config.formatters.beautiful_traceback_exception_formatter(sio: TextIO, exc_info: structlog.typing.ExcInfo) → [None](https://docs.python.org/3/builtins/constants.html#None)

By default, rich and then better-exceptions is used to render exceptions when a ConsoleRenderer is used.

I prefer beautiful-traceback, so I’ve added a custom processor to use it.

[https://github.com/hynek/structlog/blob/66e22d261bf493ad2084009ec97c51832fdbb0b9/src/structlog/dev.py#L412](https://github.com/hynek/structlog/blob/66e22d261bf493ad2084009ec97c51832fdbb0b9/src/structlog/dev.py#L412)

### structlog_config.formatters.get_json_exception_formatter()

Returns a callable that formats an exception for JSON logging.
Unifies the logic between standard logs and the pytest plugin.

### *class* structlog_config.formatters.PathPrettifier(base_dir: [pathlib.Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None)

A processor for printing paths.

Changes all pathlib.Path objects.

1. Remove PosixPath(…) wrapper by calling str() on the path.
2. If path is relative to current working directory,
   print it relative to working directory.

Note that working directory is determined when configuring structlog.

#### base_dir

### *class* structlog_config.formatters.RenameField(fields: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict))

A structlog processor that renames fields in the event dictionary.

This processor allows for renaming keys in the event dictionary during log processing.

* **Parameters:**
  **fields** ([*dict*](https://docs.python.org/3/builtins/stdtypes.html#dict)) – A dictionary mapping original field names (keys) to new field names (values).
  For example, {‘old_name’: ‘new_name’} will rename ‘old_name’ to ‘new_name’.
* **Returns:**
  A callable that transforms an event dictionary by renaming specified fields.
* **Return type:**
  callable

### Examples

```pycon
>>> from structlog.processors import TimeStamper
>>> processors = [
...     RenameField({"timestamp": "new_field"}),
... ]
>>> # This will rename "timestamp" field to "New_field" in log events
```

#### fields

### *class* structlog_config.formatters.WheneverFormatter

A processor for formatting whenever datetime objects.

Changes all whenever datetime objects (ZonedDateTime, Instant, PlainDateTime, etc.)
from their repr() format (e.g., ZonedDateTime(“2025-11-02 00:00:00+00:00[UTC]”))
to their string format (e.g., 2025-11-02 00:00:00+00:00[UTC]).

This provides cleaner log output without the class wrapper.

### structlog_config.formatters.add_fastapi_context(logger: [logging.Logger](https://docs.python.org/3/library/logging.html#logging.Logger), method_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str), event_dict: [collections.abc.MutableMapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), Any]) → [collections.abc.MutableMapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), Any]

Take all state added to starlette-context and add to the logs

[https://github.com/tomwojcik/starlette-context/blob/master/example/setup_logging.py](https://github.com/tomwojcik/starlette-context/blob/master/example/setup_logging.py)
