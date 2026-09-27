"""AuscultaForge — Automated Tests for Scientific Signal Quality Characterization.

Verifies:
- Empty and invalid input rejection (empty array, NaN, Inf, non-positive fs)
- Zeros signal (rms = 0, crest factor = 0, no saturation)
- Constant signal (mean == constant, peak == constant, peak-to-peak == 0)
- Known sinusoid (RMS == A / sqrt(2), crest factor == sqrt(2))
- Scaled sinusoids and amplitude linearity
- Unit impulse behavior
- Exact full-scale samples (+/-1.0) and digital saturation fraction
- Explicit assurance that digital saturation does NOT assert acoustic overload
- Sample count and duration calculations
- Zero-crossing rate on AC signals
"""

import math
import numpy as np
import pytest

from pcg_core.scientific.models import SignalQualityConfig, SignalCharacterizationResult
from pcg_core.scientific.signal_quality import compute_signal_quality


class TestScientificSignalQuality:
    """Verifies deterministic scalar signal quality characterization."""

    def test_rejects_empty_signal(self):
        with pytest.raises(ValueError, match="empty signal array"):
            compute_signal_quality(np.array([]), sample_rate_hz=48000)

    def test_rejects_invalid_sample_rate(self):
        with pytest.raises(ValueError, match="strictly positive"):
            compute_signal_quality(np.ones(100), sample_rate_hz=0)
        with pytest.raises(ValueError, match="strictly positive"):
            compute_signal_quality(np.ones(100), sample_rate_hz=-100)

    def test_rejects_nan_and_inf(self):
        arr_nan = np.array([0.1, 0.2, np.nan, 0.4])
        with pytest.raises(ValueError, match="NaN or infinite"):
            compute_signal_quality(arr_nan, sample_rate_hz=48000)

        arr_inf = np.array([0.1, 0.2, np.inf, 0.4])
        with pytest.raises(ValueError, match="NaN or infinite"):
            compute_signal_quality(arr_inf, sample_rate_hz=48000)

    def test_zeros_signal(self):
        fs = 48000.0
        n = 4800
        x = np.zeros(n)
        res = compute_signal_quality(x, sample_rate_hz=fs)

        assert res.sample_count == n
        assert pytest.approx(res.duration_s) == 0.1
        assert res.mean_dc == 0.0
        assert res.rms == 0.0
        assert res.peak_absolute == 0.0
        assert res.peak_to_peak == 0.0
        assert res.crest_factor == 0.0
        assert res.digital_full_scale_utilization == 0.0
        assert res.digital_saturation_count == 0
        assert res.digital_saturation_fraction == 0.0

    def test_constant_dc_signal(self):
        fs = 4000.0
        c = 0.42
        x = np.full(2000, c)
        res = compute_signal_quality(x, sample_rate_hz=fs)

        assert pytest.approx(res.mean_dc) == c
        assert pytest.approx(res.rms) == c
        assert pytest.approx(res.peak_absolute) == c
        assert pytest.approx(res.peak_to_peak) == 0.0
        assert pytest.approx(res.crest_factor) == 1.0  # peak / rms = c / c = 1.0
        assert pytest.approx(res.digital_full_scale_utilization) == c
        assert res.digital_saturation_count == 0

    def test_pure_sinusoid_rms_and_crest_factor(self):
        fs = 48000.0
        amp = 0.5
        freq = 100.0  # Exactly 10 cycles in 4800 samples
        n = 4800
        t = np.arange(n) / fs
        x = amp * np.sin(2.0 * np.pi * freq * t)

        res = compute_signal_quality(x, sample_rate_hz=fs)

        expected_rms = amp / np.sqrt(2.0)
        expected_crest = amp / expected_rms  # sqrt(2) ~ 1.4142

        assert pytest.approx(res.mean_dc, abs=1e-6) == 0.0
        assert pytest.approx(res.rms, rel=1e-3) == expected_rms
        assert pytest.approx(res.peak_absolute, rel=1e-3) == amp
        assert pytest.approx(res.peak_to_peak, rel=1e-3) == 2.0 * amp
        assert pytest.approx(res.crest_factor, rel=1e-3) == expected_crest
        assert pytest.approx(res.digital_full_scale_utilization, rel=1e-3) == amp
        assert res.digital_saturation_count == 0

    def test_amplitude_scaling_linearity(self):
        fs = 4000.0
        rng = np.random.default_rng(12345)
        base = rng.standard_normal(2000)
        base /= np.max(np.abs(base))  # normalize to 1.0

        res1 = compute_signal_quality(0.2 * base, sample_rate_hz=fs)
        res2 = compute_signal_quality(0.8 * base, sample_rate_hz=fs)

        assert pytest.approx(res2.rms / res1.rms, rel=1e-3) == 4.0
        assert pytest.approx(res2.peak_absolute / res1.peak_absolute, rel=1e-3) == 4.0
        # Crest factor is scale-invariant
        assert pytest.approx(res1.crest_factor, rel=1e-3) == res2.crest_factor

    def test_impulse_signal(self):
        fs = 1000.0
        x = np.zeros(100)
        x[10] = 1.0  # Unit impulse

        res = compute_signal_quality(x, sample_rate_hz=fs)

        assert pytest.approx(res.peak_absolute) == 1.0
        assert pytest.approx(res.rms) == 1.0 / np.sqrt(100)
        assert pytest.approx(res.crest_factor) == 10.0
        assert res.digital_saturation_count == 1
        assert pytest.approx(res.digital_saturation_fraction) == 0.01

    def test_digital_saturation_vs_acoustic_overload(self):
        fs = 48000.0
        x = np.zeros(1000)
        # 5 samples clipped at exact full-scale 1.0
        x[100:105] = 1.0
        # 3 samples at -1.0
        x[200:203] = -1.0

        cfg = SignalQualityConfig(clipping_threshold=0.999)
        res = compute_signal_quality(x, sample_rate_hz=fs, config=cfg)

        assert res.digital_saturation_count == 8
        assert pytest.approx(res.digital_saturation_fraction) == 8.0 / 1000.0
        # Provenance explicitly asserts digital full-scale hit definition
        assert res.provenance["clipping_definition"] == "digital_full_scale_hits_only_not_acoustic_overload"

    def test_zero_crossing_rate(self):
        fs = 1000.0
        freq = 50.0  # 50 Hz -> 100 zero-crossings per second
        t = np.arange(1000) / fs
        x = np.sin(2.0 * np.pi * freq * t)

        res = compute_signal_quality(x, sample_rate_hz=fs)
        assert res.zero_crossing_rate is not None
        # 100 zero crossings over 999 intervals ~ 0.10
        assert pytest.approx(res.zero_crossing_rate, abs=0.01) == 0.10

    def test_to_dict_serialization(self):
        fs = 48000.0
        x = np.array([0.1, -0.2, 0.5, -0.9, 0.999])
        res = compute_signal_quality(x, sample_rate_hz=fs)
        d = res.to_dict()

        assert d["schema_version"] == "1.0.0"
        assert d["sample_count"] == 5
        assert isinstance(d["digital_saturation_count"], int)
        assert isinstance(d["rms"], float)
        assert not math.isnan(d["crest_factor"])
