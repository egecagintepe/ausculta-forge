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
        assert data["state"]["is_streaming"] is True


def test_stream_controls_endpoints(test_app_and_dir):
    app, _ = test_app_and_dir
    with TestClient(app) as client:
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

            # Next message is a signal_frame from background stream
            frame_msg = ws.receive_json()
            assert frame_msg["type"] == "signal_frame"
            assert "raw_samples" in frame_msg
            assert "filtered_samples" in frame_msg
            assert len(frame_msg["raw_samples"]) > 0
            assert "metrics" in frame_msg
            assert "rms" in frame_msg["metrics"]
            assert "stream_quality" in frame_msg

            # Test command: set_filter
            ws.send_json({"action": "set_filter", "preset": "diaphragm"})
            state_msg = ws.receive_json()
            # Could receive another signal_frame first or stream_state
            while state_msg.get("type") == "signal_frame":
                state_msg = ws.receive_json()
            assert state_msg["type"] == "stream_state"
            assert state_msg["filter_preset"] == "diaphragm"


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
            assert frame["type"] == "signal_frame"
            assert len(frame["raw_samples"]) > 0
            assert frame["sample_rate_hz"] == fs
