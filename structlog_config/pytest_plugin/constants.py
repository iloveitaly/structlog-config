import re
from dataclasses import dataclass
from pathlib import Path

import pytest
import structlog
from pytest_plugin_utils import set_pytest_option

logger = structlog.get_logger(logger_name="structlog_config.pytest")


@dataclass
class CapturedTestFailure:
    # "path/to/test.py:42" — from the innermost traceback entry
    location: str
    # directory containing the stdout/stderr/exception capture files for this test
    artifact_dir: Path
    # one-line summary from ExceptionInfo.exconly(): type + message, no traceback
    exception_summary: str | None
    # duration of the test's call phase in seconds
    duration: float | None = None


CAPTURE_KEY = pytest.StashKey[dict]()
"Stash key for the plugin's config dict on pytest.Config."

CAPTURED_TESTS_KEY = pytest.StashKey[list[CapturedTestFailure]]()
"Stash key for the list of failed tests that had output captured."

SLOW_THRESHOLD_KEY = pytest.StashKey[float | None]()
"Stash key for the slow test threshold in seconds; None means slow reporting is disabled."

PLUGIN_NAMESPACE: str = "structlog_config"
"Namespace used when registering options and artifact dirs with pytest-plugin-utils."

SUBPROCESS_CAPTURE_ENV = "STRUCTLOG_CAPTURE_DIR"
"Env var set per-test so spawned subprocesses know which artifact directory to write into."

PERSIST_FAILED_ONLY = True
"When True, artifact directories are deleted for passing tests."

CAPTURE_ENABLED_KEY = "enabled"
"Key in the CAPTURE_KEY stash dict that indicates whether the plugin is active."

CAPTURE_OUTPUT_DIR_KEY = "output_dir"
"Key in the CAPTURE_KEY stash dict that holds the root output directory path."

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


set_pytest_option(
    PLUGIN_NAMESPACE,
    "structlog_output",
    default=None,
    help="Enable output capture on test failure and write to DIR",
    available=None,
    type_hint=Path,
)
