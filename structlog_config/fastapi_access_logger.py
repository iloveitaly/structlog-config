"""
FastAPI access logger module with optional FastAPI dependency.

This module provides structured access logging for FastAPI applications, but 
gracefully handles the case where FastAPI is not installed. All functions will 
work but return safe default values when FastAPI dependencies are not available.

To use this module with FastAPI:
    pip install fastapi starlette python-ipware

Example usage:
    from structlog_config.fastapi_access_logger import add_middleware
    add_middleware(app)

Note: client_ip_from_request is not imported by default in the main package
since FastAPI is not a required dependency. Import it directly from this module
if needed.
"""
from time import perf_counter
from urllib.parse import quote

import structlog

log = structlog.get_logger("access_log")

# Try to import FastAPI dependencies - return early if not available
try:
    from fastapi import FastAPI
    from python_ipware import IpWare
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Match, Mount
    from starlette.types import Scope
    from starlette.websockets import WebSocket
    
    ipw = IpWare()
    _FASTAPI_AVAILABLE = True
except ImportError:
    log.warning(
        "FastAPI dependencies not available. The fastapi_access_logger module will not function properly. "
        "Install FastAPI and related dependencies if you need this functionality."
    )
    _FASTAPI_AVAILABLE = False


def get_route_name(app, scope, prefix: str = "") -> str:
    """Generate a descriptive route name for timing metrics"""
    if not _FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available - cannot use get_route_name function")
        
    if prefix:
        prefix += "."

    route = next(
        (r for r in app.router.routes if r.matches(scope)[0] == Match.FULL), None
    )

    if hasattr(route, "endpoint") and hasattr(route, "name"):
        return f"{prefix}{route.endpoint.__module__}.{route.name}"  # type: ignore
    elif isinstance(route, Mount):
        return f"{type(route.app).__name__}<{route.name!r}>"
    else:
        return scope["path"]


def get_path_with_query_string(scope) -> str:
    """Get the URL with the substitution of query parameters.

    Args:
        scope: Current context.

    Returns:
        str: URL with query parameters
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available - cannot use get_path_with_query_string function")
        
    if "path" not in scope:
        return "-"
    path_with_query_string = quote(scope["path"])
    if raw_query_string := scope["query_string"]:
        query_string = raw_query_string.decode("ascii")
        path_with_query_string = f"{path_with_query_string}?{query_string}"
    return path_with_query_string


def client_ip_from_request(request) -> str | None:
    """
    Get the client IP address from the request.

    Headers are not case-sensitive.

    Uses ipware library to properly extract client IP from various proxy headers.
    Fallback to direct client connection if no proxy headers found.
    
    Note: This function requires FastAPI/Starlette and related dependencies.
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available - cannot use client_ip_from_request function")
        
    headers = request.headers

    # TODO this seems really inefficient, we should just rewrite the ipware into this repo :/
    # Convert Starlette headers to format expected by ipware (HTTP_ prefixed)
    # ipware expects headers in WSGI/Django-style meta format where HTTP headers
    # are prefixed with "HTTP_" and dashes become underscores.
    # See: https://github.com/un33k/python-ipware/blob/main/python_ipware/python_ipware.py#L33-L40
    meta_dict = {}
    for name, value in headers.items():
        # Convert header name to HTTP_ prefixed format
        meta_key = f"HTTP_{name.upper().replace('-', '_')}"
        meta_dict[meta_key] = value

    # Use ipware to extract IP from headers
    ip, trusted_route = ipw.get_client_ip(meta=meta_dict)
    if ip:
        log.debug(
            "extracted client IP from headers", ip=ip, trusted_route=trusted_route
        )
        return str(ip)

    # Fallback to direct client connection
    host = request.client.host if request.client else None

    return host


def is_static_assets_request(scope) -> bool:
    """Check if the request is for static assets. Pretty naive check.

    Args:
        scope: Current context.

    Returns:
        bool: True if the request is for static assets, False otherwise.
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available - cannot use is_static_assets_request function")
        
    return (
        scope["path"].endswith(".css")
        or scope["path"].endswith(".js")
        # .map files are attempted when devtools are enabled
        or scope["path"].endswith(".js.map")
        or scope["path"].endswith(".ico")
        or scope["path"].endswith(".png")
        or scope["path"].endswith(".jpg")
        or scope["path"].endswith(".jpeg")
        or scope["path"].endswith(".gif")
    )


def add_middleware(
    app,
) -> None:
    """
    Add better access logging to fastapi:

    >>> from structlog_config import fastapi_access_logger
    >>> fastapi_access_logger.add_middleware(app)

    You'll also want to disable the default uvicorn logs:

    >>> uvicorn.run(..., log_config=None, access_log=False)
    
    Note: This function requires FastAPI and related dependencies to be installed.
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "Cannot add FastAPI middleware: FastAPI dependencies not available. "
            "Install FastAPI and related dependencies to use this functionality."
        )

    @app.middleware("http")
    async def access_log_middleware(
        request, call_next
    ):
        scope = request.scope
        route_name = get_route_name(app, request.scope)

        # TODO what other request types are there? why do we need this guard?
        if scope["type"] != "http":
            return await call_next(request)

        start = perf_counter()
        response = await call_next(request)

        assert start
        elapsed = perf_counter() - start

        # debug log all asset requests otherwise the logs because unreadable
        log_method = log.debug if is_static_assets_request(scope) else log.info

        log_method(
            f"{response.status_code} {scope['method']} {get_path_with_query_string(scope)}",
            time=round(elapsed * 1000),
            status=response.status_code,
            method=scope["method"],
            path=scope["path"],
            query=scope["query_string"].decode(),
            client_ip=client_ip_from_request(request),
            route=route_name,
        )

        return response
