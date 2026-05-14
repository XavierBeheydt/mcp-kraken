"""Tests for the ``?apikey=`` → ``Authorization: Bearer`` middleware.

Verifies that the middleware translates a query-string bearer into the
header form FastMCP expects, while leaving requests that already carry
an Authorization header (or no apikey at all) untouched.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send

from mcp_kraken.server import _ApiKeyQueryMiddleware, _extract_apikey


async def _echo_app(scope: Scope, receive: Receive, send: Send) -> None:
    """Minimal ASGI app that echoes the auth header and query string."""
    assert scope["type"] == "http"
    headers = {
        name.decode("latin-1").lower(): value.decode("latin-1")
        for name, value in scope.get("headers", [])
    }
    body = json.dumps(
        {
            "authorization": headers.get("authorization"),
            "query_string": scope["query_string"].decode("latin-1"),
        }
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


@pytest.fixture
def client() -> TestClient:
    return TestClient(_ApiKeyQueryMiddleware(_echo_app))


def test_apikey_param_becomes_bearer_header(client: TestClient) -> None:
    response = client.get("/mcp?apikey=secret123&other=keep")
    body = response.json()
    assert body["authorization"] == "Bearer secret123"
    assert body["query_string"] == "other=keep"


def test_apikey_alone_is_stripped(client: TestClient) -> None:
    response = client.get("/mcp?apikey=secret123")
    body = response.json()
    assert body["authorization"] == "Bearer secret123"
    assert body["query_string"] == ""


def test_existing_auth_header_wins(client: TestClient) -> None:
    response = client.get(
        "/mcp?apikey=ignored",
        headers={"Authorization": "Bearer existing"},
    )
    body = response.json()
    assert body["authorization"] == "Bearer existing"
    # URL is left unchanged when the header is already present
    assert "apikey=ignored" in body["query_string"]


def test_no_apikey_is_passthrough(client: TestClient) -> None:
    response = client.get("/mcp?other=keep")
    body = response.json()
    assert body["authorization"] is None
    assert body["query_string"] == "other=keep"


def test_empty_apikey_is_ignored(client: TestClient) -> None:
    response = client.get("/mcp?apikey=&other=keep")
    body = response.json()
    assert body["authorization"] is None
    # Empty apikey leaves the URL alone — auth will fail downstream as
    # if no credential was supplied.
    assert "other=keep" in body["query_string"]


def test_extract_apikey_unit() -> None:
    token, rest = _extract_apikey(b"foo=1&apikey=abc&bar=2")
    assert token == "abc"
    assert rest == b"foo=1&bar=2"


def test_extract_apikey_absent() -> None:
    token, rest = _extract_apikey(b"foo=1&bar=2")
    assert token is None
    assert rest == b"foo=1&bar=2"


def test_extract_apikey_empty_value() -> None:
    token, rest = _extract_apikey(b"apikey=&foo=1")
    assert token is None
    # Empty value isn't consumed — the original query is returned verbatim
    assert rest == b"apikey=&foo=1"


@pytest.fixture
def http_app(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Full HTTP app with auth enabled, for integration-style checks."""
    from mcp_kraken.config import Settings
    from mcp_kraken.server import build_http_app

    monkeypatch.setenv("KRAKEN_API_KEY", "test")
    monkeypatch.setenv("KRAKEN_API_SECRET", "dGVzdHNlY3JldA==")
    monkeypatch.setenv("MCP_KRAKEN_TOKEN_DB", str(tmp_path / "tokens.db"))
    monkeypatch.setenv("MCP_KRAKEN_AUTH_DISABLED", "false")
    return build_http_app(Settings()), Settings()


def test_mcp_endpoint_accepts_apikey_query(http_app: Any) -> None:
    """A valid token in the URL must satisfy the FastMCP auth layer.

    We don't post a real MCP message — we just need a response that is
    NOT 401, which proves auth passed.
    """
    from mcp_kraken.auth import TokenStore

    app, settings = http_app
    store = TokenStore(settings.token_db)
    issued = store.create(name="apikey-test")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(f"/mcp?apikey={issued.plaintext}", json={})
    assert response.status_code != 401


def test_mcp_endpoint_rejects_invalid_apikey_query(http_app: Any) -> None:
    app, _ = http_app
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/mcp?apikey=mck_nope", json={})
    assert response.status_code == 401


def test_mcp_endpoint_rejects_missing_credential(http_app: Any) -> None:
    app, _ = http_app
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/mcp", json={})
    assert response.status_code == 401
