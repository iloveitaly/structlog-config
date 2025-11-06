"""
Determine if certain packages are installed to conditionally enable processors
"""

try:
    import orjson
except ImportError:
    orjson = None

try:
    import sqlalchemy
except ImportError:
    sqlalchemy = None

try:
    import activemodel
except ImportError:
    activemodel = None

try:
    import typeid
except ImportError:
    typeid = None

try:
    import pretty_traceback
except ImportError:
    pretty_traceback = None

try:
    import starlette_context
except ImportError:
    starlette_context = None

try:
    import whenever
except ImportError:
    whenever = None
