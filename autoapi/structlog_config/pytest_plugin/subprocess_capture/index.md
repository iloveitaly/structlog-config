# structlog_config.pytest_plugin.subprocess_capture

## Functions

| [`configure_subprocess_capture`](#structlog_config.pytest_plugin.subprocess_capture.configure_subprocess_capture)(→ None)   | Redirect child process stdout/stderr into per-test capture files.   |
|-----------------------------------------------------------------------------------------|---------------------------------------------------------------------|

## Module Contents

### structlog_config.pytest_plugin.subprocess_capture.configure_subprocess_capture() → [None](https://docs.python.org/3/builtins/constants.html#None)

Redirect child process stdout/stderr into per-test capture files.

This is intended for subprocess entrypoints when using the spawn start method,
where child processes do not inherit the parent’s fd redirection. The parent
sets STRUCTLOG_CAPTURE_DIR to the per-test artifact directory via the
–structlog-output option; this function creates subprocess-<pid>-stdout.txt
and subprocess-<pid>-stderr.txt there.

If STRUCTLOG_CAPTURE_DIR is not set, this is a no-op.
