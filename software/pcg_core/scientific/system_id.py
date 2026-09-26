"""AuscultaForge — Scientific SISO System Identification Foundation.

Implements conservative Single-Input Single-Output (SISO) best-linear frequency response
estimation under the classical H1 estimator model.

Mathematical Framework & Conventions:
1. Classical H1 Model:
   Assumes a linear time-invariant relationship with additive output noise:
       y[n] = (h * x)[n] + v[n]
   where excitation x[n] is measured without noise, and v[n] is uncorrelated with x[n].
   
2. SciPy Cross-Spectral Density Convention:
   scipy.signal.csd(x, y) evaluates <conj(X(f)) * Y(f)> = S_xy(f).
   Since Y(f) = H(f) * X(f) + V(f), we have:
       S_xy(f) = <X*(f) * (H(f) X(f) + V(f))> = H(f) * S_xx(f)
   Therefore, the unbiased H1 transfer function estimator is:
       H1(f) = S_xy(f) / S_xx(f) = csd(x, y) / welch(x)
       
3. Ordinary Magnitude-Squared Coherence:
       gamma_xy^2(f) = |S_xy(f)|^2 / (S_xx(f) * S_yy(f))
   Measures frequency-dependent linear association under the estimator assumptions.
   COHERENCE ALONE DOES NOT ESTABLISH PHYSICAL CAUSALITY.
   
4. Coherent & Residual Output Spectra:
       G_yy,coherent(f) = gamma_xy^2(f) * G_yy(f)  (linearly associated output component)
       G_yy,residual(f) = (1 - gamma_xy^2(f)) * G_yy(f)  (unexplained/noise/nonlinear component)
       
5. Excited-Frequency Energy Mask:
   Coherence and FRF calculations are only physically meaningful at frequencies where the
   input stimulus has sufficient energy. An explicit mask is formed:
       mask(f) = (f >= f_low) & (f <= f_high) & (10*log10(G_xx(f)/max(G_xx)) >= threshold_db)
   Summary metric 'mean_coherence_over_excited_band' is evaluated strictly over this mask.
   
6. End-to-End System Response Metrology Boundary:
   In phantom or laboratory testing (stimulus -> DAC -> amp -> speaker -> phantom -> coupling ->
   chestpiece -> sensor -> acquisition), H1 characterizes the COMPLETE END-TO-END TRANSMISSION CHAIN.
   It is NOT an isolated stethoscope transfer function, NOT an anatomical chest response, and
   NOT calibrated acoustic sound pressure.
"""

from __future__ import annotations

from typing import Optional
import numpy as np
import scipy.signal

from .models import SystemIdConfig, SystemIdentificationResult


def estimate_siso_system_id(
    input_signal: np.ndarray,
    output_signal: np.ndarray,
    sample_rate_hz: float,
    config: Optional[SystemIdConfig] = None,
    input_name: str = "reference_stimulus",
    output_name: str = "capture_response",
) -> SystemIdentificationResult:
    """Estimate SISO best-linear frequency response (H1), coherence, and spectral partitions.
    
    Parameters
    ----------
    input_signal : np.ndarray
        1D floating-point excitation sequence (reference).
    output_signal : np.ndarray
        1D floating-point response sequence (capture).
    sample_rate_hz : float
        Sampling frequency in Hertz (both signals must share this rate).
    config : Optional[SystemIdConfig]
        Welch/CSD windowing parameters and excited-band mask settings.
    input_name : str
        Human-readable name of input stimulus.
    output_name : str
        Human-readable name of output capture.
        
    Returns
    -------
    SystemIdentificationResult
        Autospectra, cross-spectrum, H1 magnitude/phase, coherence, and excited-band summary.
        
    Raises
    ------
    ValueError
        If inputs are empty, contain NaN/Inf, or sample_rate_hz <= 0.
    """
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be strictly positive, got {sample_rate_hz}")
        
    if not isinstance(input_signal, np.ndarray):
        input_signal = np.asarray(input_signal, dtype=np.float64)
    if not isinstance(output_signal, np.ndarray):
        output_signal = np.asarray(output_signal, dtype=np.float64)
        
    if input_signal.ndim != 1:
        input_signal = input_signal.flatten()
    if output_signal.ndim != 1:
        output_signal = output_signal.flatten()
        
    if len(input_signal) == 0 or len(output_signal) == 0:
        raise ValueError("Cannot perform system identification on empty signal arrays.")
        
    if np.any(np.isnan(input_signal)) or np.any(np.isinf(input_signal)):
        raise ValueError("Input signal contains NaN or infinite values.")
    if np.any(np.isnan(output_signal)) or np.any(np.isinf(output_signal)):
        raise ValueError("Output signal contains NaN or infinite values.")

    cfg = config or SystemIdConfig()
    
    # Harmonize lengths if mismatched: truncate to common length
    min_len = min(len(input_signal), len(output_signal))
    x = input_signal[:min_len]
    y = output_signal[:min_len]

    nperseg = min(cfg.nperseg, min_len)
    if nperseg < 8:
        raise ValueError(f"Common signal length ({min_len}) is too short for system identification (minimum 8 samples).")
        
    noverlap = cfg.effective_noverlap()
    if noverlap >= nperseg:
        noverlap = nperseg // 2
        
    nfft = cfg.effective_nfft()
    if nfft < nperseg:
        nfft = nperseg

    # 1. Input Autospectrum Gxx(f)
    f_x, Gxx = scipy.signal.welch(
        x,
        fs=float(sample_rate_hz),
        window=cfg.window,
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        detrend=cfg.detrend,
        scaling="density",
    )

    # 2. Output Autospectrum Gyy(f)
    f_y, Gyy = scipy.signal.welch(
        y,
        fs=float(sample_rate_hz),
        window=cfg.window,
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        detrend=cfg.detrend,
        scaling="density",
    )

    # 3. Cross-Spectral Density Gxy(f)
    # Convention: scipy.signal.csd(x, y) = <X*(f) * Y(f)>
    f_xy, Gxy = scipy.signal.csd(
        x,
        y,
        fs=float(sample_rate_hz),
        window=cfg.window,
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        detrend=cfg.detrend,
        scaling="density",
    )

    freqs = f_x
    df = float(sample_rate_hz) / float(nfft)

    # 4. Ordinary Magnitude-Squared Coherence
    # gamma_xy^2 = |Gxy|^2 / (Gxx * Gyy)
    denom_coh = Gxx * Gyy
    coh = np.zeros_like(freqs, dtype=np.float64)
    valid_coh = denom_coh > 1e-30
    coh[valid_coh] = np.abs(Gxy[valid_coh]) ** 2 / denom_coh[valid_coh]
    coh = np.clip(coh, 0.0, 1.0)

    # 5. H1 Best-Linear FRF Estimator: H1(f) = Gxy(f) / Gxx(f)
    # Regularized to prevent division by near-zero at unexcited frequencies
    eps = 1e-30
    H1 = Gxy / (Gxx + eps)

    h1_mag = np.abs(H1)
    h1_mag_db = 20.0 * np.log10(np.maximum(h1_mag, 1e-15))
    h1_phase_rad = np.angle(H1)  # Wrapped into [-pi, +pi]
    h1_phase_deg = np.rad2deg(h1_phase_rad)
    h1_phase_unwrapped_deg = np.rad2deg(np.unwrap(h1_phase_rad))

    # 6. Coherent and Residual Output Spectra
    coherent_output = coh * Gyy
    residual_output = np.maximum(0.0, (1.0 - coh) * Gyy)

    # 7. Excited-Frequency Energy Mask
    f_low, f_high = cfg.excited_band_hz
    in_freq_band = (freqs >= f_low) & (freqs <= f_high)
    
    max_gxx = float(np.max(Gxx)) if len(Gxx) > 0 else 1.0
    if max_gxx > 0:
        gxx_rel_db = 10.0 * np.log10(np.maximum(Gxx, 1e-30) / max_gxx)
        sufficient_energy = gxx_rel_db >= float(cfg.energy_threshold_db_rel_max)
    else:
        sufficient_energy = np.ones_like(freqs, dtype=bool)

    excited_mask = in_freq_band & sufficient_energy
    excited_count = int(np.sum(excited_mask))

    mean_coh_excited: Optional[float] = None
    if excited_count > 0:
        mean_coh_excited = float(np.mean(coh[excited_mask]))

    notes = (
        "SISO H1 best-linear frequency response estimate. In phantom testing, this characterizes "
        "the full end-to-end electro-acoustic transmission chain (stimulus -> DAC -> amp -> speaker -> "
        "phantom -> coupling -> chestpiece -> sensor -> acquisition). It is NOT an isolated stethoscope FRF, "
        "NOT anatomical chest response, and coherence alone does NOT establish physical causality."
    )

    provenance = {
        "analysis_type": "siso_system_id_h1",
        "sample_rate_hz": float(sample_rate_hz),
        "input_sample_count": len(x),
        "output_sample_count": len(y),
        "nperseg": nperseg,
        "noverlap": noverlap,
        "nfft": nfft,
        "window": cfg.window,
        "detrend": cfg.detrend,
        "csd_convention": "scipy.signal.csd(x, y) = <conj(X) * Y>; H1 = Gxy / Gxx",
        "excited_band_hz": list(cfg.excited_band_hz),
        "energy_threshold_db_rel_max": cfg.energy_threshold_db_rel_max,
        "analysis_profile": cfg.analysis_profile,
    }

    return SystemIdentificationResult(
        schema_version="1.0.0",
        sample_rate_hz=float(sample_rate_hz),
        input_name=input_name,
        output_name=output_name,
        frequencies_hz=[float(v) for v in freqs],
        gxx_autospectrum=[float(v) for v in Gxx],
        gyy_autospectrum=[float(v) for v in Gyy],
        gxy_cross_spectrum_real=[float(v.real) for v in Gxy],
        gxy_cross_spectrum_imag=[float(v.imag) for v in Gxy],
        coherence=[float(v) for v in coh],
        h1_magnitude=[float(v) for v in h1_mag],
        h1_magnitude_db=[float(v) for v in h1_mag_db],
        h1_phase_rad=[float(v) for v in h1_phase_rad],
        h1_phase_deg=[float(v) for v in h1_phase_deg],
        h1_phase_unwrapped_deg=[float(v) for v in h1_phase_unwrapped_deg],
        coherent_output_spectrum=[float(v) for v in coherent_output],
        residual_output_spectrum=[float(v) for v in residual_output],
        excited_frequency_mask=[bool(v) for v in excited_mask],
        excited_bins_count=excited_count,
        mean_coherence_over_excited_band=mean_coh_excited,
        frequency_bin_spacing_hz=df,
        notes=notes,
        provenance=provenance,
    )
