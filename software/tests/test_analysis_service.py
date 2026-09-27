"""AuscultaForge — Automated Tests for Session Analysis & Reference-vs-Capture Workbench.

Verifies:
- WAV asset import, validation, SHA-256 generation, and metadata extraction
- Corrupt, empty, and stereo audio rejection policies
- Traversal-safe asset and session identifier validation
- Session analysis summary generation with bounded decimated waveforms
- Quantitative reference-vs-capture comparison (identical, delay, gain, noise, differing fs)
- Least-squares gain propagation into result schemas
- Comparison report persistence to disk and reload
- Rejection of absolute system-specific paths in persisted reports
- Bounded size of all UI display series (waveforms, spectra, coherence)
- Full REST API endpoints (assets upload/list/delete, session summary, compare, export)
"""

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re

from fastapi.testclient import TestClient
import numpy as np
import pytest
import scipy.signal
from scipy.io import wavfile

from pcg_core.recording import SessionMetadata
from pcg_app.analysis_service import (
    AnalysisService,
    validate_identifier,
    decimate_aligned_traces_shared_time,
)
from pcg_app.app import create_app


def make_mono_wav_bytes(
    fs: int = 4000,
    duration_s: float = 1.0,
    freq_hz: float = 100.0,
    amplitude: float = 0.5,
) -> bytes:
    """Generate in-memory mono PCM WAV audio bytes."""
    n_samples = int(fs * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False, dtype=np.float32)
    tone = amplitude * np.sin(2 * np.pi * freq_hz * t)
    pcm = (tone * 32767).astype(np.int16)

    buf = io.BytesIO()
    wavfile.write(buf, fs, pcm)
    return buf.getvalue()


def create_recorded_session(
    sessions_dir: Path,
    session_id: str,
    fs: int = 4000,
    duration_s: float = 1.0,
    freq_hz: float = 100.0,
    amplitude: float = 0.5,
    acquisition_mode: str = "hardware_rev_a",
) -> Path:
    """Create a mock recorded session on disk with raw.wav and session.json."""
    sess_dir = sessions_dir / session_id
    sess_dir.mkdir(parents=True, exist_ok=True)

    wav_bytes = make_mono_wav_bytes(fs=fs, duration_s=duration_s, freq_hz=freq_hz, amplitude=amplitude)
    wav_path = sess_dir / "raw.wav"
    with open(wav_path, "wb") as f:
        f.write(wav_bytes)

    wav_hash = hashlib.sha256(wav_bytes).hexdigest()
    n_samples = int(fs * duration_s)

    meta = SessionMetadata(
        session_id=session_id,
        started_at_utc=datetime.now(timezone.utc).isoformat(),
        ended_at_utc=datetime.now(timezone.utc).isoformat(),
        source="hardware",
        sample_rate_hz=fs,
        total_blocks=max(1, n_samples // 512),
        total_samples=n_samples,
        duration_s=duration_s,
        first_sequence=0,
        last_sequence=max(1, n_samples // 512) - 1,
        first_timestamp_s=0.0,
        last_timestamp_s=duration_s,
        raw_wav_relpath="raw.wav",
        raw_wav_sha256=wav_hash,
        stream_quality={
            "total_blocks": max(1, n_samples // 512),
            "dropped_blocks": 0,
            "repeated_sequences": 0,
            "sequence_discontinuities": 0,
            "is_healthy": True,
        },
        git_commit_sha="test_commit_sha",
        environment={"os": "Windows"},
        acquisition_mode=acquisition_mode,
        termination_reason="user_stopped",
        device_info={"device_id": "ESP32S3-HW", "firmware_version": "v1.0"},
    )

    with open(sess_dir / "session.json", "w", encoding="utf-8") as f:
        json.dump(meta.to_dict(), f, indent=2)

    return sess_dir


# =============================================================================
# 1. Reference Asset Management Tests
# =============================================================================

class TestReferenceAssetManagement:
    """Verifies safe WAV import, hash generation, metadata, and asset lifecycle."""

    def test_import_reference_wav_and_metadata(self, tmp_path: Path):
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )
        wav_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.5, freq_hz=80.0)
        expected_hash = hashlib.sha256(wav_bytes).hexdigest()

        meta = service.import_reference_wav(wav_bytes, original_filename="normal_s1_s2.wav")

        assert meta["asset_id"].startswith("ref_")
        assert meta["sha256"] == expected_hash
        assert meta["sample_rate_hz"] == 4000
        assert meta["channels"] == 1
        assert meta["total_samples"] == 6000
        assert meta["duration_s"] == 1.5
        assert meta["filename"] == "normal_s1_s2.wav"

        # Verify persisted files
        wav_file = tmp_path / "assets" / f"{meta['asset_id']}.wav"
        json_file = tmp_path / "assets" / f"{meta['asset_id']}.json"
        assert wav_file.exists()
        assert json_file.exists()

    def test_import_wav_rejects_empty_and_corrupt(self, tmp_path: Path):
        service = AnalysisService(assets_dir=tmp_path / "assets")

        # Empty bytes
        with pytest.raises(ValueError, match="empty or too short"):
            service.import_reference_wav(b"", "empty.wav")

        # Arbitrary junk bytes
        with pytest.raises(ValueError, match="Corrupt or unsupported"):
            service.import_reference_wav(b"RIFFjunkjunkjunkjunkjunkjunkjunkjunkjunkjunk", "junk.wav")

    def test_import_wav_rejects_stereo(self, tmp_path: Path):
        service = AnalysisService(assets_dir=tmp_path / "assets")

        # Create stereo WAV bytes
        fs = 4000
        n_samples = 4000
        t = np.linspace(0, 1.0, n_samples, endpoint=False)
        stereo_data = np.column_stack([
            (0.5 * np.sin(2 * np.pi * 100 * t) * 32767).astype(np.int16),
            (0.5 * np.cos(2 * np.pi * 100 * t) * 32767).astype(np.int16),
        ])
        buf = io.BytesIO()
        wavfile.write(buf, fs, stereo_data)
        stereo_bytes = buf.getvalue()

        with pytest.raises(ValueError, match="Stereo/multichannel audio"):
            service.import_reference_wav(stereo_bytes, "stereo_ref.wav")

    def test_traversal_safe_asset_ids(self, tmp_path: Path):
        service = AnalysisService(assets_dir=tmp_path / "assets")

        # Attempt path traversal
        with pytest.raises(ValueError, match="Invalid asset_id format"):
            service.get_reference_asset("../bad_id")

        with pytest.raises(ValueError, match="Invalid asset_id format"):
            service.delete_reference_asset("..\\bad_id")

        with pytest.raises(ValueError, match="asset_id must be a non-empty string"):
            service.get_reference_asset("")

    def test_asset_listing_and_deletion(self, tmp_path: Path):
        service = AnalysisService(assets_dir=tmp_path / "assets")
        wav1 = make_mono_wav_bytes(fs=4000, duration_s=0.5, freq_hz=70.0)
        wav2 = make_mono_wav_bytes(fs=4000, duration_s=1.0, freq_hz=120.0)

        meta1 = service.import_reference_wav(wav1, "ref1.wav")
        meta2 = service.import_reference_wav(wav2, "ref2.wav")

        assets = service.list_reference_assets()
        assert len(assets) == 2
        ids = [a["asset_id"] for a in assets]
        assert meta1["asset_id"] in ids
        assert meta2["asset_id"] in ids

        # Delete meta1
        deleted = service.delete_reference_asset(meta1["asset_id"])
        assert deleted is True
        assert service.get_reference_asset(meta1["asset_id"]) is None
        assert len(service.list_reference_assets()) == 1


# =============================================================================
# 2. Session Analysis Summary Tests
# =============================================================================

class TestSessionAnalysisSummary:
    """Verifies individual session inspection, filtering, metrics, and bounded waveforms."""

    def test_session_analysis_summary_generation(self, tmp_path: Path):
        sessions_dir = tmp_path / "sessions"
        create_recorded_session(
            sessions_dir=sessions_dir,
            session_id="sess_test_001",
            fs=48000,
            duration_s=2.0,
            freq_hz=75.0,
            amplitude=0.6,
        )

        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=sessions_dir,
        )

        summary = service.get_session_analysis_summary("sess_test_001", max_waveform_points=500)

        assert summary["session_id"] == "sess_test_001"
        assert summary["sample_rate_hz"] == 48000
        assert summary["total_samples"] == 96000
        assert summary["duration_s"] == 2.0
        assert summary["acquisition_mode"] == "hardware_rev_a"
        assert summary["device_info"]["device_id"] == "ESP32S3-HW"

        # Metrics check
        metrics = summary["metrics"]
        assert metrics["raw_rms"] > 0.3
        assert metrics["filtered_rms"] > 0.2
        assert metrics["dominant_frequency_hz"] > 60.0
        assert "fundamental_pcg_20_150hz" in metrics["band_energy_ratios"]

        # Display series bounds check
        display = summary["display"]
        assert len(display["raw_points"]) <= 500
        assert len(display["filtered_points"]) <= 500
        assert len(display["time_points_s"]) == len(display["raw_points"])
        assert len(display["spectrum_frequencies_hz"]) <= 128
        assert len(display["spectrum_power_db"]) == len(display["spectrum_frequencies_hz"])

    def test_session_analysis_summary_rejects_missing_or_invalid(self, tmp_path: Path):
        service = AnalysisService(sessions_dir=tmp_path / "sessions")

        with pytest.raises(ValueError, match="Invalid session_id format"):
            service.get_session_analysis_summary("../traversal_session")

        with pytest.raises(FileNotFoundError, match="Recorded session not found"):
            service.get_session_analysis_summary("non_existent_session")


# =============================================================================
# 3. Quantitative Reference-vs-Capture Comparison Tests
# =============================================================================

class TestReferenceVsCaptureComparison:
    """Verifies signal alignment, metrics, noise tolerance, and report persistence."""

    def test_identical_reference_and_capture_comparison(self, tmp_path: Path):
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        wav_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.0, freq_hz=100.0, amplitude=0.5)
        asset = service.import_reference_wav(wav_bytes, "clean_ref.wav")

        create_recorded_session(
            sessions_dir=tmp_path / "sessions",
            session_id="sess_identical",
            fs=4000,
            duration_s=1.0,
            freq_hz=100.0,
            amplitude=0.5,
        )

        res = service.compare_reference_and_capture(
            asset_id=asset["asset_id"],
            session_id="sess_identical",
            max_waveform_points=400,
        )

        # Objective engineering validation checks
        align = res["alignment"]
        metrics = res["metrics"]

        assert align["delay_samples"] == 0
        assert align["delay_ms"] == 0.0
        assert align["resampled"] is False

        assert metrics["normalized_cross_correlation"] == pytest.approx(1.0, abs=1e-3)
        assert metrics["least_squares_gain"] == pytest.approx(1.0, abs=1e-3)
        assert metrics["rms_gain_ratio"] == pytest.approx(1.0, abs=1e-3)
        assert metrics["rmse"] == pytest.approx(0.0, abs=1e-4)
        assert metrics["nrmse"] == pytest.approx(0.0, abs=1e-4)
        assert metrics["signal_to_error_ratio_db"] >= 90.0  # Perfect reconstruction

        # Display bounds check
        disp = res["display"]
        assert len(disp["aligned_reference"]) <= 400
        assert len(disp["aligned_capture"]) <= 400
        assert len(disp["error"]) <= 400
        assert len(disp["time_ms"]) == len(disp["aligned_reference"])
        assert len(disp["spectrum_frequencies_hz"]) <= 128
        assert len(disp["coherence_frequencies_hz"]) <= 128

    def test_known_artificial_delay_detection(self, tmp_path: Path):
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        fs = 4000
        duration_s = 2.0
        t = np.linspace(0, duration_s, int(fs * duration_s), endpoint=False, dtype=np.float32)
        # Chirp / distinctive multi-frequency signal for sharp cross-correlation
        ref_signal = 0.4 * np.sin(2 * np.pi * 50 * t) + 0.3 * np.sin(2 * np.pi * 150 * t)

        ref_buf = io.BytesIO()
        wavfile.write(ref_buf, fs, (ref_signal * 32767).astype(np.int16))
        asset = service.import_reference_wav(ref_buf.getvalue(), "distinctive_ref.wav")

        # Delay capture by exactly 100 samples (25.0 ms at 4000 Hz)
        delay_samples_known = 100
        cap_signal = np.concatenate([np.zeros(delay_samples_known, dtype=np.float32), ref_signal])

        sess_dir = tmp_path / "sessions" / "sess_delayed"
        sess_dir.mkdir(parents=True, exist_ok=True)
        cap_buf = io.BytesIO()
        wavfile.write(cap_buf, fs, (cap_signal * 32767).astype(np.int16))
        with open(sess_dir / "raw.wav", "wb") as f:
            f.write(cap_buf.getvalue())

        meta = SessionMetadata(
            session_id="sess_delayed",
            started_at_utc=datetime.now(timezone.utc).isoformat(),
            ended_at_utc=datetime.now(timezone.utc).isoformat(),
            source="hardware",
            sample_rate_hz=fs,
            total_blocks=10,
            total_samples=len(cap_signal),
            duration_s=float(len(cap_signal) / fs),
            first_sequence=0,
            last_sequence=9,
            first_timestamp_s=0.0,
            last_timestamp_s=float(len(cap_signal) / fs),
            raw_wav_relpath="raw.wav",
            raw_wav_sha256="",
            stream_quality={},
            git_commit_sha="",
            environment={},
        )
        with open(sess_dir / "session.json", "w", encoding="utf-8") as f:
            json.dump(meta.to_dict(), f)

        res = service.compare_reference_and_capture(asset["asset_id"], "sess_delayed")

        assert res["alignment"]["delay_samples"] == pytest.approx(100, abs=2)
        assert res["alignment"]["delay_ms"] == pytest.approx(25.0, abs=0.6)
        assert res["metrics"]["normalized_cross_correlation"] > 0.98

    def test_known_amplitude_scaling_least_squares_gain(self, tmp_path: Path):
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        ref_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.0, freq_hz=90.0, amplitude=0.8)
        asset = service.import_reference_wav(ref_bytes, "gain_ref.wav")

        # Capture is attenuated to exactly 0.40x
        create_recorded_session(
            sessions_dir=tmp_path / "sessions",
            session_id="sess_scaled",
            fs=4000,
            duration_s=1.0,
            freq_hz=90.0,
            amplitude=0.32,  # 0.32 / 0.8 = 0.40
        )

        res = service.compare_reference_and_capture(asset["asset_id"], "sess_scaled")

        assert res["metrics"]["least_squares_gain"] == pytest.approx(0.40, abs=0.01)
        assert res["metrics"]["gain_ratio_peak"] == pytest.approx(0.40, abs=0.01)
        assert res["metrics"]["gain_ratio_rms"] == pytest.approx(0.40, abs=0.01)
        assert res["metrics"]["normalized_cross_correlation"] == pytest.approx(1.0, abs=1e-3)

    def test_additive_noise_least_squares_vs_rms_gain(self, tmp_path: Path):
        """Validates that under zero-mean noise, least-squares gain remains unbiased while RMS gain ratio increases."""
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        fs = 4000
        duration_s = 2.0
        n_samples = int(fs * duration_s)
        t = np.linspace(0, duration_s, n_samples, endpoint=False, dtype=np.float32)
        clean = 0.4 * np.sin(2 * np.pi * 100 * t)

        ref_buf = io.BytesIO()
        wavfile.write(ref_buf, fs, (clean * 32767).astype(np.int16))
        asset = service.import_reference_wav(ref_buf.getvalue(), "noise_ref.wav")

        # Add zero-mean Gaussian noise to capture
        rng = np.random.RandomState(42)
        noise = rng.normal(0.0, 0.10, size=n_samples).astype(np.float32)
        noisy_cap = clean + noise

        sess_dir = tmp_path / "sessions" / "sess_noisy"
        sess_dir.mkdir(parents=True, exist_ok=True)
        cap_buf = io.BytesIO()
        wavfile.write(cap_buf, fs, (np.clip(noisy_cap, -1.0, 1.0) * 32767).astype(np.int16))
        with open(sess_dir / "raw.wav", "wb") as f:
            f.write(cap_buf.getvalue())

        meta = SessionMetadata(
            session_id="sess_noisy",
            started_at_utc=datetime.now(timezone.utc).isoformat(),
            ended_at_utc=datetime.now(timezone.utc).isoformat(),
            source="hardware",
            sample_rate_hz=fs,
            total_blocks=10,
            total_samples=n_samples,
            duration_s=duration_s,
            first_sequence=0,
            last_sequence=9,
            first_timestamp_s=0.0,
            last_timestamp_s=duration_s,
            raw_wav_relpath="raw.wav",
            raw_wav_sha256="",
            stream_quality={},
            git_commit_sha="",
            environment={},
        )
        with open(sess_dir / "session.json", "w", encoding="utf-8") as f:
            json.dump(meta.to_dict(), f)

        res = service.compare_reference_and_capture(asset["asset_id"], "sess_noisy")

        # Least-squares gain should remain close to 1.0 (unbiased)
        assert res["metrics"]["least_squares_gain"] == pytest.approx(1.0, abs=0.05)
        # RMS gain ratio must be GREATER than 1.0 because noise power adds to RMS
        assert res["metrics"]["rms_gain_ratio"] > 1.02
        # NCC is reduced by noise
        assert 0.85 < res["metrics"]["normalized_cross_correlation"] < 0.99

    def test_differing_sample_rate_resampling(self, tmp_path: Path):
        """Verifies 48 kHz Rev-A capture is automatically resampled to reference sample rate."""
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        # Reference at 4000 Hz
        ref_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.0, freq_hz=100.0, amplitude=0.5)
        asset = service.import_reference_wav(ref_bytes, "ref_4k.wav")

        # Capture at 48,000 Hz Rev-A rate
        create_recorded_session(
            sessions_dir=tmp_path / "sessions",
            session_id="sess_48k_rev_a",
            fs=48000,
            duration_s=1.0,
            freq_hz=100.0,
            amplitude=0.5,
        )

        res = service.compare_reference_and_capture(asset["asset_id"], "sess_48k_rev_a")

        assert res["alignment"]["resampled"] is True
        assert res["alignment"]["effective_sample_rate_hz"] == 4000
        assert res["reference"]["sample_rate_hz"] == 4000
        assert res["capture"]["sample_rate_hz"] == 48000
        assert res["metrics"]["normalized_cross_correlation"] == pytest.approx(1.0, abs=0.02)
        assert res["metrics"]["least_squares_gain"] == pytest.approx(1.0, abs=0.05)

    def test_report_persistence_reload_and_no_absolute_paths(self, tmp_path: Path):
        service = AnalysisService(
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
            sessions_dir=tmp_path / "sessions",
        )

        ref_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.0, freq_hz=80.0)
        asset = service.import_reference_wav(ref_bytes, "persist_ref.wav")
        create_recorded_session(sessions_dir=tmp_path / "sessions", session_id="sess_persist")

        res = service.compare_reference_and_capture(asset["asset_id"], "sess_persist")
        analysis_id = res["analysis_id"]

        # Verify report file exists
        report_file = tmp_path / "analysis" / analysis_id / "comparison.json"
        assert report_file.exists()

        # Reload report via service
        reloaded = service.get_comparison_report(analysis_id)
        assert reloaded is not None
        assert reloaded["analysis_id"] == analysis_id
        assert reloaded["metrics"] == res["metrics"]

        # List reports
        report_list = service.list_comparison_reports()
        assert len(report_list) >= 1
        assert report_list[0]["analysis_id"] == analysis_id

        # Verify NO absolute paths are stored in the persisted JSON file
        raw_text = report_file.read_text(encoding="utf-8")
        assert str(tmp_path) not in raw_text
        assert "C:\\" not in raw_text
        assert "c:\\" not in raw_text

    def test_decimate_aligned_traces_shared_time_narrow_extrema(self):
        """Verifies shared-time decimation preserves narrow extrema from both reference and capture

        at their exact common timestamps, satisfies error[i] == capture[i] - reference[i],
        and remains strictly bounded in point count.
        """
        fs = 4000
        n_samples = 2000
        max_display_points = 200

        # Base signals
        t = np.linspace(0, n_samples / fs, n_samples, endpoint=False, dtype=np.float32)
        ref = 0.1 * np.sin(2 * np.pi * 30 * t)
        cap = 0.1 * np.cos(2 * np.pi * 30 * t)

        # Place distinct narrow extrema inside the SAME bucket (e.g. around sample 500)
        peak_ref_idx = 505
        peak_cap_idx = 525

        ref[peak_ref_idx] = 0.98765   # Distinct positive peak in reference
        cap[peak_cap_idx] = -0.87654  # Distinct negative peak in capture

        t_ms, ref_pts, cap_pts, err_pts = decimate_aligned_traces_shared_time(
            reference=ref,
            capture=cap,
            sample_rate_hz=fs,
            max_display_points=max_display_points,
        )

        # 1. Output size is strictly bounded
        assert len(t_ms) <= max_display_points
        assert len(t_ms) == len(ref_pts) == len(cap_pts) == len(err_pts)
        assert len(t_ms) >= 32

        # 2. Both extrema remain visible in their respective decimated series
        assert max(ref_pts) == pytest.approx(0.98765, abs=1e-4)
        assert min(cap_pts) == pytest.approx(-0.87654, abs=1e-4)

        # 3. Output arrays share exactly the same timestamps
        expected_ref_peak_time_ms = round((peak_ref_idx / fs) * 1000.0, 3)
        expected_cap_peak_time_ms = round((peak_cap_idx / fs) * 1000.0, 3)

        assert expected_ref_peak_time_ms in t_ms
        assert expected_cap_peak_time_ms in t_ms

        ref_peak_i = t_ms.index(expected_ref_peak_time_ms)
        cap_peak_i = t_ms.index(expected_cap_peak_time_ms)

        assert ref_pts[ref_peak_i] == pytest.approx(0.98765, abs=1e-4)
        assert cap_pts[cap_peak_i] == pytest.approx(-0.87654, abs=1e-4)

        # 4. Pointwise error equality: error[i] == capture[i] - reference[i]
        for i in range(len(t_ms)):
            assert err_pts[i] == pytest.approx(cap_pts[i] - ref_pts[i], abs=1e-5)

        # 5. Timestamps are strictly monotonic
        for i in range(len(t_ms) - 1):
            assert t_ms[i] < t_ms[i + 1]


# =============================================================================
# 4. REST API Endpoints Integration Tests
# =============================================================================

class TestAnalysisAPIEndpoints:
    """Verifies FastAPI endpoints for reference upload, listing, comparison, and JSON export."""

    @pytest.fixture
    def test_client_and_service(self, tmp_path: Path):
        assets_dir = tmp_path / "assets"
        analysis_dir = tmp_path / "analysis"
        sessions_dir = tmp_path / "sessions"

        service = AnalysisService(
            assets_dir=assets_dir,
            analysis_dir=analysis_dir,
            sessions_dir=sessions_dir,
        )

        app = create_app(
            sessions_dir=sessions_dir,
            assets_dir=assets_dir,
            analysis_dir=analysis_dir,
            analysis_service=service,
        )

        with TestClient(app) as client:
            yield client, service, sessions_dir

    def test_api_upload_list_and_delete_reference_asset(self, test_client_and_service):
        client, _, _ = test_client_and_service
        wav_bytes = make_mono_wav_bytes(fs=4000, duration_s=0.5, freq_hz=100.0)

        # POST /api/analysis/assets
        resp = client.post(
            "/api/analysis/assets",
            files={"file": ("test_ref.wav", wav_bytes, "audio/wav")},
        )
        assert resp.status_code == 201
        asset = resp.json()
        assert asset["asset_id"].startswith("ref_")
        assert asset["sample_rate_hz"] == 4000

        # GET /api/analysis/assets
        list_resp = client.get("/api/analysis/assets")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        asset_id = asset["asset_id"]

        # GET /api/analysis/assets/{asset_id}
        get_resp = client.get(f"/api/analysis/assets/{asset_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["filename"] == "test_ref.wav"

        # DELETE /api/analysis/assets/{asset_id}
        del_resp = client.delete(f"/api/analysis/assets/{asset_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Verify deletion
        assert client.get(f"/api/analysis/assets/{asset_id}").status_code == 404

    def test_api_session_analysis_summary(self, test_client_and_service):
        client, _, sessions_dir = test_client_and_service
        create_recorded_session(sessions_dir, "sess_api_summary", fs=48000, duration_s=1.0)

        resp = client.get("/api/sessions/sess_api_summary/analysis-summary?max_points=300")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess_api_summary"
        assert len(data["display"]["raw_points"]) <= 300
        assert "metrics" in data
        assert "dominant_frequency_hz" in data["metrics"]

    def test_api_compare_and_export_report(self, test_client_and_service):
        client, service, sessions_dir = test_client_and_service
        wav_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.0, freq_hz=100.0)
        asset = service.import_reference_wav(wav_bytes, "api_ref.wav")
        create_recorded_session(sessions_dir, "sess_api_compare", fs=4000, duration_s=1.0, freq_hz=100.0)

        # POST /api/analysis/compare
        comp_resp = client.post(
            "/api/analysis/compare",
            json={"asset_id": asset["asset_id"], "session_id": "sess_api_compare", "max_points": 400},
        )
        assert comp_resp.status_code == 200
        res = comp_resp.json()
        analysis_id = res["analysis_id"]
        assert res["metrics"]["normalized_cross_correlation"] == pytest.approx(1.0, abs=0.01)

        # GET /api/analysis/{analysis_id}
        get_rep = client.get(f"/api/analysis/{analysis_id}")
        assert get_rep.status_code == 200
        assert get_rep.json()["analysis_id"] == analysis_id

        # GET /api/analysis/{analysis_id}/export
        export_resp = client.get(f"/api/analysis/{analysis_id}/export")
        assert export_resp.status_code == 200
        assert "application/json" in export_resp.headers.get("content-type", "")
        assert "attachment" in export_resp.headers.get("content-disposition", "")
        exported_data = export_resp.json()
        assert exported_data["analysis_id"] == analysis_id
        assert exported_data["version"] == "1.0"

    def test_system_id_cross_rate_resampling_service(self, tmp_path: Path):
        """Regression test for system ID differing sample rates (ref: 4000 Hz, cap: 2000 Hz).

        Verifies:
        - No TypeError during resampling orchestration
        - resampled == True
        - effective/working sample rate == 4000 Hz
        - finite H1 and coherence results
        - persisted system-ID report reloads successfully from disk
        """
        assets_dir = tmp_path / "assets"
        analysis_dir = tmp_path / "analysis"
        sessions_dir = tmp_path / "sessions"

        service = AnalysisService(
            assets_dir=assets_dir,
            analysis_dir=analysis_dir,
            sessions_dir=sessions_dir,
        )

        # Reference WAV = 4000 Hz, 1.5 seconds
        ref_bytes = make_mono_wav_bytes(fs=4000, duration_s=1.5, freq_hz=120.0, amplitude=0.4)
        asset = service.import_reference_wav(ref_bytes, "ref_4000hz.wav")
        asset_id = asset["asset_id"]

        # Capture session WAV = 2000 Hz, 1.5 seconds
        sess_id = "sess_cap_2000hz"
        create_recorded_session(sessions_dir, sess_id, fs=2000, duration_s=1.5, freq_hz=120.0, amplitude=0.4)

        # Execute system ID orchestration
        report = service.run_system_id(asset_id=asset_id, session_id=sess_id)

        # 1. No TypeError and valid analysis_id generated
        assert isinstance(report, dict)
        assert "analysis_id" in report
        analysis_id = report["analysis_id"]

        # 2. Resampled flag is true
        assert report["capture"]["resampled"] is True
        assert report["capture"]["sample_rate_hz"] == 2000
        assert report["reference"]["sample_rate_hz"] == 4000

        # 3. Effective/working sample rate is 4000 Hz
        assert report["capture"]["effective_sample_rate_hz"] == 4000.0
        assert report["system_id"]["sample_rate_hz"] == 4000.0

        # 4. Finite H1/coherence results
        h1_mag_db = report["system_id"]["h1_magnitude_db"]
        coherence = report["system_id"]["coherence"]
        assert len(h1_mag_db) > 0
        assert len(coherence) > 0
        assert np.all(np.isfinite(h1_mag_db))
        assert np.all(np.isfinite(coherence))

        # 5. Persisted result reloads successfully
        reloaded = service.get_system_id_report(analysis_id)
        assert reloaded is not None
        assert reloaded["analysis_id"] == analysis_id
        assert reloaded["capture"]["resampled"] is True
        assert reloaded["system_id"]["sample_rate_hz"] == 4000.0
        assert np.all(np.isfinite(reloaded["system_id"]["h1_magnitude_db"]))
        assert np.all(np.isfinite(reloaded["system_id"]["coherence"]))
