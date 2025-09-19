from time import perf_counter
from urllib.parse import quote

import structlog
from fastapi import FastAPI
from python_ipware import IpWare
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match, Mount
from starlette.types import Scope
from starlette.websockets import WebSocket

log = structlog.get_logger("access_log")
ipw = IpWare()


def get_route_name(app: FastAPI, scope: Scope, prefix: str = "") -> str:
    """Generate a descriptive route name for timing metrics"""
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


def get_path_with_query_string(scope: Scope) -> str:
    """Get the URL with the substitution of query parameters.

    Args:
        scope (Scope): Current context.

    Returns:
        str: URL with query parameters
    """
    if "path" not in scope:
        return "-"
    path_with_query_string = quote(scope["path"])
    if raw_query_string := scope["query_string"]:
        query_string = raw_query_string.decode("ascii")
        path_with_query_string = f"{path_with_query_string}?{query_string}"
    return path_with_query_string


def get_client_addr(scope: Scope) -> str:
    """Get the client's address.

    Args:
        scope (Scope): Current context.

    Returns:
        str: Client's address in the IP:PORT format.
    """
    client = scope.get("client")
    if not client:
        return ""
    ip, port = client
    return f"{ip}:{port}"


def client_ip_from_request(request: Request | WebSocket) -> str | None:
    """
    Get the client IP address from the request.

    Headers are not case-sensitive.

    Uses ipware library to properly extract client IP from various proxy headers.
    Fallback to direct client connection if no proxy headers found.
    """
    headers = request.headers
    
    # Use ipware to extract IP from headers
    ip, trusted_route = ipw.get_client_ip(headers)
    if ip:
        log.debug("extracted client IP from headers", ip=ip, trusted_route=trusted_route)
        return str(ip)
    
    # Fallback to direct client connection
    host = getattr(request.client, "host", None) if hasattr(request, "client") and request.client else None
    
    return host


# TODO we should look at the static asset logic and pull the prefix path from tha
def is_static_assets_request(scope: Scope) -> bool:
    """Check if the request is for static assets. Pretty naive check.

    Args:
        scope (Scope): Current context.

    Returns:
        bool: True if the request is for static assets, False otherwise.
    """
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
    app: FastAPI,
) -> None:
    """
    Add better access logging to fastapi:

    >>> from structlog_config import fastapi_access_logger
    >>> fastapi_access_logger.add_middleware(app)

    You'll also want to disable the default uvicorn logs:

    >>> uvicorn.run(..., log_config=None, access_log=False)
    """

    @app.middleware("http")
    async def access_log_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
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
