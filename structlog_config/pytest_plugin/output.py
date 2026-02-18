import json
import shutil
from pathlib import Path

import pytest
from pytest_plugin_utils import get_artifact_dir

from .. import packages
from .capture import CapturedOutput
from .constants import (
    CAPTURE_ENABLED_KEY,
    CAPTURE_KEY,
    CAPTURED_TESTS_KEY,
    PERSIST_FAILED_ONLY,
    PLUGIN_NAMESPACE,
    CapturedTestFailure,
    _strip_ansi,
)


def _accumulate_captured_output(
    item: pytest.Item, phase_output: CapturedOutput
) -> None:
    """Append per-phase captured output to item's accumulated full output."""
    if not hasattr(item, "_full_captured_output"):
        item._full_captured_output = CapturedOutput(stdout="", stderr="")  # type: ignore[attr-defined]

    existing: CapturedOutput = item._full_captured_output  # type: ignore[attr-defined]
    existing.stdout += phase_output.stdout
    existing.stderr += phase_output.stderr


def _write_output_files(item: pytest.Item):
    """Write captured output to files on failure."""
    config = item.config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})
    if not config[CAPTURE_ENABLED_KEY]:
        return

    test_dir = get_artifact_dir(PLUGIN_NAMESPACE, item)

    if hasattr(item, "_full_captured_output"):
        output = item._full_captured_output  # type: ignore[attr-defined]
    else:
        output = CapturedOutput(stdout="", stderr="")

    # Each phase (setup/call/teardown) can fail independently, so excinfo is a list
    exception_parts = []
    first_excinfo = None
    if hasattr(item, "_excinfo"):
        for _when, excinfo in item._excinfo:  # type: ignore[attr-defined]
            if first_excinfo is None:
                first_excinfo = excinfo
            exception_parts.append(str(excinfo.getrepr(style="long")))

    output.exception = "\n\n".join(exception_parts) if exception_parts else None

    files_written = False

    if output.stdout:
        (test_dir / "stdout.txt").write_text(_strip_ansi(output.stdout))
        files_written = True

    if output.stderr:
        (test_dir / "stderr.txt").write_text(_strip_ansi(output.stderr))
        files_written = True

    if output.exception:
        (test_dir / "exception.txt").write_text(_strip_ansi(output.exception))
        files_written = True

    if first_excinfo is not None and packages.beautiful_traceback is not None:
        from beautiful_traceback.json_formatting import exc_to_json

        exc_dict = exc_to_json(first_excinfo.value, first_excinfo.tb)
        (test_dir / "exception.json").write_text(json.dumps(exc_dict, indent=2))
        files_written = True

    # Only register the test in the summary if files were actually written for a failure
    will_persist = files_written and (
        not PERSIST_FAILED_ONLY or hasattr(item, "_excinfo")
    )
    if not will_persist:
        return

    if first_excinfo is not None:
        # traceback[-1] is the innermost frame — where the assertion/error actually fired
        tb_entry = first_excinfo.traceback[-1]
        # lineno is 0-indexed; +1 converts to the 1-indexed line number editors show
        file = str(tb_entry.path)
        line = tb_entry.lineno + 1
        # exconly() returns "ExceptionType: message" without the full traceback
        exception_summary = first_excinfo.exconly()
    else:
        file = item.nodeid
        line = None
        exception_summary = None

    captured_tests = item.config.stash.get(CAPTURED_TESTS_KEY, [])
    captured_tests.append(
        CapturedTestFailure(
            nodeid=item.nodeid,
            file=file,
            line=line,
            artifact_dir=test_dir,
            exception_summary=exception_summary,
            duration=getattr(item, "_test_duration", None),
        )
    )


def _clean_artifact_dir(path: Path) -> None:
    if not path.exists():
        return

    for entry in path.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
            continue

        entry.unlink()
