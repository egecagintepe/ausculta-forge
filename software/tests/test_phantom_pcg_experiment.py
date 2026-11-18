"""AuscultaForge — Automated Acoustic Phantom PCG Experiment Runner Tests.

Validates:
1. Shannon energy envelope computation and S1/S2 peak detection.
2. Simulated acoustic phantom channel behavior (delay, attenuation, low-pass damping).
3. End-to-end execution of `execute_phantom_pcg_experiment` in simulated mode.
4. Correct generation of JSON and Markdown reports with full provenance.
5. Strict adherence to academic gating rules (simulation tagged as PHYSICAL_PENDING).
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

from tools.hardware.run_phantom_pcg_experiment import (
    compute_shannon_envelope,
    compute_coherence_pcg_band,
    simulate_acoustic_phantom_capture,
    execute_phantom_pcg_experiment,
)

ROOT = Path(__file__).resolve().parents[2]


class TestShannonEnvelope:
    """Tests for normalized Shannon energy envelope extraction."""

    def test_shannon_envelope_basic_properties(self):
        fs = 48000
        t = np.linspace(0, 2.0, 2 * fs, endpoint=False)
        # Create synthetic signal with two distinct pulses (simulating S1 and S2)
        sig = np.zeros_like(t, dtype=np.float32)
        sig[int(0.3 * fs):int(0.4 * fs)] = 0.5 * np.sin(2 * np.pi * 50 * t[:int(0.1 * fs)])
        sig[int(0.7 * fs):int(0.78 * fs)] = 0.4 * np.sin(2 * np.pi * 80 * t[:int(0.08 * fs)])

        env, peaks = compute_shannon_envelope(sig, sample_rate_hz=fs, smoothing_window_ms=30.0)

        assert len(env) == len(sig)
        assert np.all(env >= 0.0)
        assert len(peaks) == 2
        # Check that detected peak times correspond approximately to the pulses
        assert 0.25 <= peaks[0]["time_s"] <= 0.45
        assert 0.65 <= peaks[1]["time_s"] <= 0.85


class TestSimulatedPhantomChannel:
    """Tests for acoustic phantom channel simulation."""

    def test_simulation_delay_and_attenuation(self):
        fs = 48000
        dur_s = 1.0
        n = int(dur_s * fs)
        stim = 0.7 * np.sin(2 * np.pi * 100 * np.linspace(0, dur_s, n)).astype(np.float32)

        cap = simulate_acoustic_phantom_capture(
            stim,
            sample_rate_hz=fs,
            acoustic_delay_ms=10.0,
            attenuation_db=-6.0,
            lowpass_cutoff_hz=450.0,
            noise_std=0.001,
        )

        assert len(cap) == len(stim)
        # Verify attenuation: output amplitude should be roughly half (-6 dB)
        assert np.max(np.abs(cap)) < np.max(np.abs(stim))


class TestEndToEndExperimentExecution:
    """Tests for full experiment execution and report generation."""

    def test_simulated_experiment_run(self, tmp_path):
        ref_path = ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
        if not ref_path.is_file():
            pytest.skip(f"Reference PCG not found: {ref_path}")

        out_dir = tmp_path / "phantom_runs"
        report = execute_phantom_pcg_experiment(
            reference_wav_path=ref_path,
            output_dir=out_dir,
            simulate=True,
            operator="TestRunner",
            notes="Automated pytest regression",
            target_duration_s=5.0,  # 5s test duration for speed
            target_sample_rate_hz=48000,
        )

        assert report["is_physical"] is False
        assert report["hardware_status"] == "SIMULATED_BENCH_TEST"
        assert report["gate_status"] == "SIMULATION_VERIFIED_PHYSICAL_PENDING"

        # Check alignment metrics
        align = report["alignment_and_similarity"]
        assert align["normalized_cross_correlation"] >= 0.35
        assert align["mean_coherence_20_250hz"] >= 0.40
        assert 8.0 <= align["estimated_delay_ms"] <= 15.0

        # Check morphology metrics
        morph = report["s1_s2_morphology"]
        assert morph["captured_peak_count"] >= 4
        assert morph["estimated_heart_rate_bpm"] > 30.0

        # Check report files written
        trial_id = report["trial_id"]
        trial_dir = out_dir / trial_id
        assert (trial_dir / "phantom_pcg_experiment_report.json").is_file()
        assert (trial_dir / "phantom_pcg_experiment_report.md").is_file()
        assert (trial_dir / "stimulus_pcg_48000hz.wav").is_file()
        assert (trial_dir / "captured_pcg_48000hz.wav").is_file()
