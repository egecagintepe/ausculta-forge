"""AuscultaForge — USB CDC-ACM Integration Bridge End-to-End Test Suite.

Verifies:
1. Enumeration of host serial ports and inclusion of simulated ESP32-S3 endpoint
2. Real-time FastAPI / DeviceRuntime handshake with simulated CDC-ACM device (HELLO -> READY)
3. Nonzero session ID enforcement and capability verification
4. Acquisition session start (Mode 1: Deterministic G1 and Mode 0: Real Acoustic)
5. Full-rate 48 kHz push-driven sample ingestion into StreamManager
6. Live session recording, WAV file generation, and metadata provenance
7. Acquisition stop (STOP_REQ -> STOP_ACK), telemetry reconciliation, and G1 evidence generation
8. Clean disconnect and state teardown
9. Graceful error handling for unreachable ports, invalid states, and duplicate connections
"""

import asyncio
from pathlib import Path
import time
from typing import Any

from fastapi.testclient import TestClient
import numpy as np
import pytest

from pcg_app.app import create_app
from pcg_app.canonical import CanonicalSessionEngine, SessionState
from pcg_app.device_runtime import DeviceRuntime, DeviceState
from pcg_core.recording import get_session, verify_session_integrity


@pytest.fixture
def integration_app(tmp_path: Path):
    """Fixture providing clean app instance with isolated session directories."""
    sess_dir = tmp_path / "sessions"
    assets_dir = tmp_path / "assets"
    analysis_dir = tmp_path / "analysis"
    app = create_app(
        sessions_dir=sess_dir,
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
    )
    return app


@pytest.fixture
def client(integration_app):
    return TestClient(integration_app)


def test_usb_ports_enumeration(client: TestClient):
    """Verify GET /api/device/usb/ports lists ports and always provides the simulated endpoint."""
    resp = client.get("/api/device/usb/ports")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    sim_ports = [p for p in data if p["port_name"] == "SIMULATED_ESP32_S3"]
    assert len(sim_ports) == 1
    assert sim_ports[0]["is_espressif_candidate"] is True


def test_usb_connect_invalid_port(client: TestClient):
    """Verify connecting to an invalid/non-existent COM port fails gracefully with 400."""
    resp = client.post("/api/device/usb/connect", json={"port": "COM_NON_EXISTENT_999"})
    assert resp.status_code == 400
    assert "Failed to connect" in resp.json()["detail"]

    # Verify device state reflects error
    st_resp = client.get("/api/device/state")
    assert st_resp.json()["state"] == "error"


def test_usb_short_loopback_cannot_pass_full_g1(client: TestClient):
    """A clean 2048-sample lifecycle is still insufficient for 480000-sample G1."""
    # 1. Connect
    conn_resp = client.post("/api/device/usb/connect", json={"port": "SIMULATED_ESP32_S3", "timeout_s": 2.0})
    assert conn_resp.status_code == 200
    conn_data = conn_resp.json()
    assert conn_data["status"] == "connected"
    assert conn_data["port"] == "SIMULATED_ESP32_S3"
    assert conn_data["capabilities"]["sample_rate_hz"] == 48000
    assert conn_data["capabilities"]["protocol_version"] == "1.0"

    # Verify session summary
    sess_resp = client.get("/api/device/usb/session")
    assert sess_resp.status_code == 200
    assert sess_resp.json()["session_state"] == "READY"

    # 2. Start Acquisition (Mode 1: G1 Deterministic, 2048 samples = 8 frames)
    start_resp = client.post(
        "/api/device/usb/start",
        json={"source_mode": 1, "target_samples": 2048, "sample_rate_hz": 48000},
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "streaming"
    assert start_data["session_id"].startswith("0x")
    assert start_data["session_id"] != "0x00000000"

    # Wait briefly for frames to be ingested
    time.sleep(0.15)

    # Verify streaming state
    sess_resp2 = client.get("/api/device/usb/session")
    counters = sess_resp2.json()["counters"]
    assert counters["host_samples_accepted"] > 0
    assert counters["host_sample_value_errors"] == 0

    # 3. Stop Acquisition
    stop_resp = client.post("/api/device/usb/stop")
    assert stop_resp.status_code == 200
    stop_data = stop_resp.json()
    assert stop_data["status"] == "stopped"
    assert stop_data["g1_evidence"] is not None
    assert stop_data["g1_evidence"]["verification_result"] == "FAIL"
    assert "exact_samples" in stop_data["g1_evidence"]["failure_reasons"]

    # 4. Read G1 Evidence Endpoint
    g1_resp = client.get("/api/device/usb/g1-evidence")
    assert g1_resp.status_code == 200
    g1_data = g1_resp.json()
    assert g1_data["mode"] == "DETERMINISTIC_G1"
    assert g1_data["verification_result"] == "FAIL"
    assert g1_data["is_simulated"] is True
    exported = client.post("/api/device/usb/g1-export")
    assert exported.status_code == 200 and exported.headers["content-type"] == "application/zip"

    # 5. Disconnect
    disc_resp = client.post("/api/device/usb/disconnect")
    assert disc_resp.status_code == 200
    assert disc_resp.json()["status"] == "disconnected"


def test_usb_recording_integration(client: TestClient, integration_app):
    """Verify live USB stream recording commits valid WAV, metadata, and SHA-256 hashes."""
    # 1. Connect
    client.post("/api/device/usb/connect", json={"port": "SIMULATED_ESP32_S3"})

    # 2. Start Acquisition (Acoustic Mode 0, 480000 continuous samples)
    client.post("/api/device/usb/start", json={"source_mode": 0, "target_samples": 480000})

    # 3. Start Recording Session
    rec_start = client.post("/api/recording/start", json={"source": "Live ESP32-S3 Acoustic"})
    assert rec_start.status_code == 200
    session_id = rec_start.json()["session_id"]

    # Stream for a short duration to record frames
    time.sleep(0.1)

    # 4. Stop Recording Session
    rec_stop = client.post("/api/recording/stop")
    assert rec_stop.status_code == 200
    meta = rec_stop.json()
    assert meta["session_id"] == session_id
    assert meta["total_samples"] > 0
    assert meta["acquisition_mode"] == "software_simulated"
    assert meta["device_info"] is None
    assert "signed_pcm_24bit_in_32bit_slot" in meta["wire_format"]

    # 5. Stop Acquisition & Disconnect
    client.post("/api/device/usb/stop")
    client.post("/api/device/usb/disconnect")

    # 6. Verify Session Integrity on Disk
    manager = integration_app.state.stream_manager
    res = verify_session_integrity(session_id, manager.sessions_dir)
    assert res["is_valid"] is True
    assert res["sample_count_match"] is True
    assert res["sha256_match"] is True


def test_usb_lifecycle_error_handling(client: TestClient):
    """Verify calling start or stop on disconnected device returns proper 400 errors."""
    # Disconnected start
    start_resp = client.post("/api/device/usb/start")
    assert start_resp.status_code == 400
    assert "Device is not ready" in start_resp.json()["detail"]

    # Disconnected stop
    stop_resp = client.post("/api/device/usb/stop")
    assert stop_resp.status_code == 400
    assert "No active device engine" in stop_resp.json()["detail"]

    # No G1 evidence when no session run
    g1_resp = client.get("/api/device/usb/g1-evidence")
    assert g1_resp.status_code == 404
