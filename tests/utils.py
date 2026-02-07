import json
import os
from contextlib import contextmanager
from typing import Dict


@contextmanager
def temp_env_var(env_vars: Dict[str, str]):
    """
    Context manager for temporarily setting environment variables.

    Args:
        env_vars: Dictionary of environment variables to set

    Example:
        with temp_env_var({"LOG_LEVEL": "DEBUG"}):
            # Code that depends on LOG_LEVEL being DEBUG
            ...
    """
    original_values = {}

    # Save original values and set new ones
    for name, value in env_vars.items():
        if name in os.environ:
            original_values[name] = os.environ[name]
        os.environ[name] = value

    try:
        yield
    finally:
        # Restore original values
        for name in env_vars:
            if name in original_values:
                os.environ[name] = original_values[name]
            else:
                del os.environ[name]


def mock_package_not_included(monkeypatch, package_name: str) -> None:
    import structlog_config.packages as packages

    monkeypatch.setattr(packages, package_name, None)


def read_jsonl(text: str) -> list[dict]:
    """Parse multi-line log output as JSONL, returning all parsed objects."""
    return [
        json.loads(line) for line in text.splitlines() if line.strip().startswith("{")
    ]
