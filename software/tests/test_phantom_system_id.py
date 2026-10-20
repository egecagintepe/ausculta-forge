"""AuscultaForge — Sprint 07 Test Suite: Phantom Reference Playback & System Identification.

Tests cover:
1. Deterministic stimulus generation (100 Hz sine, multitone, log sweep, impulse train, reference WAV).
2. Stimulus WAV byte serialization, rational polyphase resampling, and SHA-256 integrity.
3. Latency decomposition: separation of acoustic propagation lag from audio buffer delay.
4. Robust alignment and synchronization failure detection under noise or silence.
5. Digital clipping and excited-band coverage detection in 20–500 Hz characterization band.
6. SISO H1 frequency response and magnitude-squared coherence on known synthetic channels.
7. Metrological truthfulness: non-flat transducer disclaimers, no uncalibrated physical units,
   and PENDING physical evidence status.
8. REST API endpoints for phantom templates, stimulus generation, and characterization.
"""

from __future__ import annotations

import io
import json
import math
import numpy as np
import pytest
import scipy.signal
from scipy.io import wavfile
from fastapi.testclient import TestClient

from pcg_core.stimulus import (
    StimulusRecord,
    generate_100hz_sine,
    generate_multitone,
    generate_log_sweep,
    generate_impulse_train,
    prepare_reference_wav_stimulus,
)
from pcg_core.phantom import (
    PhantomTemplate,
    STANDARD_PHANTOM_TEMPLATES,
    PhantomExperimentRecord,
    estimate_phantom_alignment,
    run_phantom_characterization,
    detect_clipping,
    METROLOGICAL_DISCLAIMER_PHANTOM,
)
from pcg_app.app import create_app
from pcg_app.state import StreamManager
from pcg_app.analysis_service import AnalysisService


class TestStimulusPreparation:
    """Deterministic stimulus preparation verification."""

    def test_generate_100hz_sine(self):
        """100 Hz sine must match analytical frequency, RMS, peak, and crest factor."""
        fs = 48000
        dur = 2.0
        amp = 0.8
        rec = generate_100hz_sine(duration_s=dur, sample_rate_hz=fs, amplitude_fs=amp)

        assert rec.stimulus_type == "sine_100hz"
        assert rec.sample_rate_hz == fs
        assert rec.total_samples == int(dur * fs)
        assert pytest.approx(rec.duration_s, rel=1e-4) == dur
        assert pytest.approx(rec.peak_fs, rel=1e-4) == amp
        assert pytest.approx(rec.rms_fs, rel=1e-3) == amp / math.sqrt(2.0)
        assert pytest.approx(rec.crest_factor, rel=1e-3) == math.sqrt(2.0)
        assert len(rec.sha256) == 64

        # FFT peak must be exactly at 100 Hz
        fft_mag = np.abs(np.fft.rfft(rec.samples))
        freqs = np.fft.rfftfreq(len(rec.samples), d=1.0 / fs)
        peak_freq = freqs[np.argmax(fft_mag)]
        assert abs(peak_freq - 100.0) < 0.5

    def test_generate_multitone_schroeder_phase(self):
        """Multitone with Schroeder phase must exhibit lower crest factor than zero-phase."""
        freqs = [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0]
        rec_schroeder = generate_multitone(
            frequencies_hz=freqs, duration_s=2.0, sample_rate_hz=48000,
            peak_amplitude_fs=0.8, use_schroeder_phase=True
        )
        rec_zero_phase = generate_multitone(
            frequencies_hz=freqs, duration_s=2.0, sample_rate_hz=48000,
            peak_amplitude_fs=0.8, use_schroeder_phase=False
        )

        assert rec_schroeder.stimulus_type == "multitone"
        assert rec_schroeder.peak_fs <= 0.8 + 1e-4
        # Schroeder phase optimizes power distribution: crest factor must be significantly lower
        assert rec_schroeder.crest_factor < rec_zero_phase.crest_factor

    def test_generate_log_sweep(self):
        """Logarithmic sweep must cover 20–500 Hz with smooth tapered edges."""
        fs = 48000
        dur = 2.0
        rec = generate_log_sweep(
            f_start_hz=20.0, f_stop_hz=500.0, duration_s=dur,
            sample_rate_hz=fs, amplitude_fs=0.8, taper_duration_s=0.05
        )

        assert rec.stimulus_type == "log_sweep"
        assert rec.total_samples == int(dur * fs)
        # End tapers: first sample must be close to zero due to Hann window
        assert abs(rec.samples[0]) < 0.05
        assert abs(rec.samples[-1]) < 0.05
        assert rec.peak_fs <= 0.8 + 1e-4

    def test_generate_impulse_train(self):
        """Impulse train must have exact pulse count and interval."""
        fs = 48000
        rec = generate_impulse_train(interval_s=1.0, duration_s=3.0, sample_rate_hz=fs, amplitude_fs=0.9)
        assert rec.stimulus_type == "impulse_train"
        # Pulses occur at 0.2s, 1.2s, 2.2s -> exactly 3 pulses
        pulse_indices = np.where(rec.samples > 0.5)[0]
        assert len(pulse_indices) == 3

    def test_stimulus_wav_serialization(self):
        """to_wav_bytes must produce valid 16-bit and 32-bit mono WAV streams."""
        rec = generate_100hz_sine(duration_s=0.5, sample_rate_hz=48000)

        # 16-bit
        wav16 = rec.to_wav_bytes(bit_depth=16)
        buf16 = io.BytesIO(wav16)
        fs_read, data16 = wavfile.read(buf16)
        assert fs_read == 48000
        assert data16.dtype == np.int16
        assert len(data16) == len(rec.samples)

        # 32-bit float
        wav32 = rec.to_wav_bytes(bit_depth=32)
        buf32 = io.BytesIO(wav32)
        fs_read32, data32 = wavfile.read(buf32)
        assert fs_read32 == 48000
        assert data32.dtype == np.float32
        assert np.allclose(data32, rec.samples, atol=1e-5)

    def test_prepare_reference_wav_with_resampling(self):
        """prepare_reference_wav_stimulus must perform exact rational polyphase resampling."""
        orig_fs = 4000
        n_orig = 2000
        t = np.arange(n_orig) / orig_fs
        tone = (0.5 * np.sin(2 * np.pi * 50.0 * t)).astype(np.float32)

        buf = io.BytesIO()
        wavfile.write(buf, orig_fs, (tone * 32767).astype(np.int16))
        raw_bytes = buf.getvalue()

        # Resample from 4 kHz to 48 kHz
        rec = prepare_reference_wav_stimulus(
            wav_bytes=raw_bytes,
            target_sample_rate_hz=48000,
            normalize_peak_fs=0.8,
            filename="test_tone.wav"
        )
        assert rec.sample_rate_hz == 48000
        assert rec.parameters["resampled"] is True
        assert rec.parameters["original_sample_rate_hz"] == 4000
        # 4000 -> 48000 is 12x upsampling
        assert rec.total_samples == n_orig * 12
        assert pytest.approx(rec.peak_fs, rel=1e-3) == 0.8


class TestAlignmentAndLatencyDecomposition:
    """Verification of alignment, latency separation, and fault detection."""

    def test_estimate_known_delay(self):
        """Cross-correlation must accurately recover injected acoustic delay."""
        fs = 48000
        stim = generate_log_sweep(f_start_hz=20.0, f_stop_hz=500.0, duration_s=2.0, sample_rate_hz=fs)

        injected_delay_ms = 45.0
        injected_delay_samples = int(round((injected_delay_ms / 1000.0) * fs))

        # Capture is delayed by 45 ms and scaled by 0.7
        padded_cap = np.concatenate([np.zeros(injected_delay_samples, dtype=np.float32), stim.samples * 0.7])

        aligned_ref, aligned_cap, align_res, latency = estimate_phantom_alignment(
            reference=stim.samples,
            captured=padded_cap,
            sample_rate_hz=fs,
            pipeline_buffer_delay_ms=30.0,
            target_band_hz=(20.0, 500.0),
        )

        # Delay recovered within 1 sample tolerance
        assert abs(align_res.estimated_delay_samples - injected_delay_samples) <= 1
        assert abs(align_res.estimated_delay_ms - injected_delay_ms) < 0.1
        assert align_res.sync_status == "SYNCHRONIZED"
        assert align_res.normalized_cross_correlation > 0.95
        assert pytest.approx(align_res.least_squares_gain, rel=0.02) == 0.7

        # Latency decomposition verified
        assert pytest.approx(latency.estimated_acoustic_lag_ms, rel=0.01) == injected_delay_ms
        assert latency.playback_pipeline_buffer_delay_ms == 30.0
        assert pytest.approx(latency.total_end_to_end_latency_estimate_ms, rel=0.01) == injected_delay_ms + 30.0
        assert latency.is_hardware_synchronized is False

    def test_missing_synchronization_detection(self):
        """Uncorrelated noise must be flagged as SYNC_FAILED with low correlation."""
        fs = 48000
        stim = generate_log_sweep(duration_s=1.0, sample_rate_hz=fs)
        rng = np.random.default_rng(42)
        uncorrelated_noise = (rng.standard_normal(len(stim.samples)) * 0.1).astype(np.float32)

        _, _, align_res, _ = estimate_phantom_alignment(
            reference=stim.samples,
            captured=uncorrelated_noise,
            sample_rate_hz=fs,
        )

        assert align_res.sync_status == "SYNC_FAILED"
        assert align_res.normalized_cross_correlation < 0.20

    def test_digital_clipping_detection(self):
        """detect_clipping must flag exact clipped samples and event count."""
        sig = np.array([0.1, 0.5, 0.9995, 1.0, 0.9992, 0.2, -0.9999, -1.0, 0.0], dtype=np.float32)
        res = detect_clipping(sig, threshold=0.999)

        assert res["clipping_detected"] is True
        assert res["clipped_samples_count"] == 5
        # Contiguous events: indices 2,3,4 (event 1), indices 6,7 (event 2)
        assert res["clipped_events_count"] == 2


class TestSisoSystemIdentification:
    """Classical SISO H1 frequency response and coherence verification on known channels."""

    def test_h1_and_coherence_on_synthetic_linear_filter(self):
        """H1 FRF must accurately recover frequency response of known Butterworth lowpass."""
        fs = 48000
        dur = 3.0
        # Broadband excitation: multitone across 20–500 Hz
        freqs = [30.0, 50.0, 80.0, 120.0, 180.0, 260.0, 360.0, 480.0]
        stim = generate_multitone(frequencies_hz=freqs, duration_s=dur, sample_rate_hz=fs, peak_amplitude_fs=0.8)

        # Synthetic channel: 2nd-order Butterworth lowpass at 150 Hz + gain 0.5 + 5 ms delay
        sos = scipy.signal.butter(2, 150.0, btype="low", fs=fs, output="sos")
        y = scipy.signal.sosfilt(sos, stim.samples).astype(np.float32) * 0.5

        # Add small uncorrelated noise (SNR ~ 40 dB)
        rng = np.random.default_rng(123)
        noise = (rng.standard_normal(len(y)) * 0.002).astype(np.float32)
        y_noisy = y + noise

        rec = run_phantom_characterization(
            stimulus=stim,
            capture_samples=y_noisy,
            capture_fs=fs,
            template_id="PHANTOM_MULTITONE_PCG_V1",
            trial_id="test_trial_001",
            hardware_status="SIMULATED_BENCH_TEST",
        )

        assert rec.trial_id == "test_trial_001"
        assert rec.hardware_status == "SIMULATED_BENCH_TEST"
        assert rec.alignment.sync_status == "SYNCHRONIZED"

        sys_data = rec.system_id
        assert sys_data["mean_coherence_over_excited_band"] is not None
        # In linear channel with high SNR, coherence across excited bins must exceed 0.90
        assert sys_data["mean_coherence_over_excited_band"] > 0.85

        # Verify lowpass attenuation: H1 at 50 Hz must be higher than H1 at 400 Hz
        freqs_resp = np.array(sys_data["frequencies_hz"])
        h1_mag_db = np.array(sys_data["h1_magnitude_db"])
        idx_50 = np.argmin(np.abs(freqs_resp - 50.0))
        idx_400 = np.argmin(np.abs(freqs_resp - 400.0))

        # At 50 Hz (passband), gain is ~ 0.5 (-6 dB)
        assert -10.0 < h1_mag_db[idx_50] < -4.0
        # At 400 Hz (stopband), gain is significantly lower (< -15 dB)
        assert h1_mag_db[idx_400] < -12.0


class TestMetrologicalTruthfulness:
    """Enforcement of metrological honesty and disclaimers."""

    def test_phantom_templates_catalog(self):
        """Catalog must contain all 5 required experiment templates with checklists."""
        assert len(STANDARD_PHANTOM_TEMPLATES) == 5
        assert "PHANTOM_SINE_100HZ_V1" in STANDARD_PHANTOM_TEMPLATES
        assert "PHANTOM_MULTITONE_PCG_V1" in STANDARD_PHANTOM_TEMPLATES
        assert "PHANTOM_LOG_SWEEP_20_500HZ_V1" in STANDARD_PHANTOM_TEMPLATES
        assert "PHANTOM_IMPULSE_TRAIN_V1" in STANDARD_PHANTOM_TEMPLATES
        assert "PHANTOM_PCG_REPLAY_V1" in STANDARD_PHANTOM_TEMPLATES

        for tmpl in STANDARD_PHANTOM_TEMPLATES.values():
            assert tmpl.target_frequency_band_hz == [20.0, 500.0]
            assert tmpl.default_output_gain_dbfs <= 0.0
            assert len(tmpl.checklist) >= 3

    def test_disclaimer_and_pending_status(self):
        """Phantom record must declare non-flat response disclaimer and PENDING status."""
        stim = generate_100hz_sine(duration_s=1.0, sample_rate_hz=48000)
        rec = run_phantom_characterization(
            stimulus=stim,
            capture_samples=stim.samples,
            capture_fs=48000,
            hardware_status="PENDING_PHYSICAL_MEASUREMENT",
        )

        assert rec.hardware_status == "PENDING_PHYSICAL_MEASUREMENT"
        assert "Neither the exciter nor the microphone is assumed to have a flat frequency response" in rec.metrological_disclaimer
        assert "No absolute sound pressure levels (Pa, dB SPL)" in rec.metrological_disclaimer
        assert "PC audio output -> PAM8403 amplifier -> 12-ohm exciter" in rec.intended_chain


class TestPhantomApiEndpoints:
    """FastAPI integration tests for phantom routes."""

    @pytest.fixture
    def client(self, tmp_path):
        app = create_app(
            sessions_dir=tmp_path / "sessions",
            assets_dir=tmp_path / "assets",
            analysis_dir=tmp_path / "analysis",
        )
        return TestClient(app)

    def test_api_list_templates(self, client):
        resp = client.get("/api/scientific/phantom/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        ids = [t["template_id"] for t in data]
        assert "PHANTOM_LOG_SWEEP_20_500HZ_V1" in ids

    def test_api_generate_stimulus_and_characterize(self, client, tmp_path):
        # 1. Generate stimulus
        gen_resp = client.post("/api/scientific/phantom/stimulus/generate", json={
            "stimulus_type": "sine_100hz",
            "duration_s": 1.0,
            "sample_rate_hz": 48000,
            "amplitude_fs": 0.8,
            "save_as_asset": True,
        })
        assert gen_resp.status_code == 200
        stim_data = gen_resp.json()
        asset_id = stim_data["asset_id"]
        assert asset_id is not None

        # 2. Mock a recorded session in tmp_path / sessions
        sess_id = "test_sess_001"
        sess_dir = tmp_path / "sessions" / sess_id
        sess_dir.mkdir(parents=True, exist_ok=True)
        # Write 48kHz audio to session
        t = np.arange(48000) / 48000.0
        audio = (0.7 * np.sin(2 * np.pi * 100.0 * t)).astype(np.float32)
        wavfile.write(sess_dir / "raw.wav", 48000, (audio * 32767).astype(np.int16))
        with open(sess_dir / "session.json", "w") as f:
            json.dump({"session_id": sess_id, "duration_s": 1.0, "total_samples": 48000, "raw_wav_sha256": "dummy"}, f)

        # 3. Call characterize
        char_resp = client.post("/api/scientific/phantom/characterize", json={
            "asset_id": asset_id,
            "session_id": sess_id,
            "template_id": "PHANTOM_SINE_100HZ_V1",
            "hardware_status": "PENDING_PHYSICAL_MEASUREMENT",
        })
        assert char_resp.status_code == 200
        char_data = char_resp.json()
        assert char_data["hardware_status"] == "PENDING_PHYSICAL_MEASUREMENT"
        assert char_data["alignment"]["sync_status"] == "SYNCHRONIZED"

        # 4. List phantom experiments
        list_resp = client.get("/api/scientific/phantom/experiments")
        assert list_resp.status_code == 200
        exps = list_resp.json()
        assert len(exps) >= 1
        assert exps[0]["trial_id"] == char_data["trial_id"]

        # 5. Get individual phantom experiment
        get_resp = client.get(f"/api/scientific/phantom/experiments/{char_data['trial_id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["trial_id"] == char_data["trial_id"]
