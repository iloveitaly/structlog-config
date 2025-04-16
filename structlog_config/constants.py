import logging
import os

from decouple import config

PYTHONASYNCIODEBUG = config("PYTHONASYNCIODEBUG", default=False, cast=bool)
"this is a builtin py constant, we check for it to ensure we don't silence this log level"

NO_COLOR = "NO_COLOR" in os.environ
"support NO_COLOR standard https://no-color.org"

package_logger = logging.getLogger(__name__)
"strange name to not be confused with all of the log-related names floating around"
