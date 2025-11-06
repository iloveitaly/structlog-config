import logging
from pathlib import Path
from typing import Any, MutableMapping, TextIO

from structlog.typing import EventDict, ExcInfo

from structlog_config.constants import NO_COLOR


def simplify_activemodel_objects(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Make the following transformations to the logs:

    - Convert keys ('object') whose value inherit from activemodel's BaseModel to object_id=str(object.id)
    - Convert TypeIDs to their string representation object=str(object)

    What's tricky about this method, and other structlog processors, is they are run *after* a response
    is returned to the user. So, they don't error out in tests and it doesn't impact users. They do show up in Sentry.
    """
    from activemodel import BaseModel
    from sqlalchemy.orm.base import object_state
    from typeid import TypeID

    for key, value in list(event_dict.items()):
        if isinstance(value, BaseModel):

            def get_field_no_refresh(instance, field_name):
                """
                This was a hard-won little bit of code: in fastapi, this action happens *after* the
                db session dependency has finished, which means the session is closed.

                If a DB operation within the session causes the model to be marked as stale, then this will trigger
                a `sqlalchemy.orm.exc.DetachedInstanceError` error. This logic pulls the cached value from the object
                which is better for performance *and* avoids the error.
                """
                return str(object_state(instance).dict.get(field_name))

            # TODO this will break as soon as a model doesn't have `id` as pk
            event_dict[f"{key}_id"] = get_field_no_refresh(value, "id")
            del event_dict[key]

        elif isinstance(value, TypeID):
            event_dict[key] = str(value)

    return event_dict


def logger_name(logger: Any, method_name: Any, event_dict: EventDict) -> EventDict:
    """
    structlog does not have named loggers, so we roll our own

    >>> structlog.get_logger(logger_name="my_logger_name")
    """

    if logger_name := event_dict.pop("logger_name", None):
        # `logger` is a special key that structlog treats as the logger name
        # look at `structlog.stdlib.add_logger_name` for more information
        event_dict.setdefault("logger", logger_name)

    return event_dict


def beautiful_traceback_exception_formatter(sio: TextIO, exc_info: ExcInfo) -> None:
    """
    By default, rich and then better-exceptions is used to render exceptions when a ConsoleRenderer is used.

    I prefer beautiful-traceback, so I've added a custom processor to use it.

    https://github.com/hynek/structlog/blob/66e22d261bf493ad2084009ec97c51832fdbb0b9/src/structlog/dev.py#L412
    """

    # only available in dev
    from beautiful_traceback.formatting import exc_to_traceback_str

    _, exc_value, traceback = exc_info
    # TODO support local_stack_only env var support
    formatted_exception = exc_to_traceback_str(exc_value, traceback, color=not NO_COLOR)
    sio.write("\n" + formatted_exception)


# lifted from:
# https://github.com/underyx/structlog-pretty/blob/a6a4abbb1f6e4a879f9f5a95ba067577cea65a08/structlog_pretty/processors.py#L226C1-L252C26
class PathPrettifier:
    """A processor for printing paths.

    Changes all pathlib.Path objects.

    1. Remove PosixPath(...) wrapper by calling str() on the path.
    2. If path is relative to current working directory,
       print it relative to working directory.

    Note that working directory is determined when configuring structlog.
    """

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.cwd()

    def __call__(self, _, __, event_dict):
        for key, path in event_dict.items():
            if not isinstance(path, Path):
                continue
            path = event_dict[key]
            try:
                path = path.relative_to(self.base_dir)
            except ValueError:
                pass  # path is not relative to cwd
            event_dict[key] = str(path)

        return event_dict


# https://github.com/amenezes/structlog_ext_utils/blob/9b4fbd301c891dd55faf4ce3b102c08a5a0f970a/structlog_ext_utils/processors.py#L59
class RenameField:
    """
    A structlog processor that renames fields in the event dictionary.

    This processor allows for renaming keys in the event dictionary during log processing.

    Parameters
    ----------
    fields : dict
        A dictionary mapping original field names (keys) to new field names (values).
        For example, {'old_name': 'new_name'} will rename 'old_name' to 'new_name'.

    Returns
    -------
    callable
        A callable that transforms an event dictionary by renaming specified fields.

    Examples
    --------
    >>> from structlog.processors import TimeStamper
    >>> processors = [
    ...     RenameField({"timestamp": "new_field"}),
    ... ]
    >>> # This will rename "timestamp" field to "New_field" in log events
    """

    def __init__(self, fields: dict) -> None:
        self.fields = fields

    def __call__(self, _, __, event_dict):
        for from_key, to_key in self.fields.items():
            if event_dict.get(from_key):
                event_dict[to_key] = event_dict.pop(from_key)
        return event_dict


class WheneverFormatter:
    """A processor for formatting whenever datetime objects.

    Changes all whenever datetime objects (ZonedDateTime, Instant, PlainDateTime, etc.)
    from their repr() format (e.g., ZonedDateTime("2025-11-02 00:00:00+00:00[UTC]"))
    to their string format (e.g., 2025-11-02 00:00:00+00:00[UTC]).

    This provides cleaner log output without the class wrapper.
    """

    def __call__(self, _, __, event_dict):
        for key, value in event_dict.items():
            # Check if the value has the _pywhenever module attribute
            # This is a reliable way to detect whenever types without importing them
            if hasattr(value, "__module__") and value.__module__.startswith("whenever"):
                event_dict[key] = str(value)

        return event_dict


def add_fastapi_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Take all state added to starlette-context and add to the logs

    https://github.com/tomwojcik/starlette-context/blob/master/example/setup_logging.py
    """
    from starlette_context import context

    if context.exists():
        event_dict.update(context.data)
    return event_dict
