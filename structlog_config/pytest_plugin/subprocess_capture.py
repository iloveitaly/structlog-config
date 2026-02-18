import os
import sys
from pathlib import Path

from .constants import SUBPROCESS_CAPTURE_ENV, logger

_subprocess_capture_configured = False
"Guard flag so configure_subprocess_capture() is idempotent within a single process."

_subprocess_stdout_file = None
"Open file handle for the current subprocess's stdout capture file."

_subprocess_stderr_file = None
"Open file handle for the current subprocess's stderr capture file."


def configure_subprocess_capture() -> None:
    """Redirect child process stdout/stderr into per-test capture files.

    This is intended for subprocess entrypoints when using the spawn start method,
    where child processes do not inherit the parent's fd redirection. The parent
    sets STRUCTLOG_CAPTURE_DIR to the per-test artifact directory via the
    --structlog-output option; this function creates subprocess-<pid>-stdout.txt
    and subprocess-<pid>-stderr.txt there.

    If STRUCTLOG_CAPTURE_DIR is not set, this is a no-op.
    """
    global _subprocess_capture_configured
    global _subprocess_stdout_file
    global _subprocess_stderr_file

    # Guard against being called more than once in the same subprocess
    if _subprocess_capture_configured:
        return

    # The parent process sets this env var to the per-test artifact directory
    output_dir = os.getenv(SUBPROCESS_CAPTURE_ENV)
    if not output_dir:
        logger.error("subprocess capture env not set", env_var=SUBPROCESS_CAPTURE_ENV)
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Include PID in filenames so concurrent subprocesses don't overwrite each other
    pid = os.getpid()
    stdout_path = output_path / f"subprocess-{pid}-stdout.txt"
    stderr_path = output_path / f"subprocess-{pid}-stderr.txt"

    _subprocess_stdout_file = open(stdout_path, "a", encoding="utf-8")
    _subprocess_stderr_file = open(stderr_path, "a", encoding="utf-8")

    # Redirect OS-level fds so all writes (including from C extensions) go to the files
    os.dup2(_subprocess_stdout_file.fileno(), 1)
    os.dup2(_subprocess_stderr_file.fileno(), 2)

    # Reopen Python's sys.stdout/stderr to match the redirected fds
    sys.stdout = open(1, "w", encoding="utf-8", errors="replace", closefd=False)
    sys.stderr = open(2, "w", encoding="utf-8", errors="replace", closefd=False)

    # Flush on every newline so output isn't lost if the subprocess exits unexpectedly
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    _subprocess_capture_configured = True
