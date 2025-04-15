import os

from decouple import config

# TODO this should probably be removed and just use the env logger config?
PYTHON_LOG_PATH = config("PYTHON_LOG_PATH", default=None)

PYTHONASYNCIODEBUG = config("PYTHONASYNCIODEBUG", default=False, cast=bool)
"this is a builtin py constant, we check for it to ensure we don't silence this log level"

NO_COLOR = "NO_COLOR" in os.environ
"support NO_COLOR standard https://no-color.org"
