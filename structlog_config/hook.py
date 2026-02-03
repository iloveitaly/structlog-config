import sys

import structlog


def install_exception_hook(json_logger: bool = False):
    def structlog_excepthook(exc_type, exc_value, exc_traceback):
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
