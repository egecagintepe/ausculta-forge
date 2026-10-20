"""Tests for AuscultaForge Desktop Security, Health & Dynamic Authentication."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from pcg_app.app import create_app


def test_health_endpoint():
    """Verify that the health endpoint returns OK without authentication."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "AuscultaForge"


def test_auth_disabled_by_default():
    """When auth_token is None, requests succeed without auth headers."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 200


def test_auth_enabled_rejects_missing_token():
    """When auth_token is set, requests without token are rejected with 403."""
    app = create_app(auth_token="secret_test_token_123")
    client = TestClient(app)

    # Health remains public
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200

    # Status requires token
    unauth_resp = client.get("/api/status")
    assert unauth_resp.status_code == 403
    assert "Unauthorized" in unauth_resp.json()["detail"]


def test_auth_enabled_rejects_invalid_token():
    """When auth_token is set, requests with invalid token are rejected with 403."""
    app = create_app(auth_token="secret_test_token_123")
    client = TestClient(app)

    headers = {"X-AuscultaForge-Auth": "wrong_token"}
    resp = client.get("/api/status", headers=headers)
    assert resp.status_code == 403


def test_auth_enabled_accepts_header_token():
    """Requests with valid X-AuscultaForge-Auth header succeed."""
    token = "secret_test_token_123"
    app = create_app(auth_token=token)
    client = TestClient(app)

    headers = {"X-AuscultaForge-Auth": token}
    resp = client.get("/api/status", headers=headers)
    assert resp.status_code == 200
    assert "capabilities" in resp.json()


def test_auth_enabled_accepts_bearer_token():
    """Requests with valid Authorization: Bearer <token> succeed."""
    token = "secret_test_token_123"
    app = create_app(auth_token=token)
    client = TestClient(app)

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/status", headers=headers)
    assert resp.status_code == 200


def test_websocket_auth_rejection():
    """WebSocket connection without token is closed with code 1008."""
    token = "secret_test_token_123"
    app = create_app(auth_token=token)
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws"):
            pass
    assert excinfo.value.code == 1008


def test_websocket_auth_success():
    """WebSocket connection with valid query token succeeds."""
    token = "secret_test_token_123"
    app = create_app(auth_token=token)
    client = TestClient(app)

    with client.websocket_connect(f"/ws?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "hello"
