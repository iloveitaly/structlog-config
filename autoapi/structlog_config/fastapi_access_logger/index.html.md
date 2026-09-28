# structlog_config.fastapi_access_logger

Requires fastapi and is not loaded by default since fastapi is not a default dependency.

## Attributes

| [`log`](#structlog_config.fastapi_access_logger.log)    |    |
|---------------------------------------------------------|----|
| [`ipware`](#structlog_config.fastapi_access_logger.ipware) |    |

## Functions

| [`get_route_name`](#structlog_config.fastapi_access_logger.get_route_name)(→ str)                | Generate a descriptive route name for timing metrics           |
|---------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [`get_path_with_query_string`](#structlog_config.fastapi_access_logger.get_path_with_query_string)(→ str)    | Get the URL with the substitution of query parameters.         |
| [`client_ip_from_request`](#structlog_config.fastapi_access_logger.client_ip_from_request)(→ str | None) | Get the client IP address from the request.                    |
| [`is_static_assets_request`](#structlog_config.fastapi_access_logger.is_static_assets_request)(→ bool)     | Check if the request is for static assets. Pretty naive check. |
| [`add_middleware`](#structlog_config.fastapi_access_logger.add_middleware)(→ None)               | Add better access logging to fastapi:                          |

## Module Contents

### structlog_config.fastapi_access_logger.log

### structlog_config.fastapi_access_logger.ipware

### structlog_config.fastapi_access_logger.get_route_name(app: [fastapi.FastAPI](https://fastapi.tiangolo.com/reference/fastapi/#fastapi.FastAPI), scope: starlette.types.Scope, prefix: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = '') → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

Generate a descriptive route name for timing metrics

### structlog_config.fastapi_access_logger.get_path_with_query_string(scope: starlette.types.Scope) → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

Get the URL with the substitution of query parameters.

* **Parameters:**
  **scope** (*Scope*) – Current context.
* **Returns:**
  URL with query parameters
* **Return type:**
  [str](https://docs.python.org/3/builtins/stdtypes.html#str)

### structlog_config.fastapi_access_logger.client_ip_from_request(request: [starlette.requests.Request](https://fastapi.tiangolo.com/reference/request/#fastapi.Request) | [starlette.websockets.WebSocket](https://fastapi.tiangolo.com/reference/websockets/#fastapi.WebSocket)) → [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)

Get the client IP address from the request.

Uses fastapi-ipware library to properly extract client IP from various proxy headers.
Fallback to direct client connection if no proxy headers found.

### structlog_config.fastapi_access_logger.is_static_assets_request(scope: starlette.types.Scope) → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Check if the request is for static assets. Pretty naive check.

* **Parameters:**
  **scope** (*Scope*) – Current context.
* **Returns:**
  True if the request is for static assets, False otherwise.
* **Return type:**
  [bool](https://docs.python.org/3/builtins/functions.html#bool)

### structlog_config.fastapi_access_logger.add_middleware(app: [fastapi.FastAPI](https://fastapi.tiangolo.com/reference/fastapi/#fastapi.FastAPI)) → [None](https://docs.python.org/3/builtins/constants.html#None)

Add better access logging to fastapi:

```pycon
>>> from structlog_config import fastapi_access_logger
>>> fastapi_access_logger.add_middleware(app)
```

You’ll also want to disable the default uvicorn logs:

```pycon
>>> uvicorn.run(..., log_config=None, access_log=False)
```
