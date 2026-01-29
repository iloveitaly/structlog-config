"""Test structlog_config."""

import structlog_config


def test_import() -> None:
    """Test that the  can be imported."""
    assert isinstance(structlog_config.__name__, str)
