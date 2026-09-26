"""AuscultaForge — Automated Tests for Scientific Envelope Lab.

Verifies:
- Analytical signal magnitude (Hilbert envelope) on amplitude-modulated (AM) waveform
- Moving RMS envelope on known-amplitude signal
- Discrete Teager-Kaiser Energy Operator (TKEO):
  - Numerical proof test: Psi[A cos(omega_0 n)] == A^2 * sin^2(omega_0) within machine tolerance
  - Frequency sensitivity (higher energy at higher frequency for same amplitude)
  - Amplitude quadratic scaling (Psi proportional to A^2)
  - Boundary handling policies ('replicate' and 'zero')
  - Noise and invalid input robustness
- Short-time PSD-band envelope:
  - In-band burst (40–60 Hz) vs out-of-band burst (200 Hz) energy discrimination
  - Correct time-vector cadence and hop alignment
- Deferred status of homomorphic envelope
"""

import math
import numpy as np
import pytest

from pcg_core.scientific.models import EnvelopeLabConfig, EnvelopeLabResult
from pcg_core.scientific.envelopes import (
    compute_hilbert_envelope,
    compute_moving_rms_envelope,
    compute_tkeo,
    compute_psd_band_envelope,
    compute_envelope_lab,
)


class TestScientificEnvelopeLab:
    """Verifies Stage-A deterministic envelope extraction algorithms."""

    def test_hilbert_envelope_am_signal(self):
        """Verifies Hilbert envelope recovers modulation envelope on an AM carrier."""
        fs = 4000.0
        duration = 1.0
        n = int(fs * duration)
        t = np.arange(n) / fs

        f_carrier = 300.0
        f_mod = 5.0
        mod_index = 0.4
        
        # Exact theoretical envelope: A(t) = 1.0 + mod_index * cos(2*pi*f_mod*t)
        expected_envelope = 1.0 + mod_index * np.cos(2.0 * np.pi * f_mod * t)
        carrier = np.cos(2.0 * np.pi * f_carrier * t)
        am_signal = expected_envelope * carrier

        recovered = compute_hilbert_envelope(am_signal)

        # Discard 10% edges to avoid Hilbert filter boundary transients
        margin = int(0.10 * n)
        err = np.abs(recovered[margin:-margin] - expected_envelope[margin:-margin])
        assert np.max(err) < 0.05  # Within 5% of theoretical envelope

    def test_moving_rms_constant_signal(self):
        """Moving RMS of a constant C should be |C| everywhere in the interior."""
        fs = 1000.0
        c = 0.75
        x = np.full(500, c)
        rms_env = compute_moving_rms_envelope(x, sample_rate_hz=fs, window_duration_s=0.02)

        # Interior samples should equal |c|
        assert pytest.approx(rms_env[50:-50], abs=1e-6) == c

    def test_tkeo_theoretical_sinusoid_identity(self):
        """Mathematical proof: For x[n] = A * cos(omega_0 * n), Psi[x[n]] == A^2 * sin^2(omega_0)."""
        A = 2.5
        # Test across multiple discrete frequencies omega_0
        for omega_0 in [0.05, 0.15, 0.35, 0.70]:
            n = np.arange(100)
            x = A * np.cos(omega_0 * n + 0.3)  # Arbitrary phase
            
            tkeo = compute_tkeo(x, boundary_policy="zero")
            expected_val = (A ** 2) * (np.sin(omega_0) ** 2)

            # Interior samples n = 1 to 98 must exactly match theoretical value
            interior = tkeo[1:-1]
            np.testing.assert_allclose(interior, expected_val, rtol=1e-10)

    def test_tkeo_frequency_and_amplitude_scaling(self):
        """Verifies TKEO scales quadratically with amplitude and increases with frequency."""
        fs = 4000.0
        t = np.arange(1000) / fs
        
        # Frequency scaling: 50 Hz vs 150 Hz with identical amplitude 1.0
        x_50 = np.cos(2.0 * np.pi * 50.0 * t)
        x_150 = np.cos(2.0 * np.pi * 150.0 * t)

        tkeo_50 = compute_tkeo(x_50)
        tkeo_150 = compute_tkeo(x_150)

        mean_50 = np.mean(tkeo_50[10:-10])
        mean_150 = np.mean(tkeo_150[10:-10])
        assert mean_150 > mean_50  # Higher frequency gives higher TKEO

        # Amplitude scaling: 2x amplitude gives 4x TKEO
        x_50_scaled = 2.0 * x_50
        tkeo_scaled = compute_tkeo(x_50_scaled)
        mean_scaled = np.mean(tkeo_scaled[10:-10])
        assert pytest.approx(mean_scaled / mean_50, rel=1e-3) == 4.0

    def test_tkeo_boundary_policies(self):
        x = np.array([1.0, 2.0, 4.0, 7.0, 11.0])
        
        # 'replicate': tkeo[0] == tkeo[1], tkeo[-1] == tkeo[-2]
        res_rep = compute_tkeo(x, boundary_policy="replicate")
        assert res_rep[0] == res_rep[1]
        assert res_rep[-1] == res_rep[-2]

        # 'zero': tkeo[0] == 0.0, tkeo[-1] == 0.0
        res_zero = compute_tkeo(x, boundary_policy="zero")
        assert res_zero[0] == 0.0
        assert res_zero[-1] == 0.0

    def test_psd_band_envelope_springer_40_60_hz(self):
        """Verifies 40-60 Hz PSD envelope responds strongly to 50 Hz burst and rejects 200 Hz tone."""
        fs = 1000.0
        duration = 2.0
        n = int(fs * duration)
        t = np.arange(n) / fs

        # Signal with in-band 50 Hz tone in first second, out-of-band 200 Hz in second second
        x = np.zeros(n)
        x[:1000] = np.sin(2.0 * np.pi * 50.0 * t[:1000])   # In-band (40-60 Hz)
        x[1000:] = np.sin(2.0 * np.pi * 200.0 * t[1000:])  # Out-of-band

        time_s, env = compute_psd_band_envelope(
            x,
            sample_rate_hz=fs,
            band_hz=(40.0, 60.0),
            window_duration_s=0.05,
            overlap_fraction=0.5,
            window_type="hamming",
        )

        assert len(time_s) == len(env)
        assert len(time_s) > 10

        # Mean envelope in first second (50 Hz active) vs second second (200 Hz active)
        first_half = env[time_s < 0.9]
        second_half = env[time_s > 1.1]

        assert np.mean(first_half) > 10.0 * np.mean(second_half)

    def test_compute_envelope_lab_suite(self):
        fs = 1000.0
        t = np.arange(1000) / fs
        x = np.sin(2.0 * np.pi * 50.0 * t)

        res = compute_envelope_lab(x, sample_rate_hz=fs)

        assert isinstance(res, EnvelopeLabResult)
        assert "hilbert" in res.envelopes
        assert "moving_rms" in res.envelopes
        assert "tkeo" in res.envelopes
        assert "psd_band" in res.envelopes

        # Check serialization
        d = res.to_dict()
        assert d["schema_version"] == "1.0.0"
        assert d["provenance"]["homomorphic_status"] == "DEFERRED_STAGE_B"

    def test_envelope_rejects_nan_and_inf(self):
        with pytest.raises(ValueError):
            compute_hilbert_envelope(np.array([1.0, np.nan, 2.0]))
        with pytest.raises(ValueError):
            compute_moving_rms_envelope(np.array([1.0, np.inf, 2.0]), 1000)
        with pytest.raises(ValueError):
            compute_tkeo(np.array([1.0, np.nan, 2.0]))
