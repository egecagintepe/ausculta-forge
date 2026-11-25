"""Tests for Lab Live Recording workflow, provenance separation, and CLI session import."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from pcg_app.app import create_app


def test_lab_record_10s_requires_connected_device(tmp_path: Path) -> None:
    app = create_app(sessions_dir=tmp_path / "sessions")
    client = TestClient(app)

    resp = client.post("/api/lab/record-10s/start", json={"experiment_type": "MIC_DIAGNOSTIC"})
    assert resp.status_code == 400
    assert "not connected" in resp.json()["detail"].lower()


def test_lab_record_10s_simulated_enforces_simulated_provenance(tmp_path: Path) -> None:
    app = create_app(sessions_dir=tmp_path / "sessions")
    with TestClient(app) as client:
        conn = client.post("/api/device/usb/connect", json={"port": "SIMULATED_ESP32_S3"})
        assert conn.status_code == 200

        # Even if operator requests PHYSICAL_PHANTOM on SIMULATED_ESP32_S3, provenance stays SIMULATED
        start = client.post(
            "/api/lab/record-10s/start",
            json={"experiment_type": "PHYSICAL_PHANTOM", "target_samples": 1024, "source_mode": 0},
        )
        assert start.status_code == 200
        body = start.json()
        assert body["experiment_type"] == "SIMULATED"
        assert body["is_simulated"] is True
        sid = body["session_id"]

        # Wait briefly for bounded capture to auto-finalize; fallback to explicit stop if still active
        finalized = False
        for _ in range(40):
            sess_resp = client.get(f"/api/sessions/{sid}")
            if sess_resp.status_code == 200 and sess_resp.json().get("status") == "finalized":
                finalized = True
                break
            time.sleep(0.05)
        if not finalized:
            client.post("/api/lab/record-10s/stop")

        sess = client.get(f"/api/sessions/{sid}").json()
        assert sess["status"] == "finalized"
        assert sess["acquisition_mode"] == "software_simulated"
        assert sess["processing_profile"]["experiment_type"] == "SIMULATED"
        assert sess["processing_profile"]["acquisition_origin"] == "software_simulated"
        assert sess["total_samples"] >= 1024

        client.post("/api/device/usb/disconnect")


def test_lab_cli_sessions_list_and_import(tmp_path: Path) -> None:
    app = create_app(sessions_dir=tmp_path / "sessions")
    client = TestClient(app)

    cli_resp = client.get("/api/lab/cli-sessions")
    assert cli_resp.status_code == 200
    items = cli_resp.json()
    assert isinstance(items, list)
    # Verify our real MIC_DIAGNOSTIC session (if present on disk) can be imported cleanly
    diag = [x for x in items if x["session_id"] == "session_20261125_075205_9923da49"]
    if diag:
        imp = client.post(
            "/api/lab/import-cli-session",
            json={"session_dir": diag[0]["session_dir"], "experiment_type": "MIC_DIAGNOSTIC"},
        )
        assert imp.status_code == 200
        sid = imp.json()["session_id"]
        assert (tmp_path / "sessions" / sid / "raw.wav").is_file()
        verify = client.get(f"/api/sessions/{sid}/verify").json()
        assert verify["is_valid"] is True
        assert verify["wav_samples"] == 480000


def test_guided_coupling_diagnostic_metrics_and_sim_never_passes(tmp_path: Path) -> None:
    app = create_app(sessions_dir=tmp_path / "sessions")
    with TestClient(app) as client:
        conn = client.post("/api/device/usb/connect", json={"port": "SIMULATED_ESP32_S3"})
        assert conn.status_code == 200
        start = client.post(
            "/api/lab/record-10s/start",
            json={"experiment_type": "STETHOSCOPE_COUPLING_DIAGNOSTIC", "target_samples": 1024, "source_mode": 0},
        )
        assert start.status_code == 200
        body = start.json()
        assert body["experiment_type"] == "SIMULATED"
        assert "ack_timestamp_utc" in body
        sid = body["session_id"]

        for _ in range(40):
            sess_resp = client.get(f"/api/sessions/{sid}")
            if sess_resp.status_code == 200 and sess_resp.json().get("status") == "finalized":
                break
            time.sleep(0.05)

        diag = client.get(f"/api/lab/session/{sid}/diagnostic-metrics").json()
        assert diag["is_simulated"] is True
        assert diag["coupling_verified"] is False
        assert len(diag["tap_windows"]) == 3
        client.post("/api/device/usb/disconnect")
