import importlib

import pytest

import structlog_config.constants as constants
from structlog_config.env import get_env, get_env_bool
from structlog_config.levels import get_environment_log_level_as_string


def test_get_env_returns_default_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_ENV", raising=False)

    assert get_env("MISSING_ENV", "fallback") == "fallback"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", " yes ", "on", "Y"])
def test_get_env_bool_parses_true_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("TEST_BOOL", value)

    assert get_env_bool("TEST_BOOL") is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", " no ", "off", "N"])
def test_get_env_bool_parses_false_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("TEST_BOOL", value)

    assert get_env_bool("TEST_BOOL") is False


def test_get_env_bool_returns_default_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_BOOL", raising=False)

    assert get_env_bool("TEST_BOOL", default=True) is True


def test_get_env_bool_raises_for_invalid_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_BOOL", "sometimes")

    with pytest.raises(ValueError, match="TEST_BOOL"):
        get_env_bool("TEST_BOOL")


def test_constants_pythonasynciodebug_uses_bool_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONASYNCIODEBUG", "true")

    reloaded_constants = importlib.reload(constants)

    assert reloaded_constants.PYTHONASYNCIODEBUG is True

    monkeypatch.delenv("PYTHONASYNCIODEBUG", raising=False)
    importlib.reload(constants)


def test_get_environment_log_level_defaults_for_blank_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "   ")

    assert get_environment_log_level_as_string() == "INFO"
