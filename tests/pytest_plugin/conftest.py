"""Shared fixtures for pytest plugin tests."""

import pytest


@pytest.fixture
def plugin_conftest():
    """Conftest content for tests (plugin auto-loads via entry point)."""
    return ""
