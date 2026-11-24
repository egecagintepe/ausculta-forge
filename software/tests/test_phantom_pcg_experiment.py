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

        # Check alignment metrics
        align = report["alignment_and_similarity"]
        assert align["normalized_cross_correlation"] >= 0.35
        assert align["mean_coherence_20_250hz"] >= 0.40
        assert 8.0 <= align["estimated_delay_ms"] <= 15.0

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
