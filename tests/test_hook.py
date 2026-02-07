import sys
import threading
from types import SimpleNamespace

import structlog

from structlog_config.hook import install_exception_hook
from tests.utils import mock_package_not_included


def test_install_exception_hook_sets_global_hook():
    original_hook = sys.excepthook
    try:
        install_exception_hook()
        assert sys.excepthook != original_hook
        assert sys.excepthook.__name__ == "structlog_excepthook"
    finally:
        sys.excepthook = original_hook


def test_hook_logs_exception(capture_logs):
    original_hook = sys.excepthook
    try:
        install_exception_hook(json_logger=False)

        with structlog.testing.capture_logs() as cap_logs:
            try:
                raise ValueError("test error")
            except ValueError:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                sys.excepthook(exc_type, exc_value, exc_traceback)

        assert len(cap_logs) == 1
        log = cap_logs[0]
        assert log["event"] == "uncaught_exception"
        assert "exc_info" in log
        assert log["log_level"] == "error"

    finally:
        sys.excepthook = original_hook


def test_hook_logs_exception_without_beautiful_traceback(capture_logs, monkeypatch):
    mock_package_not_included(monkeypatch, "beautiful_traceback")

    original_hook = sys.excepthook
    try:
        install_exception_hook(json_logger=False)

        with structlog.testing.capture_logs() as cap_logs:
            try:
                raise ValueError("fallback error")
            except ValueError:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                sys.excepthook(exc_type, exc_value, exc_traceback)

        assert len(cap_logs) == 1
        log = cap_logs[0]
        assert log["event"] == "uncaught_exception"
        assert "exc_info" in log
        assert log["log_level"] == "error"

    finally:
        sys.excepthook = original_hook


def test_threading_excepthook_logs_exception(capture_logs):
    original_hook = sys.excepthook
    original_threading_hook = threading.excepthook
    try:
        install_exception_hook(json_logger=False)

        thread = threading.Thread(name="worker-1")
        args = SimpleNamespace(
            exc_type=ValueError,
            exc_value=ValueError("thread error"),
            exc_traceback=None,
            thread=thread,
        )

        with structlog.testing.capture_logs() as cap_logs:
            threading.excepthook(args)

        assert len(cap_logs) == 1
        log = cap_logs[0]
        assert log["event"] == "uncaught_exception"
        assert "exc_info" in log
        assert log["log_level"] == "error"
        assert log["thread"] == {
            "name": "worker-1",
            "id": thread.ident,
            "native_id": getattr(thread, "native_id", None),
            "is_daemon": thread.daemon,
        }

    finally:
        sys.excepthook = original_hook
        threading.excepthook = original_threading_hook
