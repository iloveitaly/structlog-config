import os

import structlog
from decouple import config

PYTHONASYNCIODEBUG = config("PYTHONASYNCIODEBUG", default=False, cast=bool)
"this is a builtin env var, we check for it to ensure we don't silence this log level"

NO_COLOR = "NO_COLOR" in os.environ
"support NO_COLOR standard https://no-color.org"

package_logger = structlog.get_logger(logger_name=__name__)
"strange name to not be confused with all of the log-related names floating around"

TRACE_LOG_LEVEL = 5
"Custom log level for trace logging, lower than DEBUG"
