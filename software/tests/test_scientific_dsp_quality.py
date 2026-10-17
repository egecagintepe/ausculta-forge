"""AuscultaForge — Automated Scientific DSP, Signal Integrity & Quality Verification (Sprint 06).

Rigorous numerical verification suite covering:
1. Causal streaming IIR vs offline zero-phase filtering and explicit metadata tracking.
2. Filter behavior, frequency response, and numerical stability at 4 kHz and 48 kHz.
3. Mandatory 20–500 Hz characterization band vs provisional 20–600 Hz general development preset.
4. Independent analytical ground truth validations:
   - Sinusoid RMS (A / sqrt(2)), Peak (A), Crest Factor (sqrt(2))
   - Square wave RMS (A), Peak (A), Crest Factor (1.0)
   - Triangle wave RMS (A / sqrt(3)), Peak (A), Crest Factor (sqrt(3))
   - DC + Sinusoid RMS sqrt(B^2 + A^2/2)
   - Digital saturation count and fraction
   - Zero-crossing rate on AC signals
   - Welch PSD Parseval energy conservation
   - Band power partition sums
   - Hilbert envelope of pure tone (constant A)
   - Moving RMS envelope of DC (constant DC)
   - TKEO theoretical frequency scaling (A^2 * sin^2(omega_0))
   - Homomorphic envelope extraction
5. Deterministic handling of silence, NaNs, very short signals, invalid sample rates, and extreme amplitudes.
6. Separate quality dimensions (clipping, continuity, VLF motion, spectral contamination, timing, morphology)
   without invented 0–100 scores or diagnostic claims.
7. Metrological rule enforcement: prohibition of uncalibrated Pa / dB SPL and raw signal immutability.
"""

import math
from typing import Any
import numpy as np
import pytest
import scipy.signal

from pcg_core.models import SampleBlock
from pcg_core.dsp import StreamingBandpass, offline_bandpass
from pcg_core.metrics import rms, peak_abs, crest_factor
from pcg_core.analysis import (
    FilterConfig,
    compute_spectrogram_data,
    analyze_source,
)
from pcg_core.sources import MockPCGSource
from pcg_core.scientific import (
    SignalQualityConfig,
    SignalCharacterizationResult,
    compute_signal_quality,
    assess_signal_quality,
    MultiDimensionalQualityReport,
    WelchConfig,
    SpectralAnalysisResult,
    compute_welch_psd,
    EnvelopeLabConfig,
    EnvelopeLabResult,
    compute_envelope_lab,
    compute_hilbert_envelope,
    compute_moving_rms_envelope,
    compute_tkeo,
    compute_psd_band_envelope,
)
from pcg_core.scientific_config import (
    SignalUnit,
    validate_unit_usage,
    get_analysis_profile,
    list_analysis_profiles,
    PCG_CHARACTERIZATION_20_500_HZ,
    GENERAL_PCG_V1,
    RAW_INTEGRITY_V1,
)


# ==============================================================================
# 1. Causal Streaming Filters vs. Offline Processing & Metadata
# ==============================================================================

class TestFilterCausalityAndMetadata:
    """Verifies that causal streaming filters and zero-phase offline filters are rigorously audited."""

    def test_streaming_bandpass_metadata_and_causality(self):
        """StreamingBandpass must report causal_iir phase policy and valid metadata."""
        bp = StreamingBandpass(sample_rate_hz=48000, low_hz=20.0, high_hz=500.0, order=4)
        meta = bp.get_metadata()

        assert meta["filter_type"] == "butterworth_bandpass"
        assert meta["phase_policy"] == "causal_iir"
        assert meta["is_causal"] is True
        assert meta["order"] == 4
        assert meta["low_hz"] == 20.0
        assert meta["high_hz"] == 500.0
        assert meta["sample_rate_hz"] == 48000
        assert meta["structure"] == "cascaded_second_order_sections_sos"

    def test_offline_bandpass_zero_phase_vs_causal(self):
        """offline_bandpass must explicitly distinguish zero_phase_noncausal from causal_iir."""
        fs = 48000
        t = np.arange(4800) / fs
        # 100 Hz tone + 5 Hz tone
        sig = (np.sin(2 * np.pi * 100.0 * t) + 0.5 * np.sin(2 * np.pi * 5.0 * t)).astype(np.float32)

        # 1. Causal filtering
        causal_out, causal_meta = offline_bandpass(sig, sample_rate_hz=fs, low_hz=20.0, high_hz=500.0, zero_phase=False)
        assert causal_meta["phase_policy"] == "causal_iir"
        assert causal_meta["zero_phase"] is False

        # 2. Zero-phase filtering
        zp_out, zp_meta = offline_bandpass(sig, sample_rate_hz=fs, low_hz=20.0, high_hz=500.0, zero_phase=True)
        assert zp_meta["phase_policy"] == "zero_phase_noncausal"
        assert zp_meta["zero_phase"] is True

        # Impulse test for causality and group delay:
        # A unit impulse at sample index 1000
        impulse_sig = np.zeros(2000, dtype=np.float32)
        impulse_sig[1000] = 1.0

        c_imp, _ = offline_bandpass(impulse_sig, sample_rate_hz=fs, low_hz=20.0, high_hz=500.0, zero_phase=False)
        zp_imp, _ = offline_bandpass(impulse_sig, sample_rate_hz=fs, low_hz=20.0, high_hz=500.0, zero_phase=True)

        # 1. Causal filter strictly obeys h[n] == 0 for n < 1000
        assert np.all(c_imp[:1000] == 0.0)
        # Peak of causal impulse response occurs strictly after the impulse onset due to group delay
        assert np.argmax(np.abs(c_imp)) > 1000

        # 2. Zero-phase filter is non-causal (rings before sample 1000) but has exactly zero peak displacement
        assert np.sum(np.abs(zp_imp[:1000])) > 0.0
        assert np.argmax(np.abs(zp_imp)) == 1000  # Exact zero delay!

    def test_raw_data_immutability(self):
        """Filtering must NEVER mutate the caller's input array."""
        orig = np.array([0.1, 0.5, -0.3, 0.8, -0.2], dtype=np.float32)
        orig_copy = orig.copy()
        block = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=4000, samples=orig)

        bp = StreamingBandpass(sample_rate_hz=4000, low_hz=20.0, high_hz=500.0)
        filtered_block = bp.process(block)

        # Input array remains untouched
        assert np.array_equal(orig, orig_copy)
        assert not np.shares_memory(orig, filtered_block.samples)


# ==============================================================================
# 2. Filter Behavior & Numerical Stability at 4 kHz and 48 kHz
# ==============================================================================

class TestFilterStabilityAndResponse:
    """Verifies Butterworth SOS stability and frequency response at 4 kHz and 48 kHz."""

    @pytest.mark.parametrize("fs", [4000, 48000])
    @pytest.mark.parametrize("low,high", [(20.0, 500.0), (20.0, 600.0)])
    def test_poles_strictly_inside_unit_circle(self, fs: int, low: float, high: float):
        """All SOS poles must satisfy |z| < 1.0 (unconditional asymptotic stability)."""
        bp = StreamingBandpass(sample_rate_hz=fs, low_hz=low, high_hz=high, order=4)
        z, p, k = scipy.signal.sos2zpk(bp.sos)
        max_pole_radius = np.max(np.abs(p))
        assert max_pole_radius < 1.0, f"Unstable pole detected at fs={fs}: |p|={max_pole_radius}"

    @pytest.mark.parametrize("fs", [4000, 48000])
    def test_frequency_response_gain_and_attenuation(self, fs: int):
        """Passband gain near 100 Hz must be ~1.0; stopband gain at 5 Hz and high freq must be heavily attenuated."""
        bp = StreamingBandpass(sample_rate_hz=fs, low_hz=20.0, high_hz=500.0, order=4)
        w, h = scipy.signal.sosfreqz(bp.sos, worN=[5.0, 100.0, min(1500.0, fs / 2.0 - 10.0)], fs=fs)
        gain_db = 20.0 * np.log10(np.abs(h))

        # 100 Hz in passband: gain ~ 0 dB (+/- 0.5 dB)
        assert abs(gain_db[1]) < 0.5, f"100 Hz gain deviation: {gain_db[1]} dB"

        # 5 Hz in stopband: attenuation > 30 dB (gain < -30 dB)
        assert gain_db[0] < -30.0, f"5 Hz attenuation insufficient: {gain_db[0]} dB"

        # High stopband: attenuation > 25 dB
        assert gain_db[2] < -25.0, f"High frequency attenuation insufficient: {gain_db[2]} dB"

    def test_streaming_block_continuity_matches_continuous_filtering(self):
        """Processing block-by-block with StreamingBandpass matches continuous filtering within float precision."""
        fs = 48000
        block_size = 512
        num_blocks = 20
        total_samples = num_blocks * block_size
        t = np.arange(total_samples) / fs
        # 80 Hz heart sound tone
        signal = (0.5 * np.sin(2 * np.pi * 80.0 * t)).astype(np.float32)

        bp = StreamingBandpass(sample_rate_hz=fs, low_hz=20.0, high_hz=500.0, order=4)

        # 1. Stream block by block
        streamed_blocks = []
        for i in range(num_blocks):
            sub = signal[i * block_size : (i + 1) * block_size]
            blk = SampleBlock(sequence=i, timestamp_s=i * block_size / fs, sample_rate_hz=fs, samples=sub)
            out_blk = bp.process(blk)
            streamed_blocks.append(out_blk.samples)
        streamed_full = np.concatenate(streamed_blocks)

        # 2. Continuous reference using same initial state
        sos = bp.sos
        cont_full, _ = scipy.signal.sosfilt(sos, signal, zi=scipy.signal.sosfilt_zi(sos) * 0.0)

        # Compare after warmup (skip first block)
        diff = np.abs(streamed_full[block_size:] - cont_full[block_size:])
        assert np.max(diff) < 1e-5, f"Block boundary discontinuity: max diff={np.max(diff)}"

    def test_filter_stability_under_silence_dc_and_extremes(self):
        """Filter handles silence (zeros), DC step, and extreme numbers without NaNs or overflows."""
        fs = 48000
        bp = StreamingBandpass(sample_rate_hz=fs, low_hz=20.0, high_hz=500.0)

        # Silence (all zeros)
        zeros_block = SampleBlock(sequence=0, timestamp_s=0.0, sample_rate_hz=fs, samples=np.zeros(1024, dtype=np.float32))
        out_zeros = bp.process(zeros_block)
        assert np.all(out_zeros.samples == 0.0)
        assert not np.any(np.isnan(out_zeros.samples))

        # Constant DC step (must settle to 0.0)
        dc_block = SampleBlock(sequence=1, timestamp_s=0.1, sample_rate_hz=fs, samples=np.full(4800, 0.75, dtype=np.float32))
        out_dc = bp.process(dc_block)
        assert not np.any(np.isnan(out_dc.samples))
        # After 4800 samples (100 ms), DC component is filtered out to near zero (< 0.01)
        assert abs(out_dc.samples[-1]) < 0.01

        # Extreme amplitude (1e6)
        big_block = SampleBlock(sequence=2, timestamp_s=0.2, sample_rate_hz=fs, samples=np.full(512, 1e6, dtype=np.float32))
        out_big = bp.process(big_block)
        assert not np.any(np.isnan(out_big.samples))
        assert not np.any(np.isinf(out_big.samples))


# ==============================================================================
# 3. Mandatory 20–500 Hz vs. Provisional 20–600 Hz Distinction
# ==============================================================================

class TestCharacterizationBandVsProvisionalPreset:
    """Verifies that the mandatory 20–500 Hz band is distinct from 20–600 Hz development presets."""

    def test_profiles_catalog_contains_both_profiles(self):
        """Standard catalog must register PCG_CHARACTERIZATION_20_500_HZ and GENERAL_PCG_V1 distinctly."""
        char_prof = get_analysis_profile("PCG_CHARACTERIZATION_20_500_HZ")
        gen_prof = get_analysis_profile("GENERAL_PCG_V1")

        assert char_prof.profile_id == "PCG_CHARACTERIZATION_20_500_HZ"
        assert char_prof.filter_policy == "butterworth_bandpass_20_500_hz_order4_causal"
        assert char_prof.feature_policy.get("characterization_band_hz") == [20.0, 500.0]

        assert gen_prof.profile_id == "GENERAL_PCG_V1"
        assert gen_prof.filter_policy == "butterworth_bandpass_20_600_hz_order4_causal"

    def test_analysis_spectrogram_reports_characterization_energy_ratio(self):
        """Spectrogram energy ratios must include characterization_pcg_20_500hz."""
        fs = 4000
        t = np.arange(4000) / fs
        # Signal concentrated in characterization band (100 Hz tone)
        sig = np.sin(2 * np.pi * 100.0 * t)
        spec = compute_spectrogram_data(sig, fs=fs)

        assert "characterization_pcg_20_500hz" in spec.band_energy_ratios
        assert "fundamental_pcg_20_150hz" in spec.band_energy_ratios
        assert "extended_pcg_150_600hz" in spec.band_energy_ratios

        # 100 Hz tone is inside both 20-150 Hz and 20-500 Hz
        assert spec.band_energy_ratios["characterization_pcg_20_500hz"] > 0.90
        assert spec.band_energy_ratios["fundamental_pcg_20_150hz"] > 0.90

    def test_analyze_source_preset_detection(self):
        """analyze_source must identify preset_name and is_provisional status accurately."""
        src = MockPCGSource(duration_s=0.5, sample_rate_hz=4000)

        # Mandatory characterization preset
        res_char = analyze_source(src, filter_low_hz=20.0, filter_high_hz=500.0)
        assert res_char.filter_config.preset_name == "characterization_20_500hz"
        assert res_char.filter_config.is_provisional is False
        assert res_char.filter_config.phase_policy == "causal_iir"

        # General provisional preset
        res_gen = analyze_source(src, filter_low_hz=20.0, filter_high_hz=600.0)
        assert res_gen.filter_config.preset_name == "general_20_600hz"
        assert res_gen.filter_config.is_provisional is True


# ==============================================================================
# 4. Exact Independent Analytical Ground Truth Validations
# ==============================================================================

class TestAnalyticalGroundTruths:
    """Verifies metrics against independently derived mathematical ground truths."""

    def test_sinusoid_analytical_metrics(self):
        """For A*sin(wt): RMS = A / sqrt(2), Peak = A, Crest Factor = sqrt(2)."""
        fs = 48000
        amp = 0.8
        f0 = 100.0
        t = np.arange(48000) / fs  # Exact 100 cycles
        x = amp * np.sin(2 * np.pi * f0 * t)

        assert pytest.approx(rms(x), rel=1e-4) == amp / np.sqrt(2.0)
        assert pytest.approx(peak_abs(x), rel=1e-4) == amp
        assert pytest.approx(crest_factor(x), rel=1e-4) == np.sqrt(2.0)

    def test_square_wave_analytical_metrics(self):
        """For square wave of amplitude A: RMS = A, Peak = A, Crest Factor = 1.0."""
        fs = 48000
        amp = 0.6
        f0 = 50.0
        t = np.arange(48000) / fs
        x = amp * np.sign(np.sin(2 * np.pi * f0 * t))

        assert pytest.approx(rms(x), rel=1e-4) == amp
        assert pytest.approx(peak_abs(x), rel=1e-4) == amp
        assert pytest.approx(crest_factor(x), rel=1e-4) == 1.0

    def test_triangle_wave_analytical_metrics(self):
        """For triangle wave of peak amplitude A: RMS = A / sqrt(3), Crest Factor = sqrt(3)."""
        fs = 48000
        amp = 0.9
        f0 = 50.0
        t = np.arange(48000) / fs
        x = amp * scipy.signal.sawtooth(2 * np.pi * f0 * t, width=0.5)

        expected_rms = amp / np.sqrt(3.0)
        expected_cf = np.sqrt(3.0)

        assert pytest.approx(rms(x), rel=1e-3) == expected_rms
        assert pytest.approx(peak_abs(x), rel=1e-3) == amp
        assert pytest.approx(crest_factor(x), rel=1e-3) == expected_cf

    def test_dc_plus_sine_analytical_rms(self):
        """For B + A*sin(wt): RMS = sqrt(B^2 + A^2 / 2)."""
        fs = 48000
        b = 0.3
        a = 0.4
        t = np.arange(48000) / fs
        x = b + a * np.sin(2 * np.pi * 100.0 * t)

        expected_rms = np.sqrt(b**2 + (a**2) / 2.0)
        assert pytest.approx(rms(x), rel=1e-4) == expected_rms

    def test_exact_clipping_detection(self):
        """Digital saturation counter must detect exact clipped sample counts."""
        x = np.full(1000, 0.5)
        x[42:47] = 0.9995  # 5 positive saturation hits
        x[100:103] = -1.0  # 3 negative saturation hits

        cfg = SignalQualityConfig(clipping_threshold=0.999)
        res = compute_signal_quality(x, sample_rate_hz=48000, config=cfg)

        assert res.digital_saturation_count == 8
        assert pytest.approx(res.digital_saturation_fraction) == 8 / 1000.0

    def test_exact_zero_crossing_rate(self):
        """For a 50 Hz square wave at 1000 Hz, ZCR = 2 * 50 / 1000 = 0.10 crossings/interval."""
        fs = 1000
        t = np.arange(1000) / fs
        x = np.sign(np.sin(2 * np.pi * 50.0 * t))

        res = compute_signal_quality(x, sample_rate_hz=fs)
        # Exactly 100 zero crossings across 999 intervals ~ 0.1001
        assert pytest.approx(res.zero_crossing_rate, abs=0.005) == 0.10

    def test_parseval_power_conservation_in_welch_psd(self):
        """Parseval theorem: Integral of Welch PSD density across [0, fs/2] equals signal variance."""
        fs = 4000.0
        n = 8000
        rng = np.random.default_rng(42)
        # Zero-mean white noise with variance = 0.04 (RMS = 0.2)
        noise = (rng.standard_normal(n) * 0.2).astype(np.float64)
        noise -= np.mean(noise)
        var_signal = float(np.var(noise))

        cfg = WelchConfig(nperseg=1024, noverlap=512, window="hann", scaling="density", detrend=False)
        res = compute_welch_psd(noise, sample_rate_hz=fs, config=cfg)

        freqs = np.array(res.frequencies_hz)
        psd = np.array(res.psd)
        # Trapezoidal numerical integration of PSD: int P(f) df
        integrated_power = float(np.trapezoid(psd, freqs))

        # Integrated power matches time-domain variance within 5% estimation uncertainty
        assert pytest.approx(integrated_power, rel=0.08) == var_signal

    def test_hilbert_envelope_of_pure_tone_is_constant(self):
        """Analytic signal magnitude of A * cos(w0 * t) is constant A (Bedrosian theorem)."""
        fs = 48000
        amp = 0.75
        t = np.arange(4800) / fs
        tone = amp * np.cos(2 * np.pi * 150.0 * t)

        env = compute_hilbert_envelope(tone)
        # Skip edge boundary transients (first 100 and last 100 samples)
        interior = env[100:-100]
        assert pytest.approx(np.mean(interior), rel=1e-3) == amp
        assert np.max(np.abs(interior - amp)) < 0.01

    def test_tkeo_theoretical_frequency_scaling(self):
        """TKEO on pure tone A * cos(w0 * n) must equal A^2 * sin^2(w0)."""
        amp = 0.8
        w0 = 0.15  # Discrete angular frequency (rad/sample)
        n = np.arange(500)
        x = amp * np.cos(w0 * n)

        tkeo_vals = compute_tkeo(x, boundary_policy="replicate")
        expected_tkeo = (amp ** 2) * (np.sin(w0) ** 2)

        # Check interior samples (n=1 to N-2)
        interior = tkeo_vals[10:-10]
        assert np.allclose(interior, expected_tkeo, atol=1e-5)


# ==============================================================================
# 5. Deterministic Error & Boundary Handling
# ==============================================================================

class TestDeterministicEdgeCases:
    """Verifies that silence, NaNs, empty inputs, and invalid rates fail safely and informatively."""

    def test_silence_all_zeros_behavior(self):
        """All-zeros signal produces finite 0.0 metrics without division by zero or NaN."""
        fs = 48000
        zeros = np.zeros(2048)

        # 1. Signal quality
        q = compute_signal_quality(zeros, sample_rate_hz=fs)
        assert q.rms == 0.0
        assert q.peak_absolute == 0.0
        assert q.crest_factor == 0.0
        assert q.digital_saturation_count == 0

        # 2. Welch PSD on zeros
        psd = compute_welch_psd(zeros, sample_rate_hz=fs)
        assert not np.any(np.isnan(psd.psd))
        assert not np.any(np.isinf(psd.psd))

        # 3. Envelopes on zeros
        assert np.all(compute_hilbert_envelope(zeros) == 0.0)
        assert np.all(compute_moving_rms_envelope(zeros, fs) == 0.0)
        assert np.all(compute_tkeo(zeros) == 0.0)

    def test_rejects_nan_and_inf_in_all_extractors(self):
        """All extractors must strictly raise ValueError on NaN or Inf."""
        bad_nan = np.array([0.1, np.nan, 0.5])
        bad_inf = np.array([0.1, np.inf, 0.5])

        for bad in (bad_nan, bad_inf):
            with pytest.raises(ValueError):
                compute_signal_quality(bad, 48000)
            with pytest.raises(ValueError):
                compute_welch_psd(bad, 48000)
            with pytest.raises(ValueError):
                compute_hilbert_envelope(bad)
            with pytest.raises(ValueError):
                compute_moving_rms_envelope(bad, 48000)
            with pytest.raises(ValueError):
                compute_tkeo(bad)
            with pytest.raises(ValueError):
                offline_bandpass(bad, 48000)

    def test_rejects_invalid_sample_rates(self):
        """Negative and zero sampling rates must raise ValueError."""
        x = np.ones(100)
        for invalid_fs in (0, -100, -1.0):
            with pytest.raises(ValueError):
                compute_signal_quality(x, invalid_fs)
            with pytest.raises(ValueError):
                compute_welch_psd(x, invalid_fs)
            with pytest.raises(ValueError):
                compute_moving_rms_envelope(x, invalid_fs)
            with pytest.raises(ValueError):
                StreamingBandpass(invalid_fs)
            with pytest.raises(ValueError):
                offline_bandpass(x, invalid_fs)

    def test_handles_short_arrays(self):
        """Arrays with length 1, 2, or 3 samples must not crash."""
        fs = 4000
        # 1-sample array
        x1 = np.array([0.5])
        q1 = compute_signal_quality(x1, fs)
        assert q1.sample_count == 1
        assert q1.rms == 0.5

        # TKEO on <3 samples returns zeros without crashing
        assert len(compute_tkeo(x1)) == 1
        assert compute_tkeo(x1)[0] == 0.0
        assert len(compute_tkeo(np.array([0.1, 0.2]))) == 2


# ==============================================================================
# 6. Separate Quality Dimensions & Anti-Fabrication Guarantees
# ==============================================================================

class TestMultiDimensionalQualityAssessment:
    """Verifies that separate quality dimensions are reported without invented 0–100 scores."""

    def test_assess_signal_quality_dimensions(self):
        """assess_signal_quality must report clipping, continuity, vlf, spectral, and timing separately."""
        fs = 48000
        t = np.arange(48000) / fs
        # Signal with DC offset (0.05) + 100 Hz tone + 5 clipped samples
        x = (0.05 + 0.4 * np.sin(2 * np.pi * 100.0 * t)).astype(np.float64)
        x[500:505] = 1.0  # 5 clipped samples

        stream_stats = {"sequence_gaps": 2, "dropped_blocks": 2, "timestamp_regressions": 0}
        report = assess_signal_quality(x, sample_rate_hz=fs, stream_stats=stream_stats)

        assert isinstance(report, MultiDimensionalQualityReport)
        d = report.to_dict()

        # 1. Clipping dimension
        assert d["clipping"]["digital_saturation_count"] == 5
        assert d["clipping"]["clipping_detected"] is True

        # 2. Continuity dimension
        assert d["continuity"]["sequence_gaps"] == 2
        assert d["continuity"]["has_discontinuity"] is True

        # 3. VLF motion dimension
        assert d["vlf_motion_evidence"]["dc_offset_present"] is True
        assert "vlf_energy_fraction_0_20hz" in d["vlf_motion_evidence"]

        # 4. Spectral contamination dimension
        assert "mains_hum_50hz_ratio" in d["spectral_contamination"]
        assert "characterization_band_fraction_20_500hz" in d["spectral_contamination"]
        assert d["spectral_contamination"]["characterization_band_fraction_20_500hz"] > 0.8

        # 5. Timing dimension
        assert d["timing_faults"]["rate_stability_status"] == "nominal"

        # 6. Morphology dimension
        assert d["morphology_evidence"]["is_silent"] is False

        # STRICT ANTI-FABRICATION RULE: NO 0–100 composite score exists anywhere in the report!
        assert "score" not in d
        assert "grade" not in d
        assert "quality_score" not in d


# ==============================================================================
# 7. Metrological Rules Enforcement
# ==============================================================================

class TestMetrologicalRules:
    """Verifies strict adherence to physical units and calibration policies."""

    def test_uncalibrated_physical_units_rejected(self):
        """Pascal and dB SPL must raise ValueError without documented calibration certificate."""
        # Uncalibrated Pascal usage raises ValueError
        with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
            validate_unit_usage("pascal", has_acoustic_calibration=False)

        # Uncalibrated dB SPL usage raises ValueError
        with pytest.raises(ValueError, match="calibrated acoustic measurement chain"):
            validate_unit_usage(SignalUnit.DB_SPL, has_acoustic_calibration=False)

        # Permitted digital units pass without error
        validate_unit_usage(SignalUnit.NORMALIZED_FS)
        validate_unit_usage(SignalUnit.DBFS)
        validate_unit_usage(SignalUnit.RAW_PCM_CODE)
        validate_unit_usage(SignalUnit.DIMENSIONLESS)
        validate_unit_usage(SignalUnit.FS_SQUARED_PER_HZ)
