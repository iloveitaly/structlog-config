# structlog_config.pytest_plugin

Pytest plugin for capturing test output to files on failure.

This plugin captures stdout, stderr, and exceptions from failing tests and writes
them to organized output directories.

Relationship to pytest’s built-in capture:
: - pytest has built-in output capture that shows output only for failing tests
  - This plugin REPLACES pytest’s capture (we require -s to disable it)
  - Instead of showing output inline, we write it to organized files
  - Useful for CI/CD where you need persistent files to inspect later

Capture:
: SimpleCapture replaces sys.stdout/stderr with StringIO objects.
  - Captures: print(), logging, most Python output
  - Misses: subprocess output, direct fd writes
  <br/>
  For subprocess output capture, call configure_subprocess_capture() at the
  top of your subprocess entrypoint. It reads STRUCTLOG_CAPTURE_DIR (set
  automatically per-test) and redirects the child process’s own fds there.

Usage:
: pytest –structlog-output=./test-output -s

Options:

Requirements:
: - Must use -s (–capture=no) flag to disable pytest’s built-in capture

Output Structure:
: DIR/
  : test_module_\_test_name/
    : stdout.txt      # stdout from test
      stderr.txt      # stderr from test
      exception.txt   # exception traceback
      exception.json  # structured exception data (requires beautiful_traceback)
