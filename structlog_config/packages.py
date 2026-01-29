"""
Determine if certain packages are installed to conditionally enable processors
"""

try:
    import orjson  # type: ignore
except ImportError:
    orjson = None

try:
    import sqlalchemy  # type: ignore
except ImportError:
    sqlalchemy = None

try:
    import activemodel  # type: ignore
except ImportError:
    activemodel = None

try:
    import typeid  # type: ignore
except ImportError:
    typeid = None

try:
    import beautiful_traceback  # type: ignore
except ImportError:
    beautiful_traceback = None

try:
    import starlette_context  # type: ignore
except ImportError:
    starlette_context = None

try:
    import whenever  # type: ignore
except ImportError:
    whenever = None
