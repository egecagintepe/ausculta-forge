"""Tests for Scientific Analysis & System Identification REST APIs.

Verifies:
- GET /api/scientific/profiles
- POST /api/scientific/session/{session_id}/analyze
- POST /api/scientific/system-id
- GET /api/scientific/system-id/reports
- GET /api/scientific/system-id/{analysis_id}
- Security and error validation (path traversal, missing IDs, invalid schemas)
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
def scientific_test_app(tmp_path: Path):
    sessions_dir = tmp_path / "sessions"
    assets_dir = tmp_path / "assets"
    analysis_dir = tmp_path / "analysis"

    sessions_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    analysis_service = AnalysisService(
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
        sessions_dir=sessions_dir,
    )

    app = create_app(
        sessions_dir=sessions_dir,
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
        analysis_service=analysis_service,
    )
    return app, sessions_dir, assets_dir, analysis_dir


def _create_mock_session(sessions_dir: Path, session_id: str, fs: int = 4000, duration_s: float = 1.0) -> None:
    sess_folder = sessions_dir / session_id
    sess_folder.mkdir(parents=True, exist_ok=True)

    t = np.linspace(0, duration_s, int(fs * duration_s), endpoint=False)
    # 50 Hz sinusoid (simulating heart sound) + small noise
    sig = 0.5 * np.sin(2 * np.pi * 50.0 * t).astype(np.float32)

    wav_path = sess_folder / "raw.wav"
    wavfile.write(str(wav_path), fs, sig)

    meta = {
        "session_id": session_id,
        "sample_rate_hz": fs,
        "duration_s": duration_s,
        "total_samples": len(sig),
        "total_blocks": len(sig) // 512,
        "started_at_utc": "2026-09-27T00:00:00Z",
        "ended_at_utc": "2026-09-27T00:00:01Z",
        "raw_wav_sha256": "fakehash",
    }
    with open(sess_folder / "session.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)


def _create_mock_reference_asset(assets_dir: Path, asset_id: str, fs: int = 4000, duration_s: float = 1.0) -> None:
    t = np.linspace(0, duration_s, int(fs * duration_s), endpoint=False)
    sig = 0.5 * np.sin(2 * np.pi * 50.0 * t).astype(np.float32)

    wav_path = assets_dir / f"{asset_id}.wav"
    wavfile.write(str(wav_path), fs, sig)

    meta = {
        "asset_id": asset_id,
        "filename": "reference_50hz.wav",
        "sha256": "fake_ref_hash",
        "sample_rate_hz": fs,
        "channels": 1,
        "total_samples": len(sig),
        "duration_s": duration_s,
        "created_at_utc": "2026-09-27T00:00:00Z",
    }
    with open(assets_dir / f"{asset_id}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)


def test_api_list_scientific_profiles(scientific_test_app):
    app, _, _, _ = scientific_test_app
    with TestClient(app) as client:
        resp = client.get("/api/scientific/profiles")
        assert resp.status_code == 200
        profiles = resp.json()
        assert isinstance(profiles, list)
        profile_ids = [p["profile_id"] for p in profiles]
        assert "GENERAL_PCG_V1" in profile_ids
        assert "BROADBAND_SYSTEM_ID_V1" in profile_ids
        assert "RAW_INTEGRITY_V1" in profile_ids


def test_api_analyze_session_scientific_success(scientific_test_app):
    app, sessions_dir, _, _ = scientific_test_app
    session_id = "sess_scientific_001"
    _create_mock_session(sessions_dir, session_id, fs=4000, duration_s=1.5)

    with TestClient(app) as client:
        resp = client.post(
            f"/api/scientific/session/{session_id}/analyze",
            json={"profile_id": "GENERAL_PCG_V1", "welch_nperseg": 512},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["schema_version"] == "1.0.0"
        assert data["session_id"] == session_id
        assert data["sample_rate_hz"] == 4000
        assert data["analysis_profile"] == "GENERAL_PCG_V1"

        # Signal quality assertions
        sq = data["signal_quality"]
        assert sq["sample_count"] == 6000
        assert sq["duration_s"] == 1.5
        assert np.isclose(sq["rms"], 0.5 / np.sqrt(2), atol=0.02)
        assert np.isclose(sq["crest_factor"], np.sqrt(2), atol=0.05)
        assert "zero_crossing_rate" in sq
        assert "zcr_metrology_note" in sq["provenance"]

        # Spectral assertions
        spec = data["spectral"]
        assert "frequencies_hz" in spec
        assert "psd" in spec
        assert "frequency_bin_spacing_hz" in spec
        assert np.isclose(spec["frequency_bin_spacing_hz"], 4000 / 512, atol=0.01)

        # Envelope lab assertions
        env_lab = data["envelope_lab"]
        assert "envelopes" in env_lab
        env_names = list(env_lab["envelopes"].keys())
        assert "hilbert" in env_names
        assert "moving_rms" in env_names
        assert "tkeo" in env_names
        assert "psd_band" in env_names

        # Bounded display payload assertions
        disp = data["display"]
        assert len(disp["time_points_s"]) <= 600
        assert len(disp["raw_signal"]) <= 600
        assert len(disp["analysis_signal"]) <= 600
        assert "psd" in disp
        assert len(disp["psd"]["frequencies_hz"]) <= 256


def test_api_analyze_session_not_found(scientific_test_app):
    app, _, _, _ = scientific_test_app
    with TestClient(app) as client:
        resp = client.post("/api/scientific/session/nonexistent_session/analyze")
        assert resp.status_code == 404


def test_api_analyze_session_path_traversal(scientific_test_app):
    app, _, _, _ = scientific_test_app
    with TestClient(app) as client:
        resp = client.post("/api/scientific/session/.._.._etc/analyze")
        assert resp.status_code == 400


def test_api_system_id_success(scientific_test_app):
    app, sessions_dir, assets_dir, _ = scientific_test_app
    asset_id = "ref_test_001"
    session_id = "sess_sysid_001"

    _create_mock_reference_asset(assets_dir, asset_id, fs=4000, duration_s=1.5)
    _create_mock_session(sessions_dir, session_id, fs=4000, duration_s=1.5)

    with TestClient(app) as client:
        resp = client.post(
            "/api/scientific/system-id",
            json={
                "asset_id": asset_id,
                "session_id": session_id,
                "nperseg": 512,
                "noverlap": 256,
                "window": "hann",
                "excited_band_min_hz": 20.0,
                "excited_band_max_hz": 500.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["schema_version"] == "1.0.0"
        assert "analysis_id" in data
        assert data["reference"]["asset_id"] == asset_id
        assert data["capture"]["session_id"] == session_id

        sys_id = data["system_id"]
        assert "mean_coherence_over_excited_band" in sys_id
        assert "coherence" in sys_id
        assert "h1_magnitude_db" in sys_id
        assert "h1_phase_rad" in sys_id
        assert "excited_frequency_mask" in sys_id
        assert "frequencies_hz" in sys_id

        # Check bounded display
        disp = data["display"]
        assert len(disp["frequency_hz"]) <= 300
        assert len(disp["coherence"]) <= 300
        assert len(disp["h1_magnitude_db"]) <= 300

        # Verify listing and getting report
        analysis_id = data["analysis_id"]
        resp_list = client.get("/api/scientific/system-id/reports")
        assert resp_list.status_code == 200
        rep_list = resp_list.json()
        assert any(r["analysis_id"] == analysis_id for r in rep_list)

        resp_get = client.get(f"/api/scientific/system-id/{analysis_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["analysis_id"] == analysis_id


def test_api_system_id_missing_entities(scientific_test_app):
    app, _, _, _ = scientific_test_app
    with TestClient(app) as client:
        resp = client.post(
            "/api/scientific/system-id",
            json={"asset_id": "nonexistent_asset", "session_id": "nonexistent_session"},
        )
        assert resp.status_code == 404
