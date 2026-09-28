# structlog_config.trace

Adds a TRACE log level to the standard logging module and structlog.

Some people believe that the standard log levels are not enough, and I’m with them.

Adapted from:
- [https://github.com/willmcgugan/httpx/blob/973d1ed4e06577d928061092affe8f94def03331/httpx/_utils.py#L231](https://github.com/willmcgugan/httpx/blob/973d1ed4e06577d928061092affe8f94def03331/httpx/_utils.py#L231)
- [https://github.com/vladmandic/sdnext/blob/d5d857aa961edbc46c9e77e7698f2e60011e7439/installer.py#L154](https://github.com/vladmandic/sdnext/blob/d5d857aa961edbc46c9e77e7698f2e60011e7439/installer.py#L154)

## Classes

| [`Logger`](#structlog_config.trace.Logger)   | Instances of the Logger class represent a single logging channel. A   |
|-----------------------------------------------------------|-----------------------------------------------------------------------|

## Functions

| [`setup_trace`](#structlog_config.trace.setup_trace)(→ None)   | Setup TRACE logging level. Safe to call multiple times.   |
|------------------------------------------------------------------------|-----------------------------------------------------------|

## Module Contents

### *class* structlog_config.trace.Logger(name, level=NOTSET)

Bases: [`logging.Logger`](https://docs.python.org/3/library/logging.html#logging.Logger)

Instances of the Logger class represent a single logging channel. A
“logging channel” indicates an area of an application. Exactly how an
“area” is defined is up to the application developer. Since an
application can have any number of areas, logging channels are identified
by a unique string. Application areas can be nested (e.g. an area
of “input processing” might include sub-areas “read CSV files”, “read
XLS files” and “read Gnumeric files”). To cater for this natural nesting,
channel names are organized into a namespace hierarchy where levels are
separated by periods, much like the Java or Python package namespace. So
in the instance given above, channel names might be “input” for the upper
level, and “input.csv”, “input.xls” and “input.gnu” for the sub-levels.
There is no arbitrary limit to the depth of nesting.

#### trace(message: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*args: Any, \*\*kwargs: Any) → [None](https://docs.python.org/3/builtins/constants.html#None)

### structlog_config.trace.setup_trace() → [None](https://docs.python.org/3/builtins/constants.html#None)

Setup TRACE logging level. Safe to call multiple times.
