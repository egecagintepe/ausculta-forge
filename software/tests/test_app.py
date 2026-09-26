"""Tests for AuscultaForge Desktop Application Bridge & WebSocket API.

Verifies:
- REST endpoints (/api/status, /api/sessions, /api/recording, /api/stream)
- WebSocket connection, handshake (hello message), and signal frames
- Control commands over WebSocket (filter preset, pause/resume, start/stop recording)
- Streaming from RealtimeWavSource through the application layer
"""

from pathlib import Path
import time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from pcg_core.models import SampleBlock
from pcg_core.sources import MockPCGSource, RealtimeWavSource
from pcg_app.app import create_app
from pcg_app.protocol import PROTOCOL_VERSION


@pytest.fixture
def test_app_and_dir(tmp_path: Path):
    sessions_dir = tmp_path / "sessions"
    app = create_app(sessions_dir=sessions_dir)
    return app, sessions_dir


def test_status_endpoint(test_app_and_dir):
    app, _ = test_app_and_dir
    with TestClient(app) as client:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "capabilities" in data
        assert "state" in data
        assert data["capabilities"]["sample_rate_hz"] == 4000
        assert data["state"]["is_streaming"] is False
        assert data["state"]["source_type"] == "none"
        assert data["state"]["device_state"] == "absent"


def test_stream_controls_endpoints(test_app_and_dir):
    app, _ = test_app_and_dir
    with TestClient(app) as client:
        # Explicitly select an engineering mock source
        resp_src = client.post("/api/stream/source", json={"source_type": "mock"})
        assert resp_src.status_code == 200
        assert resp_src.json()["source_type"] == "synthetic_dev"
        assert resp_src.json()["is_streaming"] is True

        # Pause
        resp = client.post("/api/stream/pause")
        assert resp.status_code == 200
        assert resp.json()["is_paused"] is True

        # Start / Resume
        resp = client.post("/api/stream/start")
        assert resp.status_code == 200
        assert resp.json()["is_paused"] is False

        # Set Filter
        resp = client.post("/api/stream/filter", json={"preset": "bell"})
        assert resp.status_code == 200
        assert resp.json()["filter_preset"] == "bell"
        assert resp.json()["filter_low_hz"] == 20.0
        assert resp.json()["filter_high_hz"] == 120.0


def test_recording_lifecycle_and_sessions_endpoint(test_app_and_dir):
    app, sessions_dir = test_app_and_dir
    with TestClient(app) as client:
        # Initial sessions list is empty
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

        # Starting recording with no active source must fail with 400
        resp_no_src = client.post("/api/recording/start", json={"source": "test_recording"})
        assert resp_no_src.status_code == 400
        assert "no active stream" in resp_no_src.json()["detail"].lower()

        # Explicitly select mock source for test
        client.post("/api/stream/source", json={"source_type": "mock"})

        # Start recording
        resp = client.post("/api/recording/start", json={"source": "test_recording"})
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        assert sid.startswith("session_")

        # Let the background stream feed blocks for ~0.15s
        time.sleep(0.15)

        # Stop recording
        resp = client.post("/api/recording/stop")
        assert resp.status_code == 200
        meta = resp.json()
        assert meta["session_id"] == sid
        assert meta["total_samples"] > 0
        assert meta["raw_wav_relpath"] == "raw.wav"
        assert meta["acquisition_mode"] == "synthetic_dev"
        assert meta["termination_reason"] == "completed"

        # Verify listed in /api/sessions
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == sid

        # Verify single session get
        resp = client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == sid


def test_websocket_handshake_and_frames(test_app_and_dir):
    app, _ = test_app_and_dir
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # First message must be hello
            hello_msg = ws.receive_json()
            assert hello_msg["type"] == "hello"
            assert hello_msg["version"] == PROTOCOL_VERSION
            assert "capabilities" in hello_msg
            assert "state" in hello_msg

            # Second message is device_state (truthful absent state)
            dev_msg = ws.receive_json()
            assert dev_msg["type"] == "device_state"
            assert dev_msg["device_state"] == "absent"

            # Select synthetic source via WebSocket command
            ws.send_json({"action": "select_source", "source_type": "synthetic_dev"})

            # Receive stream_state or display_frame
            msg = ws.receive_json()
            while msg.get("type") != "display_frame":
                if msg.get("type") == "stream_state":
                    assert msg["source_type"] == "synthetic_dev"
                msg = ws.receive_json()

            assert msg["type"] == "display_frame"
            assert "raw_points" in msg
            assert "filtered_points" in msg
            assert len(msg["raw_points"]) > 0
            assert "metrics" in msg
            assert "rms" in msg["metrics"]
            assert "stream_quality" in msg

            # Test command: set_filter
            ws.send_json({"action": "set_filter", "preset": "diaphragm"})
            state_msg = ws.receive_json()
            while state_msg.get("type") == "display_frame":
                state_msg = ws.receive_json()
            assert state_msg["type"] == "stream_state"
            assert state_msg["filter_preset"] == "diaphragm"


def test_device_api_endpoints_and_protocol_schemas(test_app_and_dir):
    app, _ = test_app_and_dir
    with TestClient(app) as client:
        # GET /api/device/state
        resp_state = client.get("/api/device/state")
        assert resp_state.status_code == 200
        state = resp_state.json()
        assert state["device_state"] == "absent"
        assert state["is_connected"] is False

        # GET /api/device/events
        resp_events = client.get("/api/device/events")
        assert resp_events.status_code == 200
        assert isinstance(resp_events.json(), list)

        # GET /api/device/stats
        resp_stats = client.get("/api/device/stats")
        assert resp_stats.status_code == 200
        stats = resp_stats.json()
        assert "packets_received" in stats
        assert "crc_failures" in stats


def test_streaming_from_realtime_wav_source(test_app_and_dir, tmp_path: Path):
    app, _ = test_app_and_dir
    # Create a small dummy WAV file for testing RealtimeWavSource
    wav_path = tmp_path / "test_stream.wav"
    fs = 4000
    t = np.linspace(0, 1.0, fs, endpoint=False, dtype=np.float32)
    tone = 0.5 * np.sin(2 * np.pi * 100 * t)
    wavfile.write(str(wav_path), fs, (tone * 32767).astype(np.int16))

    with TestClient(app) as client:
        # Select WAV source
        resp = client.post("/api/stream/source", json={"source_type": "realtime_wav", "path": str(wav_path)})
        assert resp.status_code == 200
        assert resp.json()["source_type"] == "realtime_wav"

        with client.websocket_connect("/ws") as ws:
            hello = ws.receive_json()
            assert hello["type"] == "hello"

            frame = ws.receive_json()
            while frame.get("type") in ("device_state", "stream_state"):
                frame = ws.receive_json()
            assert frame["type"] == "display_frame"
            assert len(frame["raw_points"]) > 0
            assert frame["sample_rate_hz"] == fs


def test_session_id_path_traversal_rejected(test_app_and_dir):
    app, _ = test_app_and_dir
    with TestClient(app) as client:
        # Invalid / traversal session ID in GET /api/sessions/{session_id}
        resp = client.get("/api/sessions/..%2Fbad_escape")
        assert resp.status_code in (400, 404)

        resp2 = client.get("/api/sessions/invalid_session@chars!")
        assert resp2.status_code == 400

        # Traversal in replay endpoint
        resp3 = client.post("/api/sessions/..%2Fbad_escape/replay")
        assert resp3.status_code in (400, 404)


def test_cors_and_websocket_origin_security(test_app_and_dir):
    from starlette.websockets import WebSocketDisconnect

    app, _ = test_app_and_dir
    with TestClient(app) as client:
        # 1. Allowed origin receives CORS allow header
        resp_allowed = client.get("/api/status", headers={"Origin": "http://localhost:3000"})
        assert resp_allowed.status_code == 200
        assert resp_allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

        # 2. Unauthorized origin does not receive CORS allow header
        resp_blocked = client.get("/api/status", headers={"Origin": "http://malicious-site.com"})
        assert resp_blocked.status_code == 200
        assert resp_blocked.headers.get("access-control-allow-origin") != "http://malicious-site.com"

        # 3. Allowed origin WebSocket succeeds
        with client.websocket_connect("/ws", headers={"Origin": "http://localhost:3000"}) as ws:
            hello = ws.receive_json()
            assert hello["type"] == "hello"

        # 4. Unauthorized origin WebSocket is rejected with code 1008
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws", headers={"Origin": "http://malicious-site.com"}):
                pass
        assert excinfo.value.code == 1008
