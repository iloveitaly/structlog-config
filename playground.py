#!/usr/bin/env -S uv tool run ipython -i

from structlog_config import configure_logger

log = configure_logger()
