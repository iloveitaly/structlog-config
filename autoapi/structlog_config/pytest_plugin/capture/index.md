# structlog_config.pytest_plugin.capture

## Classes

| [`CapturedOutput`](#structlog_config.pytest_plugin.capture.CapturedOutput)   | Container for captured output from a test phase.                               |
|-------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`SimpleCapture`](#structlog_config.pytest_plugin.capture.SimpleCapture)    | Captures via `sys.stdout` and `sys.stderr` replacement. No subprocess support. |

## Module Contents

### *class* structlog_config.pytest_plugin.capture.CapturedOutput

Container for captured output from a test phase.

#### stdout *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### stderr *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### exception *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)* *= None*

### *class* structlog_config.pytest_plugin.capture.SimpleCapture

Captures via `sys.stdout` and `sys.stderr` replacement. No subprocess support.

This works similarly to pytest’s built-in capture (which we disable with `-s`).
It replaces those streams with `StringIO` objects, capturing any Python code
that writes to them (`print()`, logging, and so on).

Limitations:

* Does not capture subprocess output. Children inherit file descriptors, not `sys.stdout`.
* Does not capture direct file descriptor writes (`os.write(1, ...)`).
* Only captures output from the current Python process.

For subprocess output capture, use `configure_subprocess_capture()` instead.

#### start()

Start capturing stdout and stderr.

#### stop() → [CapturedOutput](#structlog_config.pytest_plugin.capture.CapturedOutput)

Stop capturing and return captured output.
