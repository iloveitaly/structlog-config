import json
import shutil
from pathlib import Path
from typing import cast

import pytest
from pytest_plugin_utils import get_artifact_dir

from ..formatters import get_json_exception_formatter
from .capture import CapturedOutput
from .constants import (
    CAPTURE_ENABLED_KEY,
    CAPTURE_KEY,
    CAPTURE_OUTPUT_DIR_KEY,
    CAPTURE_PERSIST_ALL_KEY,
    CAPTURED_TESTS_KEY,
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
    """Write captured output to files for tests that should retain artifacts."""
    config = item.config.stash.get(CAPTURE_KEY, {CAPTURE_ENABLED_KEY: False})
    if not config[CAPTURE_ENABLED_KEY]:
        return

    base_dir = Path(cast(str, config[CAPTURE_OUTPUT_DIR_KEY]))
    test_dir = get_artifact_dir(item, base_dir, create=True)

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

    # Write structured exception data to exception.json
    if first_excinfo is not None:
        formatter = get_json_exception_formatter()
        exc_dict = formatter(
            (first_excinfo.type, first_excinfo.value, first_excinfo.tb)
        )
        (test_dir / "exception.json").write_text(json.dumps(exc_dict, indent=2))
        files_written = True

    persist_all = config.get(CAPTURE_PERSIST_ALL_KEY, False)
    keep_artifacts = files_written and (persist_all or hasattr(item, "_excinfo"))

    if not keep_artifacts:
        return

    if first_excinfo is None:
        return

    # traceback[-1] is the innermost frame — where the assertion/error actually fired
    tb_entry = first_excinfo.traceback[-1]
    # lineno is 0-indexed; +1 converts to the 1-indexed line number editors show
    file = str(tb_entry.path)
    line = tb_entry.lineno + 1
    # exconly() returns "ExceptionType: message" without the full traceback
    exception_summary = first_excinfo.exconly()

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
