import sys

import structlog


def install_exception_hook(json_logger: bool = False):
    """
    from structlog-config: Install a sys.excepthook that logs uncaught exceptions using structlog.
    """

    def structlog_excepthook(exc_type, exc_value, exc_traceback):
        # retain original functionality for KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger = structlog.get_logger()

        # We rely on structlog's configuration (configured in __init__.py)
        # to handle the exception formatting based on whether it's JSON or Console mode.
        logger.exception(
            "uncaught_exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = structlog_excepthook
