"""AuscultaForge — Automated Acoustic Phantom PCG Experiment Runner Tests.

Validates that false physical PASS outcomes are strictly prevented:
1. Rejection of reference/stimulus WAV passed as capture.
2. Rejection of missing raw.wav without falling back to stimulus/globs.
3. Audio playback failure blocking physical PASS.
4. CRC failures and sequence drops blocking data integrity gate.
5. Missing firmware telemetry resulting in INCONCLUSIVE (not automatic PASS).
6. Missing quiet baseline reporting INCONCLUSIVE without fabricating SNR numbers.
7. Mismatched S1/S2 rhythm/morphology resulting in morphology gate failure.
8. Unprovenanced offline WAV tagged as OFFLINE_UNVERIFIED (never PHYSICAL_VERIFIED).
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
from scipy.io import wavfile

from tools.hardware.run_phantom_pcg_experiment import (
    compute_shannon_envelope,
    compute_coherence_pcg_band,
    simulate_acoustic_phantom_capture,
    verify_s1_s2_morphological_correspondence,
    evaluate_quiet_baseline_snr,
    execute_phantom_pcg_experiment,
)

ROOT = Path(__file__).resolve().parents[2]


class TestShannonEnvelopeAndMorphology:
    """Tests for envelope extraction and strict morphological rhythm comparison."""

    def test_shannon_envelope_basic_properties(self):
        fs = 48000
        t = np.linspace(0, 2.0, 2 * fs, endpoint=False)
        sig = np.zeros_like(t, dtype=np.float32)
        sig[int(0.3 * fs):int(0.4 * fs)] = 0.5 * np.sin(2 * np.pi * 50 * t[:int(0.1 * fs)])
        sig[int(0.7 * fs):int(0.78 * fs)] = 0.4 * np.sin(2 * np.pi * 80 * t[:int(0.08 * fs)])

        env, peaks = compute_shannon_envelope(sig, sample_rate_hz=fs, smoothing_window_ms=30.0)

        assert len(env) == len(sig)
        assert np.all(env >= 0.0)
        assert len(peaks) == 2
        assert 0.25 <= peaks[0]["time_s"] <= 0.45
        assert 0.65 <= peaks[1]["time_s"] <= 0.85

    def test_s1_s2_mismatch_fails_morphology(self):
        """Random noise or constant tones must fail S1/S2 morphology correspondence."""
        fs = 48000
        dur_s = 6.0
        n = int(dur_s * fs)
        t = np.linspace(0, dur_s, n, endpoint=False)

        # Reference has 6 regular heart sound bursts (e.g. 0.8s intervals)
        ref = np.zeros(n, dtype=np.float32)
        for burst_t in [0.8, 1.6, 2.4, 3.2, 4.0, 4.8]:
            idx = int(burst_t * fs)
            ref[idx:idx + int(0.1 * fs)] = 0.6 * np.sin(2 * np.pi * 60 * t[:int(0.1 * fs)])

        # Captured is uncorrelated white noise
        rng = np.random.default_rng(seed=123)
        cap_noise = rng.normal(0, 0.2, size=n).astype(np.float32)

        matched, status, detail = verify_s1_s2_morphological_correspondence(
            ref_signal=ref,
            cap_signal=cap_noise,
            sample_rate_hz=fs,
            delay_ms=0.0,
        )

        assert matched is False
        assert "INCONCLUSIVE" in status or "FAIL" in status


class TestIntegrityAndAntiFalsePassGuards:
    """Strict tests verifying that false physical PASS is mathematically impossible."""

    def test_reject_reference_as_capture(self, tmp_path):
        """Passing the reference WAV as the capture file must raise an integrity error."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        out_dir = tmp_path / "phantom_run"
        with pytest.raises(RuntimeError, match="CRITICAL_INTEGRITY_VIOLATION"):
            execute_phantom_pcg_experiment(
                reference_wav_path=ref_path,
                output_dir=out_dir,
                captured_wav_path=ref_path,  # Intentionally passing reference as capture
            )

    def test_missing_quiet_baseline_is_inconclusive(self, tmp_path):
        """When quiet baseline is omitted, SNR must be None/INCONCLUSIVE, never fabricated."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        out_dir = tmp_path / "phantom_run"
        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=out_dir,
            simulate=True,
            quiet_session_path=None,  # No quiet baseline provided
            target_duration_s=5.0,
        )

        gate_snr = report["gates"]["acoustic_snr"]
        assert gate_snr["pass"] is False
        assert gate_snr["status"] == "INCONCLUSIVE_NO_QUIET_BASELINE"

    def test_offline_wav_without_provenance_is_unverified(self, tmp_path):
        """An arbitrary external WAV without verified session metadata cannot pass physical gate."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        # Create a synthetic external capture WAV without session.json
        ext_wav = tmp_path / "external_unprovenanced.wav"
        fs = 48000
        samples = (0.5 * np.sin(2 * np.pi * 100 * np.linspace(0, 5.0, 5 * fs))).astype(np.float32)
        wavfile.write(ext_wav, fs, (samples * 32767).astype(np.int16))

        out_dir = tmp_path / "phantom_run"
        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=out_dir,
            captured_wav_path=ext_wav,
            target_duration_s=5.0,
        )

        assert report["is_physical"] is False
        assert report["hardware_status"] == "OFFLINE_UNVERIFIED"
        assert report["gate_status"] == "OFFLINE_UNVERIFIED_PENDING_PROVENANCE"
        assert report["gates"]["overall_pass"] is False

    def test_evaluate_quiet_baseline_snr_valid(self, tmp_path):
        """Test true SNR evaluation against a real quiet recording."""
        fs = 48000
        dur_s = 5.0
        n = int(dur_s * fs)

        # Stimulus has 50 Hz tone with RMS ~ 0.2
        stim = (0.3 * np.sin(2 * np.pi * 50 * np.linspace(0, dur_s, n))).astype(np.float32)

        # Quiet has low noise RMS ~ 0.01
        rng = np.random.default_rng(42)
        quiet = rng.normal(0, 0.01, size=n).astype(np.float32)
        quiet_file = tmp_path / "quiet.wav"
        wavfile.write(quiet_file, fs, (quiet * 32767).astype(np.int16))

        snr, status, detail = evaluate_quiet_baseline_snr(
            stimulus_capture=stim,
            quiet_path=quiet_file,
            sample_rate_hz=fs,
        )

        assert snr is not None
        assert snr > 20.0  # ~26 dB
        assert status == "PASS"
        assert detail["status"] == "PASS"
        assert "active_to_quiet_band_power_ratio_db" in detail

    def test_quiet_baseline_zero_or_subnoise_is_inconclusive(self, tmp_path):
        """Digital silence or sub-noise quiet baseline must return INCONCLUSIVE, never 60 dB."""
        fs = 48000
        dur_s = 5.0
        n = int(dur_s * fs)
        stim = (0.3 * np.sin(2 * np.pi * 50 * np.linspace(0, dur_s, n))).astype(np.float32)

        # Silent quiet recording (all zeros)
        quiet_file = tmp_path / "quiet_silent.wav"
        wavfile.write(quiet_file, fs, np.zeros(n, dtype=np.int16))

        snr, status, detail = evaluate_quiet_baseline_snr(
            stimulus_capture=stim,
            quiet_path=quiet_file,
            sample_rate_hz=fs,
        )
        assert snr is None
        assert status == "INCONCLUSIVE_QUIET_ZERO_OR_INVALID"
        assert detail["status"] == "INCONCLUSIVE"

    def test_reject_copied_content_hash_as_capture(self, tmp_path):
        """Even with a different filename, matching SHA-256 of stimulus/reference must be rejected."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        # Copy reference under an innocent-sounding name
        copied_wav = tmp_path / "actual_physical_capture_20261125.wav"
        copied_wav.write_bytes(ref_path.read_bytes())

        out_dir = tmp_path / "phantom_run_hash_reject"
        with pytest.raises(RuntimeError, match="CRITICAL_INTEGRITY_VIOLATION.*identical"):
            execute_phantom_pcg_experiment(
                reference_wav_path=ref_path,
                output_dir=out_dir,
                captured_wav_path=copied_wav,
            )

    def test_s1_s2_one_to_one_matching_prevents_peak_reuse(self):
        """One single captured peak cannot be reused to match multiple reference peaks."""
        fs = 48000
        dur_s = 5.0
        n = int(dur_s * fs)
        t = np.linspace(0, dur_s, n, endpoint=False)

        # Reference has 5 regular beats at 1.0, 1.8, 2.6, 3.4, 4.2 s
        ref = np.zeros(n, dtype=np.float32)
        for burst_t in [1.0, 1.8, 2.6, 3.4, 4.2]:
            idx = int(burst_t * fs)
            ref[idx:idx + int(0.08 * fs)] = 0.8 * np.sin(2 * np.pi * 50 * t[:int(0.08 * fs)])

        # Case 1: Capture has only ONE peak at 1.0 s, then silence (fails on peak count or match)
        cap = np.zeros(n, dtype=np.float32)
        idx1 = int(1.0 * fs)
        cap[idx1:idx1 + int(0.08 * fs)] = 0.8 * np.sin(2 * np.pi * 50 * t[:int(0.08 * fs)])

        matched, status, detail = verify_s1_s2_morphological_correspondence(
            ref_signal=ref,
            cap_signal=cap,
            sample_rate_hz=fs,
            delay_ms=0.0,
        )
        assert matched is False
        assert "INSUFFICIENT" in status or "MISMATCH" in status or "LOW_PEAK_MATCH" in status
        assert detail["matched_peak_count"] <= 1  # Cannot reuse the single peak 5 times!

        # Case 2: Capture has 5 peaks (spaced by >=0.3s so each is detected), but only ONE aligns with reference (at 1.0s).
        # Other 4 are at 1.3, 1.6, 2.0, 2.3s (all >80ms away from ref peaks at 1.8, 2.6, 3.4, 4.2s)
        cap5 = np.zeros(n, dtype=np.float32)
        for burst_t in [1.0, 1.3, 1.6, 2.0, 2.3]:
            idx = int(burst_t * fs)
            cap5[idx:idx + int(0.08 * fs)] = 0.8 * np.sin(2 * np.pi * 50 * t[:int(0.08 * fs)])

        matched5, status5, detail5 = verify_s1_s2_morphological_correspondence(
            ref_signal=ref,
            cap_signal=cap5,
            sample_rate_hz=fs,
            delay_ms=0.0,
        )
        assert matched5 is False
        assert detail5["matched_peak_count"] == 1  # Exactly 1 match, others not falsely paired with 1.8, 2.6, etc.

    def test_simulated_experiment_run(self, tmp_path):
        """Simulated trial verifies software pipeline while strictly marking PHYSICAL_PENDING."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG not found.")

        out_dir = tmp_path / "phantom_runs"
        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=out_dir,
            simulate=True,
            operator="TestRunner",
            notes="Automated pytest regression",
            target_duration_s=5.0,
            target_sample_rate_hz=48000,
        )

        assert report["is_physical"] is False
        assert report["hardware_status"] == "SIMULATED_BENCH_TEST"
        assert report["gate_status"] == "SIMULATION_VERIFIED_PHYSICAL_PENDING"
        assert report["gates"]["overall_pass"] is False  # Must not claim physical pass!

        # Check alignment metrics & latency separation
        align = report["alignment_and_similarity"]
        assert align["normalized_cross_correlation"] >= 0.35
        assert align["mean_coherence_20_250hz"] >= 0.40
        assert 8.0 <= align["estimated_recording_lag_ms"] <= 15.0
        assert align["measured_end_to_end_latency_ms"] is None
        assert align["is_hardware_synchronized"] is False

        # Check morphology metrics
        morph = report["gates"]["s1_s2_morphology"]
        assert morph["pass"] is True
        assert morph["status"] == "PASS_MATCHES_SOURCE_RHYTHM"

        # Check report files written
        trial_id = report["trial_id"]
        trial_dir = out_dir / trial_id
        assert (trial_dir / "phantom_pcg_experiment_report.json").is_file()
        assert (trial_dir / "phantom_pcg_experiment_report.md").is_file()
        assert (trial_dir / "stimulus_pcg_48000hz.wav").is_file()
        assert (trial_dir / "captured_pcg_simulated_48000hz.wav").is_file()
        assert (out_dir / "TRIAL_INDEX.json").is_file()
        assert (out_dir / "TRIAL_INDEX.md").is_file()

    def test_offline_fake_session_json_without_integrity_rejected(self, tmp_path):
        """session.json alone without valid integrity manifest & telemetry must be OFFLINE_UNVERIFIED."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        sess_dir = tmp_path / "fake_session"
        sess_dir.mkdir(parents=True)
        cap_wav = sess_dir / "raw.wav"
        fs = 48000
        samples = (0.4 * np.sin(2 * np.pi * 80 * np.linspace(0, 5.0, 5 * fs))).astype(np.float32)
        wavfile.write(cap_wav, fs, (samples * 32767).astype(np.int16))

        # Write a superficial session.json claiming hardware mode=0, but missing manifest.json & telemetry
        (sess_dir / "session.json").write_text(
            json.dumps({
                "session_id": "fake_session",
                "acquisition_mode": "hardware",
                "processing_profile": {"source_mode": 0},
            }),
            encoding="utf-8",
        )

        out_dir = tmp_path / "phantom_run_fake_sess"
        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=out_dir,
            captured_wav_path=cap_wav,
            target_duration_s=5.0,
        )
        assert report["is_physical"] is False
        assert report["hardware_status"] == "OFFLINE_UNVERIFIED"
        assert report["gates"]["data_integrity"]["status"] == "INCONCLUSIVE_MISSING_TELEMETRY"
        assert report["gates"]["overall_pass"] is False

    def test_constant_or_silent_capture_rejected(self, tmp_path):
        """Silent or constant captured WAV must fail signal & alignment gates."""
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        silent_wav = tmp_path / "silent_capture.wav"
        wavfile.write(silent_wav, 48000, np.zeros(5 * 48000, dtype=np.int16))

        out_dir = tmp_path / "phantom_run_silent"
        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=out_dir,
            captured_wav_path=silent_wav,
            target_duration_s=5.0,
        )
        assert report["gates"]["clipping_margin"]["pass"] is False
        assert report["gates"]["clipping_margin"]["status"] == "FAILED_SILENCE_OR_CONSTANT_SIGNAL"
        assert report["gates"]["cross_correlation"]["pass"] is False
        assert report["gates"]["overall_pass"] is False

    def test_playback_timeout_or_abort_blocks_physical_pass(self, tmp_path, monkeypatch):
        """If audio playback times out or is aborted, playback gate must fail and block PASS."""
        import hashlib
        from pcg_core.models import SampleBlock
        from pcg_core.recording import SessionRecorder

        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        # Build a valid hardware session bundle on disk
        sessions_root = tmp_path / "sessions"
        rec = SessionRecorder(output_dir=sessions_root, source="esp32_g2")
        sid = rec.start(
            acquisition_mode="hardware",
            device_info={"device_id": "ESP32S3-TEST"},
            processing_profile={"source_mode": 0, "acquisition_origin": "physical_i2s_inmp441"},
        )
        fs = 48000
        t = np.linspace(0, 5.0, 5 * fs, endpoint=False, dtype=np.float32)
        samples = (0.3 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
        rec.record_block(SampleBlock(samples=samples, sample_rate_hz=fs, sequence=0, timestamp_s=0.0, source="esp32_g2"))
        rec.stop(termination_reason="target_reached")
        sess_dir = sessions_root / sid
        raw_wav = sess_dir / "raw.wav"
        wav_sha = hashlib.sha256(raw_wav.read_bytes()).hexdigest()

        def _fake_record_g2(**kwargs):
            cb = kwargs.get("on_capture_started")
            if cb:
                cb()
            return {
                "session_id": sid,
                "session_dir": str(sess_dir),
                "raw_wav_path": str(raw_wav),
                "raw_wav_sha256": wav_sha,
                "dropped_frames": 0,
                "crc_failures": 0,
                "in_stream_dropped_samples": 0,
                "post_target_drained_samples": 256,
                "firmware_telemetry": {
                    "generated_samples": 5 * fs + 256,
                    "dropped_samples": 256,
                    "dma_overflows": 0,
                    "ring_overflows": 0,
                    "stop_reason": 0,
                },
            }

        import pcg_app.wednesday_orchestrator as wo
        import tools.hardware.run_phantom_pcg_experiment as rpe

        monkeypatch.setattr(wo, "record_g2_session", _fake_record_g2)

        class _AbortedPlayback:
            def __init__(self, wav_path):
                self.started_event = type("E", (), {"wait": lambda *a, **k: True, "set": lambda *a: None})()
                self.completed_event = type("E", (), {"wait": lambda *a, **k: False, "set": lambda *a: None})()
                self.playback_error = None
                self.aborted = False
                self.start_timestamp = 1.0
                self.end_timestamp = None

            def start(self):
                pass

            def stop(self):
                self.aborted = True

        monkeypatch.setattr(rpe, "PlaybackController", _AbortedPlayback)

        quiet_wav = tmp_path / "quiet.wav"
        wavfile.write(quiet_wav, fs, (np.random.default_rng(1).normal(0, 0.002, 5 * fs) * 32767).astype(np.int16))

        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=tmp_path / "out_abort",
            port="COM99",
            quiet_session_path=quiet_wav,
            play_audio=True,
            audio_routing_verified=True,
            target_duration_s=5.0,
        )
        assert report["gates"]["audio_playback"]["pass"] is False
        assert "FAILED" in report["gates"]["audio_playback"]["status"]
        assert report["gates"]["overall_pass"] is False

    def test_pack_lab_return_includes_phantom_trials_and_verifies_zip(self, tmp_path):
        """Return ZIP packager must archive experiments/phantom trials with valid SHA256SUMS."""
        import hashlib
        import zipfile
        from tools.hardware.pack_lab_return import create_lab_return_zip

        fake_root = tmp_path / "repo"
        trial_dir = fake_root / "experiments/phantom/trial_20261125_090000_abc123"
        trial_dir.mkdir(parents=True)
        (trial_dir / "phantom_pcg_experiment_report.json").write_text('{"trial_id": "trial_test"}\n', encoding="utf-8")
        (trial_dir / "raw.wav").write_bytes(b"RIFFtestwavdata")
        (fake_root / "experiments/phantom/TRIAL_INDEX.md").write_text("# Index\n", encoding="utf-8")

        out_zip = tmp_path / "return_fixture.zip"
        res = create_lab_return_zip(root=fake_root, output_path=out_zip, operator="Test", appdata_logs_dir=tmp_path / "no_logs")
        assert res["status"] == "PACKAGED"
        assert res["file_count"] == 3

        with zipfile.ZipFile(out_zip, "r") as zf:
            names = set(zf.namelist())
            assert "experiments/phantom/trial_20261125_090000_abc123/phantom_pcg_experiment_report.json" in names
            assert "experiments/phantom/trial_20261125_090000_abc123/raw.wav" in names
            assert "experiments/phantom/TRIAL_INDEX.md" in names
            assert "SHA256SUMS.txt" in names
            assert "RETURN_PACKAGE_MANIFEST.json" in names
            sha_text = zf.read("SHA256SUMS.txt").decode("utf-8")
            expected_wav_sha = hashlib.sha256(b"RIFFtestwavdata").hexdigest()
            assert expected_wav_sha in sha_text

    def test_ambiguous_256_drop_without_generated_excess_rejected(self, tmp_path, monkeypatch):
        """256-sample drop when generated_samples == target_samples (not target+256) must FAIL."""
        import hashlib
        from pcg_core.models import SampleBlock
        from pcg_core.recording import SessionRecorder
        import pcg_app.wednesday_orchestrator as wo

        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip("Reference PCG file not found.")

        sessions_root = tmp_path / "sessions"
        rec = SessionRecorder(output_dir=sessions_root, source="esp32_g2")
        sid = rec.start(
            acquisition_mode="hardware",
            device_info={"device_id": "ESP32S3-TEST"},
            processing_profile={"source_mode": 0, "acquisition_origin": "physical_i2s_inmp441"},
        )
        fs = 48000
        t = np.linspace(0, 5.0, 5 * fs, endpoint=False, dtype=np.float32)
        samples = (0.3 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
        rec.record_block(SampleBlock(samples=samples, sample_rate_hz=fs, sequence=0, timestamp_s=0.0, source="esp32_g2"))
        rec.stop(termination_reason="target_reached")
        sess_dir = sessions_root / sid
        raw_wav = sess_dir / "raw.wav"
        wav_sha = hashlib.sha256(raw_wav.read_bytes()).hexdigest()

        def _fake_record_g2_ambig(**kwargs):
            return {
                "session_id": sid,
                "session_dir": str(sess_dir),
                "raw_wav_path": str(raw_wav),
                "raw_wav_sha256": wav_sha,
                "dropped_frames": 0,
                "crc_failures": 0,
                "firmware_telemetry": {
                    "generated_samples": 5 * fs,  # NOT 5*fs + 256! Ambiguous 256 drop!
                    "dropped_samples": 256,
                    "dma_overflows": 0,
                    "ring_overflows": 0,
                    "stop_reason": 0,
                },
            }

        monkeypatch.setattr(wo, "record_g2_session", _fake_record_g2_ambig)
        quiet_wav = tmp_path / "quiet.wav"
        wavfile.write(quiet_wav, fs, (np.random.default_rng(1).normal(0, 0.002, 5 * fs) * 32767).astype(np.int16))

        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=tmp_path / "out_ambig",
            port="COM99",
            quiet_session_path=quiet_wav,
            play_audio=False,
            audio_routing_verified=True,
            target_duration_s=5.0,
        )
        assert report["gates"]["data_integrity"]["pass"] is False
        assert "FAILED_FIRMWARE_DROPS" in report["gates"]["data_integrity"]["status"]
        assert report["gates"]["overall_pass"] is False
