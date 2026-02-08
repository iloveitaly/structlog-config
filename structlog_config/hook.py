import sys
import threading

import structlog

from .constants import package_logger


def install_exception_hook(json_logger: bool = False):
    """
    from structlog-config: Install a sys.excepthook that logs uncaught exceptions using structlog.
    """

    def _log_uncaught_exception(
        exc_type,
        exc_value,
        exc_traceback,
        thread: threading.Thread | None,
    ) -> None:
        # retain original functionality for KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger = structlog.get_logger()

        logger_kwargs = {}
        if thread is not None:
            logger_kwargs["thread"] = {
                "name": thread.name,
                "id": thread.ident,
                "native_id": getattr(thread, "native_id", None),
                "is_daemon": thread.daemon,
            }

        # We rely on structlog's configuration (configured in __init__.py)
        # to handle the exception formatting based on whether it's JSON or Console mode.
        logger.exception(
            "uncaught_exception",
            exc_info=(exc_type, exc_value, exc_traceback),
            **logger_kwargs,
        )

    def structlog_excepthook(exc_type, exc_value, exc_traceback):
        _log_uncaught_exception(exc_type, exc_value, exc_traceback, thread=None)

    def structlog_threading_excepthook(args):
        _log_uncaught_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            thread=args.thread,
        )

    if sys.excepthook is not sys.__excepthook__:
        package_logger.info(
            "overriding non-default excepthook",
            hook_type="sys",
            existing_hook_type=type(sys.excepthook).__name__,
        )

    if threading.excepthook is not threading.__excepthook__:
        package_logger.info(
            "overriding non-default excepthook",
            hook_type="threading",
            existing_hook_type=type(threading.excepthook).__name__,
        )

    sys.excepthook = structlog_excepthook

    threading.excepthook = structlog_threading_excepthook
