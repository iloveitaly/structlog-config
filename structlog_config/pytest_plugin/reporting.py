from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .constants import CapturedTestFailure


def _write_results_json(
    captured_tests: list[CapturedTestFailure], output_dir: str
) -> None:
    failures = [
        {
            "file": failure.file,
            "test": failure.nodeid,
            "line": failure.line,
            "exception": failure.exception_summary,
            "logs": str(failure.artifact_dir.relative_to(output_dir)),
        }
        for failure in captured_tests
    ]

    Path(output_dir, "results.json").write_text(json.dumps(failures, indent=2))


def _collect_slow_reports(terminalreporter, threshold: float) -> list:
    slow = []
    for report in terminalreporter.stats.get("passed", []):
        if report.when == "call" and report.duration >= threshold:
            slow.append(report)
    return sorted(slow, key=lambda r: r.duration, reverse=True)
