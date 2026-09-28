# Examples

Canonical runnable examples live under [`examples/`](https://github.com/iloveitaly/structlog-config/tree/master/examples) and are included here with `literalinclude` so the docs stay in sync with the scripts.

`just examples` runs the basic example, which exits on its own. The FastAPI scripts start a server, so they are documented here and left out of that recipe.

## Basic logging

Console output, a `TRACE` event, thread-local context, a stdlib logger, and a caught exception:

```{literalinclude} ../examples/basic_example.py
:language: python
```

Run it locally:

```bash
just examples
# or: uv run python examples/basic_example.py
# JSON: uv run python examples/basic_example.py --json
```

## FastAPI exception logging

JSON logging around an intentional unhandled exception. This process stays up and serves `http://localhost:8000/`.

```{literalinclude} ../examples/fastapi_server.py
:language: python
```

```bash
uv run --script examples/fastapi_server.py
```

## FastAPI dependency exceptions

The same server shape, with the exception raised from a dependency instead of the route.

```{literalinclude} ../examples/fastapi_dependency_error.py
:language: python
```

```bash
uv run --script examples/fastapi_dependency_error.py
```
