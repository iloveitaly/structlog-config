"""Test structlog_config."""

import structlog_config


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(structlog_config.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(structlog_config.__version__, str)

