"""
LLMs added this.

This seems really unnecessary, but why not? Clever way to ensure that our code examples work.
"""

import json

from examples.basic_example import run_demo
from tests.utils import temp_env_var


def test_basic_example_emits_structured_logs(capsys):
    with temp_env_var({"PYTHON_ENV": "production", "LOG_LEVEL": "TRACE"}):
        run_demo(json_mode=True)

    log_output = capsys.readouterr().out
    json_lines = [
        json.loads(line) for line in log_output.splitlines() if line.startswith("{")
    ]

    assert any(
        line["event"] == "example boot" and line["json_mode"] for line in json_lines
    )
    assert any(line["level"] == "trace" for line in json_lines)
    assert any(line.get("logger") == "demo.stdlib" for line in json_lines)
    assert any(line["event"] == "structlog exception" for line in json_lines)
    assert any(line["event"] == "stdlib exception" for line in json_lines)
