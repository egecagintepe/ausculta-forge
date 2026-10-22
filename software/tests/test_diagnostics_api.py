"""Unit tests for Diagnostics REST Endpoints in FastAPI app."""

import pytest
from fastapi.testclient import TestClient

from pcg_app.app import create_app
from pcg_app.diagnostics.flight_recorder import get_flight_recorder


@pytest.fixture
def client(tmp_path):
    app = create_app(sessions_dir=tmp_path / "sessions")
    return TestClient(app)


def test_api_diagnostics_catalog(client: TestClient):
    resp = client.get("/api/diagnostics/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 40
    codes = [item["code"] for item in data]
    assert "AF-USB-001" in codes
    assert "AF-PRT-001" in codes
    assert "AF-SIG-001" in codes


def test_api_diagnostics_events(client: TestClient):
    resp = client.get("/api/diagnostics/events?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_api_diagnostics_active_faults(client: TestClient):
    resp = client.get("/api/diagnostics/active-faults")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_api_diagnostics_correlation(client: TestClient):
    resp = client.get("/api/diagnostics/correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert "case_id" in data
    assert "summary" in data
    assert "ranked_hypotheses" in data
    assert "evidence_demarcation" in data


def test_api_diagnostics_usb_scan(client: TestClient):
    resp = client.get("/api/diagnostics/usb/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_api_diagnostics_fault_inject(client: TestClient):
    resp = client.post("/api/diagnostics/fault/inject", json={"scenario_id": "near_silence"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_fault_code"] == "AF-SIG-001"
    assert data["passed"] is True
    assert data["subsystem"] == "SIGNAL"


def test_api_diagnostics_export_bundle(client: TestClient):
    resp = client.post("/api/diagnostics/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert len(resp.content) > 100  # Non-empty ZIP content
