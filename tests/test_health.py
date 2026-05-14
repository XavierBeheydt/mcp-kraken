"""Tests for the /health endpoint.

``GET /health`` must return 200 OK with ``{"status":"ok"}`` regardless of
whether bearer-token auth is enabled — no credentials required.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def http_app(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    from mcp_kraken.config import Settings
    from mcp_kraken.server import build_http_app

    monkeypatch.setenv("KRAKEN_API_KEY", "test")
    monkeypatch.setenv("KRAKEN_API_SECRET", "dGVzdHNlY3JldA==")
    monkeypatch.setenv("MCP_KRAKEN_TOKEN_DB", str(tmp_path / "tokens.db"))
    # auth ON — so we can verify the endpoint bypasses it
    monkeypatch.setenv("MCP_KRAKEN_AUTH_DISABLED", "false")
    return build_http_app(Settings())


def test_health_returns_200(http_app: Any) -> None:
    with TestClient(http_app, raise_server_exceptions=True) as client:
        response = client.get("/health")
    assert response.status_code == 200


def test_health_body_is_json_ok(http_app: Any) -> None:
    with TestClient(http_app, raise_server_exceptions=True) as client:
        response = client.get("/health")
    assert response.headers["content-type"] == "application/json"
    assert json.loads(response.content) == {"status": "ok"}


def test_health_no_auth_required(http_app: Any) -> None:
    """Endpoint must succeed even without an Authorization header."""
    with TestClient(http_app, raise_server_exceptions=True) as client:
        response = client.get("/health", headers={})  # no bearer token
    assert response.status_code == 200
