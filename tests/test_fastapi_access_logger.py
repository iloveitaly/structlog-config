from typing import Any, Dict
from unittest import mock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from structlog_config import configure_logger
from structlog_config.fastapi_access_logger import (
    add_middleware,
    client_ip_from_request,
    get_path_with_query_string,
    get_route_name,
    is_static_assets_request,
)


@pytest.fixture
def test_app():
    """Create a test FastAPI application with our access logger middleware"""
    app = FastAPI(title="Test API")

    # Add our access logger middleware
    add_middleware(app)

    # Add some test routes
    @app.get("/")
    def root():
        return {"message": "Hello World"}

    @app.get("/items/{item_id}")
    def get_item(item_id: int, q: str = None):
        return {"item_id": item_id, "q": q}

    # Add a router to test mounted routes
    router = APIRouter(prefix="/api", tags=["api"])

    @router.get("/users")
    def get_users():
        return [{"name": "Alice"}, {"name": "Bob"}]

    @router.post("/users")
    def create_user(user: Dict[str, Any]):
        return user

    app.include_router(router)

    # Add a route that would be considered a static asset
    @app.get("/static/style.css")
    def get_css():
        return "body { color: red; }"

    return app


@pytest.fixture
def client(test_app):
    """Return a TestClient for the test app"""
    return TestClient(test_app)


def test_access_log_basic_request(client, capsys):
    """Test that basic requests are logged correctly"""
    # Configure logging
    configure_logger()

    # Make a request to the root endpoint
    response = client.get("/")
    assert response.status_code == 200

    # Check the logs
    log_output = capsys.readouterr().out

    # Basic assertions
    assert "200 GET /" in log_output
    assert "method=GET" in log_output
    assert "path=/" in log_output
    assert "status=200" in log_output


def test_access_log_with_params(client, capsys):
    """Test that requests with path and query parameters are logged correctly"""
    configure_logger()

    # Make a request with path and query parameters
    response = client.get("/items/42?q=test")
    assert response.status_code == 200

    # Check the logs
    log_output = capsys.readouterr().out

    # Check that path and query are logged correctly
    assert "200 GET /items/42?q=test" in log_output
    assert "path=/items/42" in log_output
    assert "q=test" in log_output


def test_access_log_router_routes(client, capsys):
    """Test that routes from mounted routers are logged correctly"""
    configure_logger()

    # Test GET endpoint on router
    response = client.get("/api/users")
    assert response.status_code == 200

    log_output = capsys.readouterr().out
    assert "200 GET /api/users" in log_output

    # Test POST endpoint on router
    response = client.post("/api/users", json={"name": "Charlie"})
    assert response.status_code == 200

    log_output = capsys.readouterr().out
    assert "200 POST /api/users" in log_output


def test_access_log_static_assets(client, capsys):
    """Test that static asset requests are logged at debug level"""
    configure_logger()

    # Patch the logger to verify debug vs info level
    with mock.patch("structlog_config.fastapi_access_logger.log") as mock_log:
        # Make a request to a static asset
        response = client.get("/static/style.css")
        assert response.status_code == 200

        # Verify debug was called instead of info
        mock_log.debug.assert_called_once()
        mock_log.info.assert_not_called()


def test_get_route_name(test_app):
    """Test the get_route_name function"""
    # Create a scope for a request to the root endpoint
    scope = {"type": "http", "path": "/", "method": "GET"}

    # Get the route name
    route_name = get_route_name(test_app, scope)

    # Check the result (should be the path for simple routes)
    assert route_name == "tests.test_fastapi_access_logger.root"

    # Test with a mounted route
    scope = {"type": "http", "path": "/api/users", "method": "GET"}
    route_name = get_route_name(test_app, scope)

    # The result should contain the router name
    assert "api" in route_name.lower()


def test_get_path_with_query_string():
    """Test the get_path_with_query_string function"""
    # Test path without query string
    scope = {"path": "/test", "query_string": b""}
    result = get_path_with_query_string(scope)
    assert result == "/test"

    # Test path with query string
    scope = {"path": "/test", "query_string": b"param=value&other=123"}
    result = get_path_with_query_string(scope)
    assert result == "/test?param=value&other=123"


def test_is_static_assets_request():
    """Test the is_static_assets_request function"""
    # Test CSS file
    scope = {"path": "/static/style.css"}
    assert is_static_assets_request(scope) is True

    # Test JS file
    scope = {"path": "/static/script.js"}
    assert is_static_assets_request(scope) is True

    # Test non-static file
    scope = {"path": "/api/data"}
    assert is_static_assets_request(scope) is False


def test_client_ip_from_request():
    """Test the client_ip_from_request function"""
    from unittest.mock import Mock

    # Mock the headers to provide items() method like Starlette headers
    class MockHeaders:
        def __init__(self, headers_dict):
            self._headers = headers_dict

        def items(self):
            return self._headers.items()

    # Test with X-Forwarded-For header
    request = Mock()
    request.headers = MockHeaders({"X-Forwarded-For": "192.168.1.100, 10.0.0.1"})
    request.client = Mock()
    request.client.host = "10.0.0.1"

    result = client_ip_from_request(request)
    assert result == "192.168.1.100"

    # Test with X-Real-IP header
    request = Mock()
    request.headers = MockHeaders({"X-Real-IP": "203.0.113.1"})
    request.client = Mock()
    request.client.host = "10.0.0.1"

    result = client_ip_from_request(request)
    assert result == "203.0.113.1"

    # Test with CF-Connecting-IP header (Cloudflare)
    request = Mock()
    request.headers = MockHeaders({"CF-Connecting-IP": "198.51.100.1"})
    request.client = Mock()
    request.client.host = "10.0.0.1"

    result = client_ip_from_request(request)
    assert result == "198.51.100.1"

    # Test with no proxy headers, fallback to client.host
    request = Mock()
    request.headers = MockHeaders({})
    request.client = Mock()
    request.client.host = "127.0.0.1"

    result = client_ip_from_request(request)
    assert result == "127.0.0.1"

    # Test with no client at all
    request = Mock()
    request.headers = MockHeaders({})
    request.client = None

    result = client_ip_from_request(request)
    assert result is None

    # Test IPv6 address
    request = Mock()
    request.headers = MockHeaders({"X-Forwarded-For": "2001:db8::1"})
    request.client = Mock()
    request.client.host = "127.0.0.1"

    result = client_ip_from_request(request)
    assert result == "2001:db8::1"

    # Test multiple IPs in X-Forwarded-For (should get first one)
    request = Mock()
    request.headers = MockHeaders(
        {"X-Forwarded-For": "203.0.113.1, 198.51.100.1, 192.168.1.1"}
    )
    request.client = Mock()
    request.client.host = "127.0.0.1"

    result = client_ip_from_request(request)
    assert result == "203.0.113.1"

    # Test with WebSocket (should work the same way)
    websocket = Mock()
    websocket.headers = MockHeaders({"X-Real-IP": "192.0.2.1"})
    websocket.client = Mock()
    websocket.client.host = "10.0.0.1"

    result = client_ip_from_request(websocket)
    assert result == "192.0.2.1"

    # Test case-insensitive headers
    request = Mock()
    request.headers = MockHeaders({"x-forwarded-for": "192.168.2.100"})  # lowercase
    request.client = Mock()
    request.client.host = "10.0.0.1"

    result = client_ip_from_request(request)
    assert result == "192.168.2.100"

    # Test header precedence (X-Forwarded-For should take precedence over X-Real-IP)
    request = Mock()
    request.headers = MockHeaders(
        {
            "X-Real-IP": "203.0.113.10",
            "X-Forwarded-For": "203.0.113.20",  # This should win
            "CF-Connecting-IP": "203.0.113.30",
        }
    )
    request.client = Mock()
    request.client.host = "10.0.0.1"

    result = client_ip_from_request(request)
    assert result == "203.0.113.20"

    # Test with Client-IP header (another common header)
    request = Mock()
    request.headers = MockHeaders({"Client-IP": "198.51.100.5"})
    request.client = Mock()
    request.client.host = "10.0.0.1"

    result = client_ip_from_request(request)
    assert result == "198.51.100.5"

    # Test with invalid IP (should fallback to client.host)
    request = Mock()
    request.headers = MockHeaders({"X-Real-IP": "not-a-valid-ip"})
    request.client = Mock()
    request.client.host = "172.16.0.1"

    result = client_ip_from_request(request)
    assert result == "172.16.0.1"

    # Test with empty header value (should fallback to client.host)
    request = Mock()
    request.headers = MockHeaders({"X-Real-IP": ""})
    request.client = Mock()
    request.client.host = "172.16.0.2"

    result = client_ip_from_request(request)
    assert result == "172.16.0.2"
