import logging
import sys

import pytest

from structlog_config import configure_logger, levels
from tests.capture_utils import CaptureStdout
from tests.utils import temp_env_var


@pytest.mark.parametrize(
    ("env_level", "expected"),
    [
        ("DEBUG", True),
        ("TRACE", True),
        ("INFO", False),
    ],
)
def test_is_debug_level(env_level: str, expected: bool) -> None:
    with temp_env_var({"LOG_LEVEL": env_level}):
        configure_logger()
        assert levels.is_debug_level() is expected


def test_is_debug_level_warns_on_notset():
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = root_logger.handlers[:]

    try:
        with CaptureStdout() as capture:
            root_logger.handlers = []
            handler = logging.StreamHandler(sys.stdout)
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.NOTSET)

            with temp_env_var({"LOG_LEVEL": "DEBUG"}):
                assert levels.is_debug_level() is True

            handler.flush()
            assert "logging.NOTSET" in capture.getvalue()
    finally:
        root_logger.setLevel(original_level)
        root_logger.handlers = original_handlers
