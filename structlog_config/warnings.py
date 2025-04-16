"""
Warning setup functionality to redirect Python warnings to structlog.
"""

import warnings
from typing import Any, TextIO

import structlog

_original_warnings_showwarning: Any = None

warning_logger = structlog.get_logger(logger_name="py.warnings")


def _showwarning(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> Any:
    """
    Redirects warnings to structlog so they appear in task logs etc.
    """

    warning_logger.warning(
        str(message), category=category.__name__, filename=filename, lineno=lineno
    )


def redirect_showwarnings():
    """
    Redirect Python warnings to use structlog for logging.
    """
    global _original_warnings_showwarning

    if _original_warnings_showwarning is None:
        _original_warnings_showwarning = warnings.showwarning
        # Capture warnings and show them via structlog
        warnings.showwarning = _showwarning
