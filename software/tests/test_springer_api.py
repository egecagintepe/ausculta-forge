"""Tests for Springer LR-HSMM Segmentation REST APIs.

Verifies:
- GET /api/scientific/segmentation/models (lists models including demo reproducibility model)
- POST /api/scientific/segmentation/segment without model (truthful MODEL_REQUIRED state, no fabricated states)
- POST /api/scientific/segmentation/segment with demo model (valid segmentation result & display curves)
- GET /api/scientific/segmentation/reports (lists persisted segmentation reports)
- GET /api/scientific/segmentation/{analysis_id} (retrieves persisted report)
- Security & error validation (path traversal, missing session, invalid profile)
"""

import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from pcg_app.app import create_app
from pcg_app.analysis_service import AnalysisService


@pytest.fixture
def segmentation_test_app(tmp_path: Path):
    sessions_dir = tmp_path / "sessions"
    assets_dir = tmp_path / "assets"
    analysis_dir = tmp_path / "analysis"
    models_dir = tmp_path / "models"

    sessions_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    analysis_service = AnalysisService(
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
        sessions_dir=sessions_dir,
        models_dir=models_dir,
    )

    app = create_app(
        sessions_dir=sessions_dir,
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
        analysis_service=analysis_service,
    )
    return app, sessions_dir, analysis_dir, models_dir


def _create_synthetic_pcg_session(sessions_dir: Path, session_id: str, fs: int = 1000, duration_s: float = 3.0) -> None:
    sess_folder = sessions_dir / session_id
    sess_folder.mkdir(parents=True, exist_ok=True)

    n_samples = int(fs * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    # 1.0 s periodic heart cycle (~60 BPM)
    sig = np.zeros(n_samples, dtype=np.float32)
    cycle_samples = int(fs * 1.0)
    for c_start in range(0, n_samples, cycle_samples):
        # S1 burst
        s1_len = int(0.12 * fs)
        if c_start + s1_len < n_samples:
            sig[c_start : c_start + s1_len] += 0.8 * np.sin(2 * np.pi * 50.0 * np.arange(s1_len) / fs).astype(np.float32)
        # S2 burst (at +0.35 s)
        s2_start = c_start + int(0.35 * fs)
        s2_len = int(0.09 * fs)
        if s2_start + s2_len < n_samples:
            sig[s2_start : s2_start + s2_len] += 0.6 * np.sin(2 * np.pi * 70.0 * np.arange(s2_len) / fs).astype(np.float32)

    wav_path = sess_folder / "raw.wav"
    wavfile.write(str(wav_path), fs, sig)

    meta = {
        "session_id": session_id,
        "sample_rate_hz": fs,
        "duration_s": duration_s,
        "total_samples": n_samples,
        "raw_wav_sha256": "fake_hash_1234",
    }
    with open(sess_folder / "session.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)


def test_list_segmentation_models(segmentation_test_app):
    app, _, _, _ = segmentation_test_app
    client = TestClient(app)

    resp = client.get("/api/scientific/segmentation/models")
    assert resp.status_code == 200
    models = resp.json()
    assert isinstance(models, list)
    assert len(models) >= 1

    # Built-in demo model must always be present and labeled as Demo / Reproducibility Model
    demo = next((m for m in models if m["model_id"] == "springer_demo_3feature_v1"), None)
    assert demo is not None
    assert demo["is_demo"] is True
    assert "Synthetic" in demo["label"] or "Demo" in demo["label"]


def test_segment_session_without_model_returns_model_required(segmentation_test_app):
    """Truthful no-model guard: Without a trained model, do not fabricate states."""
    app, sessions_dir, _, _ = segmentation_test_app
    client = TestClient(app)

    _create_synthetic_pcg_session(sessions_dir, "sess_no_model", duration_s=3.0)

    # Call segmentation with NO model_id
    payload = {
        "session_id": "sess_no_model",
        "model_id": None,
        "profile_id": "SPRINGER_PHYSIONET_REFERENCE_V1",
    }
    resp = client.post("/api/scientific/segmentation/segment", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    seg = data["segmentation"]
    assert seg["status"] == "MODEL_REQUIRED"
    assert seg["state_sequence_50hz"] == []
    assert seg["state_intervals"] == []
    assert len(seg["technical_warnings"]) > 0
    assert "No trained Springer segmentation model" in seg["technical_warnings"][0]


def test_segment_session_with_demo_model_succeeds(segmentation_test_app):
    """Inference with demo model produces valid intervals and display representations."""
    app, sessions_dir, analysis_dir, _ = segmentation_test_app
    client = TestClient(app)

    _create_synthetic_pcg_session(sessions_dir, "sess_demo_seg", duration_s=3.0)

    payload = {
        "session_id": "sess_demo_seg",
        "model_id": "springer_demo_3feature_v1",
        "profile_id": "SPRINGER_PHYSIONET_REFERENCE_V1",
        "max_display_points": 300,
    }
    resp = client.post("/api/scientific/segmentation/segment", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "analysis_id" in data
    assert data["session"]["session_id"] == "sess_demo_seg"

    seg = data["segmentation"]
    assert seg["status"] == "SUCCESS"
    assert seg["model_id"] == "springer_demo_3feature_v1"
    assert seg["heart_rate_estimate_bpm"] is not None
    assert len(seg["state_sequence_50hz"]) > 0
    assert len(seg["state_intervals"]) > 0

    # Verify display curves
    disp = data["display"]
    assert "waveform" in disp
    assert len(disp["waveform"]["time_s"]) <= 300
    assert len(disp["waveform"]["amplitude"]) == len(disp["waveform"]["time_s"])
    assert "feature_traces" in disp
    assert "homomorphic" in disp["feature_traces"]

    # Verify report persistence
    analysis_id = data["analysis_id"]
    get_resp = client.get(f"/api/scientific/segmentation/{analysis_id}")
    assert get_resp.status_code == 200
    persisted = get_resp.json()
    assert persisted["analysis_id"] == analysis_id

    # Verify report listing
    list_resp = client.get("/api/scientific/segmentation/reports")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert len(reports) >= 1
    assert any(r["analysis_id"] == analysis_id for r in reports)


def test_segment_session_error_handling(segmentation_test_app):
    app, sessions_dir, _, _ = segmentation_test_app
    client = TestClient(app)

    # 1. Non-existent session -> 404
    resp = client.post(
        "/api/scientific/segmentation/segment",
        json={"session_id": "non_existent_sess", "model_id": "springer_demo_3feature_v1"},
    )
    assert resp.status_code == 404

    # 2. Path traversal attack -> 400
    resp = client.post(
        "/api/scientific/segmentation/segment",
        json={"session_id": "../../../etc/passwd", "model_id": "springer_demo_3feature_v1"},
    )
    assert resp.status_code == 400

    # 3. Invalid profile ID -> 400
    _create_synthetic_pcg_session(sessions_dir, "sess_invalid_prof", duration_s=3.0)
    resp = client.post(
        "/api/scientific/segmentation/segment",
        json={"session_id": "sess_invalid_prof", "profile_id": "NON_EXISTENT_PROFILE"},
    )
    assert resp.status_code == 400
    assert "Unknown Springer profile" in resp.json()["detail"]
