"""AuscultaForge — Automated Acoustic Phantom PCG Experiment Runner.

Orchestrates the SDP4 Week 9 Feasibility Experiment with rigorous metrological integrity:
1. Prepares a standardized 48 kHz normalized stimulus from a known clinical PCG (CirCor DigiScope)
   with controlled lead-in (0.5 s), active playback (8.5 s), and tail (1.0 s).
2. Drives playback through the PC audio output into the PAM8403 amplifier and vibration exciter
   with active playback thread error tracking.
3. Concurrently acquires 10.0 seconds (480,000 samples @ 48 kHz) from the INMP441 MEMS microphone over USB CDC.
4. STRICT WAV INGEST: Opens the capture strictly via session_result["raw_wav_path"].
   Validates session metadata (source_mode=0, device_id, raw_wav_sha256, session integrity).
   Never falls back to reference/stimulus WAV or globs.
5. Ingest quality gating: Evaluates actual dropped_frames, crc_failures, and firmware telemetry.
   Separates post-target 256-sample DMA drain from in-stream drops without assuming 0 drops on missing data.
6. In-band SNR gating: Computes true 20-500 Hz SNR strictly if a quiet baseline session is provided;
   reports INCONCLUSIVE_NO_QUIET_BASELINE without fabricating numbers if omitted.
7. Aligns source and captured signals via cross-correlation and computes Welch coherence in 20-250 Hz.
8. Evaluates S1/S2 morphological rhythm preservation: requires >= 70% peak matching against
   the source heart sound complexes within 80 ms tolerance and <= 45 ms mean jitter.
9. Produces reproducible JSON and Markdown reports with full provenance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import threading
import time
from typing import Any, Optional, Tuple

import numpy as np
import scipy.signal
from scipy.io import wavfile

# Add software directory to sys.path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software"))

try:
    from pcg_core.dsp import StreamingBandpass
    from pcg_core.metrics import rms, peak_abs
    from pcg_core.phantom import (
        METROLOGICAL_DISCLAIMER_PHANTOM,
        detect_clipping,
        estimate_phantom_alignment,
    )
    from pcg_core.recording import verify_session_integrity
    from pcg_core.stimulus import prepare_reference_wav_stimulus, StimulusRecord
except ImportError as exc:
    raise SystemExit(
        f"Missing AuscultaForge core dependency: {exc}. Run with .venv Python."
    ) from exc


class PlaybackController:
    """Thread-safe Windows audio player with active error tracking."""

    def __init__(self, wav_path: Path):
        self.wav_path = wav_path
        self.started_event = threading.Event()
        self.completed_event = threading.Event()
        self.playback_error: Optional[str] = None
        self.start_timestamp: Optional[float] = None
        self.end_timestamp: Optional[float] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        def _worker():
            try:
                import winsound
                self.start_timestamp = time.monotonic()
                self.started_event.set()
                winsound.PlaySound(str(self.wav_path), winsound.SND_FILENAME)
                self.end_timestamp = time.monotonic()
            except Exception as e:
                self.playback_error = str(e)
                self.started_event.set()
            finally:
                self.completed_event.set()

        self.thread = threading.Thread(target=_worker, daemon=True)
        self.thread.start()
        # Wait up to 1.5s for initial startup
        if not self.started_event.wait(timeout=1.5):
            self.playback_error = "Audio playback worker timed out on startup"
        if self.playback_error:
            raise RuntimeError(f"AUDIO_PLAYBACK_INITIALIZATION_FAILED: {self.playback_error}")

    def stop(self) -> None:
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass


def compute_shannon_envelope(
    signal: np.ndarray,
    sample_rate_hz: int,
    smoothing_window_ms: float = 50.0,
) -> Tuple[np.ndarray, list[dict[str, Any]]]:
    """Compute normalized Shannon energy envelope and identify peak complexes.
    
    Es[n] = - x_norm[n]^2 * ln(x_norm[n]^2 + 1e-12)
    """
    sig = np.asarray(signal, dtype=np.float32)
    max_amp = float(np.max(np.abs(sig))) if len(sig) > 0 else 1.0
    norm_sig = sig / max_amp if max_amp > 1e-12 else sig

    sq = norm_sig ** 2
    shannon = -sq * np.log(sq + 1e-12)

    win_len = max(3, int((smoothing_window_ms / 1000.0) * sample_rate_hz))
    window = np.ones(win_len, dtype=np.float32) / float(win_len)
    smoothed = np.convolve(shannon, window, mode="same")

    # Heart sound burst minimum distance: 180 ms
    min_dist_samples = int(0.18 * sample_rate_hz)
    threshold = float(np.mean(smoothed) + 0.35 * np.std(smoothed))

    peaks, _ = scipy.signal.find_peaks(
        smoothed,
        distance=min_dist_samples,
        height=threshold,
    )

    detected_peaks: list[dict[str, Any]] = []
    for idx in peaks:
        t_sec = float(idx / sample_rate_hz)
        detected_peaks.append({
            "sample_index": int(idx),
            "time_s": round(t_sec, 4),
            "envelope_amplitude": round(float(smoothed[idx]), 5),
            "raw_amplitude": round(float(sig[idx]), 5),
        })

    return smoothed, detected_peaks


def verify_s1_s2_morphological_correspondence(
    ref_signal: np.ndarray,
    cap_signal: np.ndarray,
    sample_rate_hz: int,
    delay_ms: float,
    match_tolerance_ms: float = 80.0,
    min_match_fraction: float = 0.70,
    max_mean_timing_jitter_ms: float = 45.0,
) -> Tuple[bool, str, dict[str, Any]]:
    """Compare S1/S2 heart sound envelope peaks between source and captured signals.
    
    Verifies that the temporal rhythm and peak structure of the captured signal
    matches the reference clinical PCG rather than arbitrary room noise or tones.
    """
    env_ref_raw, ref_peaks = compute_shannon_envelope(ref_signal, sample_rate_hz)
    env_cap_raw, cap_peaks = compute_shannon_envelope(cap_signal, sample_rate_hz)

    # Check envelope contrast (peak-to-mean ratio): pulsed heart sounds have contrast >= 2.0
    env_contrast = float(np.max(env_cap_raw) / (np.mean(env_cap_raw) + 1e-12))

    # Filter out peaks in the first 0.3 s or last 0.5 s (edge boundary transitions)
    dur_s = float(len(ref_signal) / sample_rate_hz)
    ref_peaks = [p for p in ref_peaks if 0.3 <= p["time_s"] <= (dur_s - 0.5)]
    cap_peaks = [p for p in cap_peaks if 0.3 <= p["time_s"] <= (dur_s - 0.5)]

    if env_contrast < 2.0:
        return False, f"INCONCLUSIVE_FLAT_ENVELOPE (contrast {env_contrast:.2f} < 2.0, lacks distinct S1/S2 bursts)", {
            "ref_peak_count": len(ref_peaks),
            "cap_peak_count": len(cap_peaks),
            "matched_peak_count": 0,
            "matched_fraction": 0.0,
            "timing_errors_ms": [],
            "envelope_contrast": round(env_contrast, 2),
            "reason": "Captured envelope is relatively flat; characteristic of continuous noise rather than pulsed heart sounds.",
        }

    if len(ref_peaks) < 4:
        return False, "INCONCLUSIVE_INSUFFICIENT_REFERENCE_PEAKS", {
            "ref_peak_count": len(ref_peaks),
            "cap_peak_count": len(cap_peaks),
            "matched_peak_count": 0,
            "matched_fraction": 0.0,
            "timing_errors_ms": [],
            "reason": "Reference signal has fewer than 4 identifiable heart sound complexes.",
        }

    if len(cap_peaks) < 4:
        return False, "INCONCLUSIVE_INSUFFICIENT_CAPTURED_PEAKS", {
            "ref_peak_count": len(ref_peaks),
            "cap_peak_count": len(cap_peaks),
            "matched_peak_count": 0,
            "matched_fraction": 0.0,
            "timing_errors_ms": [],
            "reason": "Captured signal has fewer than 4 identifiable heart sound complexes.",
        }

    # Verify peak count ratio (reject spurious dense noise oscillations)
    peak_ratio = len(cap_peaks) / max(1, len(ref_peaks))
    if peak_ratio > 1.8 or peak_ratio < 0.5:
        return False, f"INCONCLUSIVE_PEAK_COUNT_MISMATCH (captured {len(cap_peaks)} vs ref {len(ref_peaks)})", {
            "ref_peak_count": len(ref_peaks),
            "cap_peak_count": len(cap_peaks),
            "matched_peak_count": 0,
            "matched_fraction": 0.0,
            "timing_errors_ms": [],
            "peak_ratio": round(peak_ratio, 2),
            "reason": "Number of detected peaks differs significantly from reference heart sound complexes.",
        }

    # For each reference peak, look for corresponding captured peak within match_tolerance_ms (one-to-one, order-preserving)
    delay_s = delay_ms / 1000.0
    tol_s = match_tolerance_ms / 1000.0

    matched_pairs: list[dict[str, Any]] = []
    timing_errors_ms: list[float] = []
    matched_cap_indices: set[int] = set()

    for rp in ref_peaks:
        expected_t = rp["time_s"] + delay_s
        best_idx: Optional[int] = None
        best_diff: float = float("inf")

        for i, cp in enumerate(cap_peaks):
            if i in matched_cap_indices:
                continue
            diff = abs(cp["time_s"] - expected_t)
            if diff < best_diff:
                best_diff = diff
                best_idx = i

        if best_idx is not None and best_diff <= tol_s:
            matched_cap_indices.add(best_idx)
            signed_err_ms = round((cap_peaks[best_idx]["time_s"] - expected_t) * 1000.0, 2)
            timing_errors_ms.append(abs(signed_err_ms))
            matched_pairs.append({
                "ref_time_s": rp["time_s"],
                "expected_cap_time_s": round(expected_t, 4),
                "actual_cap_time_s": cap_peaks[best_idx]["time_s"],
                "timing_error_ms": signed_err_ms,
            })

    matched_fraction = float(len(matched_pairs) / len(ref_peaks))
    mean_jitter_ms = float(np.mean(timing_errors_ms)) if timing_errors_ms else 999.0

    # Calculate cadence: cardiac cycle (S1-to-S1) spans two consecutive envelope peaks (S1 and S2)
    cap_intervals = np.diff([p["time_s"] for p in cap_peaks]) if len(cap_peaks) > 1 else np.array([])
    mean_cap_period = float(np.mean(cap_intervals)) if len(cap_intervals) > 0 else 0.0
    est_cycle_s = float(2.0 * mean_cap_period) if mean_cap_period > 0.1 else 0.0
    est_hr_bpm = float(60.0 / est_cycle_s) if est_cycle_s > 0.3 else 0.0

    is_matched = (
        matched_fraction >= min_match_fraction
        and mean_jitter_ms <= max_mean_timing_jitter_ms
        and 0.18 <= mean_cap_period <= 1.5
        and env_contrast >= 2.0
    )

    detail = {
        "ref_peak_count": len(ref_peaks),
        "cap_peak_count": len(cap_peaks),
        "matched_peak_count": len(matched_pairs),
        "matched_fraction": round(matched_fraction, 4),
        "min_required_fraction": min_match_fraction,
        "mean_timing_jitter_ms": round(mean_jitter_ms, 2),
        "max_allowed_jitter_ms": max_mean_timing_jitter_ms,
        "mean_inter_peak_interval_s": round(mean_cap_period, 4),
        "estimated_cardiac_cycle_s": round(est_cycle_s, 4),
        "estimated_heart_rate_bpm": round(est_hr_bpm, 1),
        "cardiac_cadence_note": "Heart rate estimated assuming 2 envelope peaks per cardiac cycle (S1 and S2). Exact S1/S2 phase assignment requires ECG or clinical ground-truth timing.",
        "matched_pairs": matched_pairs[:8],  # First 8 for provenance
    }

    if is_matched:
        status = "PASS_MATCHES_SOURCE_RHYTHM"
    elif matched_fraction < min_match_fraction:
        status = f"INCONCLUSIVE_LOW_PEAK_MATCH_FRACTION ({matched_fraction * 100:.1f}% < {min_match_fraction * 100:.0f}%)"
    elif mean_jitter_ms > max_mean_timing_jitter_ms:
        status = f"INCONCLUSIVE_HIGH_TIMING_JITTER ({mean_jitter_ms:.1f}ms > {max_mean_timing_jitter_ms}ms)"
    else:
        status = "INCONCLUSIVE_PHYSIOLOGICAL_RATE_OUT_OF_BOUNDS"

    return is_matched, status, detail


def compute_coherence_pcg_band(
    x: np.ndarray,
    y: np.ndarray,
    sample_rate_hz: int,
    band_hz: tuple[float, float] = (20.0, 250.0),
    nperseg: int = 1024,
) -> float:
    """Compute mean Welch magnitude-squared coherence in cardiac passband."""
    min_len = min(len(x), len(y))
    if min_len < nperseg:
        nperseg = max(64, min_len // 2)

    f, cxy = scipy.signal.coherence(x[:min_len], y[:min_len], fs=sample_rate_hz, nperseg=nperseg)
    mask = (f >= band_hz[0]) & (f <= band_hz[1])
    if np.any(mask):
        return float(np.mean(cxy[mask]))
    return 0.0


def simulate_acoustic_phantom_capture(
    stimulus_samples: np.ndarray,
    sample_rate_hz: int,
    acoustic_delay_ms: float = 10.0,
    attenuation_db: float = -4.0,
    lowpass_cutoff_hz: float = 450.0,
    noise_std: float = 0.005,
) -> np.ndarray:
    """Simulate realistic acoustic transmission through silicone phantom for offline test."""
    sig = np.asarray(stimulus_samples, dtype=np.float32)

    delay_samples = int((acoustic_delay_ms / 1000.0) * sample_rate_hz)
    delayed = np.pad(sig, (delay_samples, 0))[:len(sig)] if delay_samples > 0 else sig.copy()

    gain = 10.0 ** (attenuation_db / 20.0)
    attenuated = delayed * gain

    sos = scipy.signal.butter(2, lowpass_cutoff_hz, btype="lowpass", fs=sample_rate_hz, output="sos")
    damped = scipy.signal.sosfilt(sos, attenuated)

    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0.0, noise_std, size=len(damped)).astype(np.float32)

    return (damped + noise).astype(np.float32)


def evaluate_quiet_baseline_snr(
    stimulus_capture: np.ndarray,
    quiet_path: Optional[Path],
    sample_rate_hz: int,
    target_band_hz: tuple[float, float] = (20.0, 500.0),
) -> Tuple[Optional[float], str, dict[str, Any]]:
    """Compute true in-band SNR against a verified quiet baseline recording.
    
    If quiet_path is None or absent, strictly returns (None, 'INCONCLUSIVE_NO_QUIET_BASELINE', ...).
    Never manufactures an arbitrary SNR out of thin air.
    """
    if quiet_path is None:
        return None, "INCONCLUSIVE_NO_QUIET_BASELINE", {
            "status": "INCONCLUSIVE",
            "reason": "No quiet baseline session/file provided (--quiet-session). Real SNR cannot be calculated.",
        }

    p = Path(quiet_path)
    if not p.exists():
        return None, "INCONCLUSIVE_QUIET_BASELINE_FILE_MISSING", {
            "status": "INCONCLUSIVE",
            "file": str(p),
            "reason": f"Specified quiet baseline file does not exist: {p}",
        }

    # If JSON session file, locate raw.wav inside
    if p.suffix.lower() == ".json":
        meta = json.loads(p.read_text(encoding="utf-8"))
        wav_cand = p.parent / meta.get("raw_wav_relpath", "raw.wav")
        if not wav_cand.is_file():
            return None, "INCONCLUSIVE_QUIET_SESSION_WAV_MISSING", {
                "status": "INCONCLUSIVE",
                "reason": f"raw.wav referenced in session.json missing: {wav_cand}",
            }
        p = wav_cand

    try:
        q_fs, q_data = wavfile.read(p)
    except Exception as exc:
        return None, "INCONCLUSIVE_QUIET_WAV_UNREADABLE", {
            "status": "INCONCLUSIVE",
            "reason": f"Cannot read quiet WAV: {exc}",
        }

    if q_data.ndim > 1:
        q_data = q_data.mean(axis=1)
    if np.issubdtype(q_data.dtype, np.integer):
        q_samples = (q_data.astype(np.float32) / float(np.iinfo(q_data.dtype).max))
    else:
        q_samples = q_data.astype(np.float32)

    if q_fs != sample_rate_hz:
        gcd = math.gcd(int(q_fs), sample_rate_hz)
        up = sample_rate_hz // gcd
        down = int(q_fs) // gcd
        q_samples = scipy.signal.resample_poly(q_samples, up, down).astype(np.float32)

    # Bandpass filter in 20-500 Hz
    sos = scipy.signal.butter(4, [target_band_hz[0], target_band_hz[1]], btype="bandpass", fs=sample_rate_hz, output="sos")
    filt_stim = scipy.signal.sosfiltfilt(sos, stimulus_capture)
    filt_quiet = scipy.signal.sosfiltfilt(sos, q_samples)

    # Use steady-state window (1.0 s to 9.0 s) to exclude DMA startup settling
    n_start = int(1.0 * sample_rate_hz)
    n_end_stim = min(len(filt_stim), int(9.0 * sample_rate_hz))
    n_end_quiet = min(len(filt_quiet), int(9.0 * sample_rate_hz))

    stim_win = filt_stim[n_start:n_end_stim] if len(filt_stim) > n_start + 1000 else filt_stim
    quiet_win = filt_quiet[n_start:n_end_quiet] if len(filt_quiet) > n_start + 1000 else filt_quiet

    stim_rms = float(rms(stim_win))
    quiet_rms = float(rms(quiet_win))

    if not np.isfinite(stim_rms) or stim_rms <= 1e-12:
        return None, "INCONCLUSIVE_STIMULUS_ZERO_OR_INVALID", {
            "quiet_file": str(p),
            "stimulus_band_rms": round(stim_rms, 6),
            "quiet_band_rms": round(quiet_rms, 6),
            "reason": "Stimulus capture has zero, sub-noise, or non-finite RMS (< 1e-12 FS); invalid/silent recording.",
            "status": "INCONCLUSIVE",
        }

    if not np.isfinite(quiet_rms) or quiet_rms <= 1e-12:
        return None, "INCONCLUSIVE_QUIET_ZERO_OR_INVALID", {
            "quiet_file": str(p),
            "stimulus_band_rms": round(stim_rms, 6),
            "quiet_band_rms": round(quiet_rms, 6),
            "reason": "Quiet baseline recording has zero, sub-noise, or non-finite RMS (< 1e-12 FS); unphysical or disconnected microphone.",
            "status": "INCONCLUSIVE",
        }

    power_ratio_db = round(float(20.0 * np.log10(stim_rms / quiet_rms)), 2)
    sig_only_snr_db = (
        round(float(10.0 * np.log10((stim_rms**2 - quiet_rms**2) / (quiet_rms**2))), 2)
        if stim_rms > quiet_rms
        else None
    )

    is_pass = bool(power_ratio_db >= 12.0)
    status = "PASS" if is_pass else f"INCONCLUSIVE_LOW_SNR ({power_ratio_db:.1f} dB < 12.0 dB)"

    detail = {
        "quiet_file": str(p),
        "stimulus_band_rms": round(stim_rms, 6),
        "quiet_band_rms": round(quiet_rms, 6),
        "active_to_quiet_band_power_ratio_db": power_ratio_db,
        "snr_20_500hz_db": power_ratio_db,
        "signal_only_snr_db": sig_only_snr_db,
        "min_required_snr_db": 12.0,
        "status": status,
        "metric_definition": "active_to_quiet_band_power_ratio_db = 10*log10(Pa/Pq) = 20*log10(RMSa/RMSq) in 20-500 Hz cardiac band. Not absolute sound pressure level.",
    }
    return power_ratio_db, status, detail


def execute_phantom_pcg_experiment(
    reference_wav_path: Path,
    output_dir: Path,
    port: Optional[str] = None,
    captured_wav_path: Optional[Path] = None,
    quiet_session_path: Optional[Path] = None,
    simulate: bool = False,
    play_audio: bool = False,
    audio_routing_verified: bool = False,
    operator: str = "Ege_Kaan_Ozan",
    notes: str = "",
    target_duration_s: float = 10.0,
    target_sample_rate_hz: int = 48000,
) -> dict[str, Any]:
    """Execute complete reproducible acoustic phantom PCG feasibility trial."""
    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
    trial_id = f"trial_{timestamp_str}"
    target_samples = int(target_duration_s * target_sample_rate_hz)

    run_dir = output_dir / trial_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prepare reference stimulus from clinical PCG
    print(f"\n[1/6] Preparing reference PCG stimulus from {reference_wav_path.name}...")
    if not reference_wav_path.is_file():
        raise FileNotFoundError(f"Reference PCG WAV not found: {reference_wav_path}")

    raw_bytes = reference_wav_path.read_bytes()
    stim_record: StimulusRecord = prepare_reference_wav_stimulus(
        wav_bytes=raw_bytes,
        target_sample_rate_hz=target_sample_rate_hz,
        normalize_peak_fs=0.707,  # -3 dBFS to prevent DAC saturation
        filename=reference_wav_path.name,
    )

    # Standardized 10.0s timeline:
    # 0.5s lead-in quiet + 8.5s active PCG + 1.0s tail quiet = 10.0s (480,000 samples)
    lead_in_samples = int(0.5 * target_sample_rate_hz)
    tail_samples = int(1.0 * target_sample_rate_hz)
    active_samples = target_samples - lead_in_samples - tail_samples

    active_slice = (
        stim_record.samples[:active_samples]
        if len(stim_record.samples) >= active_samples
        else np.pad(stim_record.samples, (0, active_samples - len(stim_record.samples)))
    )

    # Apply 50 ms fade-in and fade-out to prevent switching pops
    fade_len = int(0.05 * target_sample_rate_hz)
    ramp_up = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
    ramp_down = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
    active_slice[:fade_len] *= ramp_up
    active_slice[-fade_len:] *= ramp_down

    stim_samples = np.concatenate([
        np.zeros(lead_in_samples, dtype=np.float32),
        active_slice,
        np.zeros(tail_samples, dtype=np.float32),
    ])

    # Export normalized stimulus WAV into separate dedicated file
    stimulus_wav_path = run_dir / f"stimulus_pcg_{target_sample_rate_hz}hz.wav"
    int16_stim = (np.clip(stim_samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    wavfile.write(stimulus_wav_path, target_sample_rate_hz, int16_stim)
    stim_sha256 = hashlib.sha256(stimulus_wav_path.read_bytes()).hexdigest()

    print(f"      Stimulus WAV ready: {stimulus_wav_path.name} ({len(stim_samples)} samples, SHA256: {stim_sha256[:12]}...)")

    # 2. Acquire or simulate captured acoustic audio
    captured_samples: np.ndarray
    capture_meta: dict[str, Any] = {}
    is_physical = False
    hardware_status = "UNKNOWN"
    cap_wav_path: Optional[Path] = None
    playback_controller: Optional[PlaybackController] = None
    playback_status = "NOT_REQUESTED"

    if simulate:
        print("\n[2/6] Running in SIMULATED acoustic phantom channel mode...")
        captured_samples = simulate_acoustic_phantom_capture(
            stim_samples,
            sample_rate_hz=target_sample_rate_hz,
            acoustic_delay_ms=10.0,
            attenuation_db=-4.0,
            lowpass_cutoff_hz=450.0,
            noise_std=0.005,
        )
        cap_wav_path = run_dir / f"captured_pcg_simulated_{target_sample_rate_hz}hz.wav"
        int16_cap = (np.clip(captured_samples, -1.0, 1.0) * 32767.0).astype(np.int16)
        wavfile.write(cap_wav_path, target_sample_rate_hz, int16_cap)

        capture_meta = {
            "source": "SIMULATED_ACOUSTIC_PHANTOM",
            "simulated_delay_ms": 10.0,
            "simulated_attenuation_db": -4.0,
            "simulated_damping_cutoff_hz": 450.0,
            "raw_wav_path": str(cap_wav_path),
            "raw_wav_sha256": hashlib.sha256(cap_wav_path.read_bytes()).hexdigest(),
            "dropped_frames": 0,
            "crc_failures": 0,
            "firmware_telemetry": {
                "generated_samples": target_samples,
                "dropped_samples": 0,
                "dma_overflows": 0,
                "ring_overflows": 0,
                "stop_reason": 0,
            },
        }
        is_physical = False
        hardware_status = "SIMULATED_BENCH_TEST"

    elif captured_wav_path is not None:
        print(f"\n[2/6] Loading pre-recorded capture from {captured_wav_path}...")
        p_cap = Path(captured_wav_path).resolve()
        if not p_cap.is_file():
            raise FileNotFoundError(f"Captured WAV not found: {p_cap}")

        # CRITICAL INTEGRITY CHECK: Reject if user passed reference or stimulus as capture
        cap_bytes = p_cap.read_bytes()
        cap_sha256 = hashlib.sha256(cap_bytes).hexdigest()
        stim_sha256 = hashlib.sha256(stimulus_wav_path.read_bytes()).hexdigest()
        ref_sha256 = hashlib.sha256(reference_wav_path.read_bytes()).hexdigest()

        if (
            p_cap == reference_wav_path.resolve()
            or p_cap == stimulus_wav_path.resolve()
            or cap_sha256 == stim_sha256
            or cap_sha256 == ref_sha256
        ):
            raise RuntimeError(
                f"CRITICAL_INTEGRITY_VIOLATION: Captured file ({p_cap.name}, SHA256: {cap_sha256[:12]}...) "
                "is identical to reference or stimulus by file path or SHA-256 digest! Refusing self-validation."
            )

        cap_fs, cap_data = wavfile.read(p_cap)
        if cap_data.ndim > 1:
            cap_data = cap_data.mean(axis=1)
        if np.issubdtype(cap_data.dtype, np.integer):
            captured_samples = (cap_data.astype(np.float32) / float(np.iinfo(cap_data.dtype).max))
        else:
            captured_samples = cap_data.astype(np.float32)

        if cap_fs != target_sample_rate_hz:
            gcd = math.gcd(int(cap_fs), target_sample_rate_hz)
            up = target_sample_rate_hz // gcd
            down = int(cap_fs) // gcd
            captured_samples = scipy.signal.resample_poly(captured_samples, up, down).astype(np.float32)

        cap_wav_path = p_cap
        cap_sha256 = hashlib.sha256(p_cap.read_bytes()).hexdigest()

        # Check if an accompanying session.json exists to verify provenance
        session_json_cand = p_cap.parent / "session.json"
        has_provenance = False
        provenance_detail: dict[str, Any] = {}
        if session_json_cand.is_file():
            try:
                s_meta = json.loads(session_json_cand.read_text(encoding="utf-8"))
                if s_meta.get("acquisition_mode") == "hardware" and s_meta.get("processing_profile", {}).get("source_mode") == 0:
                    has_provenance = True
                    provenance_detail = s_meta
            except Exception:
                has_provenance = False

        capture_meta = {
            "source": "OFFLINE_CAPTURE_WAV",
            "file": str(p_cap),
            "raw_wav_path": str(p_cap),
            "raw_wav_sha256": cap_sha256,
            "original_fs": cap_fs,
            "has_provenance": has_provenance,
            "provenance": provenance_detail,
            # In offline file mode without live engine, telemetry cannot be assumed 0
            "dropped_frames": 0 if has_provenance else None,
            "crc_failures": 0 if has_provenance else None,
            "firmware_telemetry": provenance_detail.get("firmware_telemetry"),
        }
        is_physical = has_provenance
        hardware_status = "OFFLINE_PROVENANCED" if has_provenance else "OFFLINE_UNVERIFIED"

    elif port is not None:
        print(f"\n[2/6] Initiating LIVE physical capture on {port}...")
        try:
            from pcg_app.wednesday_orchestrator import record_g2_session
        except ImportError:
            raise RuntimeError("Cannot import record_g2_session from pcg_app.")

        if not audio_routing_verified:
            print("      [WARN] Audio routing not explicitly certified (--verify-audio-routing).")

        if play_audio:
            print("      Preparing synchronized audio playback to PAM8403...")
            playback_controller = PlaybackController(stimulus_wav_path)

        def _on_capture_started():
            if playback_controller:
                playback_controller.start()

        print(f"      Streaming {target_samples} samples from ESP32-S3 over USB CDC...")
        try:
            session_result = record_g2_session(
                root=ROOT,
                port=port,
                role="pcg_phantom_stimulus",
                target_samples=target_samples,
                capture_timeout_s=25.0,
                sessions_dir=run_dir,
                on_capture_started=_on_capture_started if play_audio else None,
            )
        except Exception as cap_err:
            if playback_controller:
                playback_controller.stop()
            raise cap_err

        if playback_controller:
            playback_controller.completed_event.wait(timeout=2.0)
            if playback_controller.playback_error:
                playback_status = f"FAILED: {playback_controller.playback_error}"
                raise RuntimeError(f"AUDIO_PLAYBACK_ABORTED: {playback_controller.playback_error}")
            playback_status = "COMPLETED"

        # STRICT RECORDING EXTRACTION: ONLY open through session_result["raw_wav_path"]
        raw_path_str = session_result.get("raw_wav_path")
        if not raw_path_str:
            raise RuntimeError("CRITICAL_CAPTURE_ERROR: record_g2_session did not return raw_wav_path.")

        cap_wav_path = Path(raw_path_str).resolve()
        if not cap_wav_path.is_file():
            raise FileNotFoundError(f"CRITICAL_CAPTURE_FILE_MISSING: Captured file not found at {cap_wav_path}")

        # CRITICAL INTEGRITY CHECK: Reject if capture resolves to stimulus or reference
        if cap_wav_path == stimulus_wav_path.resolve() or cap_wav_path == reference_wav_path.resolve():
            raise RuntimeError(
                f"CRITICAL_INTEGRITY_VIOLATION: Captured WAV ({cap_wav_path}) points to stimulus/reference! "
                "Refusing corrupted capture."
            )

        # Validate session integrity using cryptographic sidecars
        session_id = session_result["session_id"]
        sess_dir = Path(session_result["session_dir"])
        integrity = verify_session_integrity(session_id, sess_dir.parent)
        if not integrity.get("is_valid"):
            raise RuntimeError(f"CRITICAL_SESSION_CORRUPTION: verify_session_integrity failed: {integrity}")

        # Check session metadata
        s_meta = json.loads((sess_dir / "session.json").read_text(encoding="utf-8"))
        if s_meta.get("acquisition_mode") != "hardware":
            raise RuntimeError(f"CRITICAL_METADATA_ERROR: acquisition_mode is {s_meta.get('acquisition_mode')}, expected 'hardware'")
        if s_meta.get("processing_profile", {}).get("source_mode") != 0:
            raise RuntimeError(f"CRITICAL_METADATA_ERROR: source_mode is not 0 (live I2S)")

        # Verify hash match
        actual_cap_sha = hashlib.sha256(cap_wav_path.read_bytes()).hexdigest()
        if actual_cap_sha != session_result.get("raw_wav_sha256"):
            raise RuntimeError("CRITICAL_HASH_MISMATCH: Captured WAV SHA-256 does not match session record.")

        cap_fs, cap_data = wavfile.read(cap_wav_path)
        captured_samples = (
            cap_data.astype(np.float32)
            if not np.issubdtype(cap_data.dtype, np.integer)
            else cap_data.astype(np.float32) / float(np.iinfo(cap_data.dtype).max)
        )

        capture_meta = session_result
        is_physical = True
        hardware_status = "PHYSICAL_VERIFIED"

    else:
        raise ValueError("Must specify either --port, --captured-wav, or --simulate.")

    # 3. Ingest Integrity & Dynamic Range Gating
    print("\n[3/6] Evaluating ingest integrity, packet loss, and clipping...")
    clip_info = detect_clipping(captured_samples, threshold=0.98)
    near_clip_frac = clip_info["clipped_fraction"]
    cap_rms = float(rms(captured_samples))
    cap_peak = float(peak_abs(captured_samples))

    # Evaluate data integrity & telemetry
    dropped_frames = capture_meta.get("dropped_frames")
    crc_failures = capture_meta.get("crc_failures")
    fw_telem = capture_meta.get("firmware_telemetry")

    telemetry_valid = bool(fw_telem is not None and dropped_frames is not None and crc_failures is not None)
    
    # Assess firmware sample drops: only proven post-target drain (256 samples) allowed
    in_stream_fw_drops = capture_meta.get("in_stream_dropped_samples")
    if in_stream_fw_drops is None:
        fw_drops = int(fw_telem.get("dropped_samples", 0)) if fw_telem else 0
        if fw_drops == 256 and (not dropped_frames) and (not crc_failures):
            in_stream_fw_drops = 0
            post_drain = 256
        else:
            in_stream_fw_drops = fw_drops
            post_drain = 0
    else:
        post_drain = int(capture_meta.get("post_target_drained_samples", 0))

    in_stream_loss = bool((dropped_frames and dropped_frames > 0) or in_stream_fw_drops > 0)
    crc_errors_present = bool(crc_failures and crc_failures > 0)

    gate_data_integrity = telemetry_valid and (not in_stream_loss) and (not crc_errors_present)

    if not telemetry_valid:
        data_integrity_status = "INCONCLUSIVE_MISSING_TELEMETRY"
    elif dropped_frames and dropped_frames > 0:
        data_integrity_status = f"FAILED_SEQUENCE_GAPS ({dropped_frames} frames dropped)"
    elif crc_errors_present:
        data_integrity_status = f"FAILED_CRC_FAILURES ({crc_failures} packets corrupt)"
    elif in_stream_fw_drops > 0:
        data_integrity_status = f"FAILED_FIRMWARE_DROPS ({in_stream_fw_drops} in-stream samples lost)"
    else:
        data_integrity_status = f"PASS (0 in-stream drops, 0 CRC errors, post_target_drain={post_drain})"

    gate_clipping = bool(near_clip_frac < 0.0005 and cap_peak < 0.99)
    clipping_status = "PASS" if gate_clipping else f"FAILED_CLIPPING (near_clipping={near_clip_frac*100:.3f}%, peak={cap_peak:.4f})"

    # 4. In-Band Acoustic SNR Evaluation (Strict Quiet Baseline Check)
    print("\n[4/6] Evaluating in-band acoustic SNR (20–500 Hz)...")
    snr_db, snr_status, snr_detail = evaluate_quiet_baseline_snr(
        stimulus_capture=captured_samples,
        quiet_path=quiet_session_path,
        sample_rate_hz=target_sample_rate_hz,
    )
    gate_snr = bool(snr_db is not None and snr_db >= 12.0)

    # 5. Bandpass Filtering & Time Alignment
    print("\n[5/6] Aligning source and captured signals via cross-correlation...")
    aligned_ref, aligned_cap, alignment_res, latency_decomp = estimate_phantom_alignment(
        reference=stim_samples,
        captured=captured_samples,
        sample_rate_hz=target_sample_rate_hz,
        pipeline_buffer_delay_ms=25.0,
        target_band_hz=(20.0, 500.0),
    )

    sos_band = scipy.signal.butter(4, [20.0, 500.0], btype="bandpass", fs=target_sample_rate_hz, output="sos")
    filt_ref = scipy.signal.sosfiltfilt(sos_band, aligned_ref)
    filt_cap = scipy.signal.sosfiltfilt(sos_band, aligned_cap)

    ncc = alignment_res.normalized_cross_correlation
    gate_alignment = bool(ncc >= 0.35)
    alignment_status = "PASS" if gate_alignment else f"FAILED_LOW_CORRELATION (NCC={ncc:.4f} < 0.35)"

    coherence_val = compute_coherence_pcg_band(
        filt_ref, filt_cap, sample_rate_hz=target_sample_rate_hz, band_hz=(20.0, 250.0)
    )
    gate_coherence = bool(coherence_val >= 0.40)
    coherence_status = "PASS" if gate_coherence else f"FAILED_LOW_COHERENCE ({coherence_val:.4f} < 0.40)"

    # 6. S1/S2 Morphological Envelope & Rhythm Verification
    print("\n[6/6] Verifying S1/S2 heart sound morphological correspondence...")
    # filt_ref and filt_cap are already mutual-delay aligned by estimate_phantom_alignment.
    # Pass delay_ms=0.0 to prevent coordinate double-shifting.
    gate_s1s2, s1s2_status, s1s2_detail = verify_s1_s2_morphological_correspondence(
        ref_signal=filt_ref,
        cap_signal=filt_cap,
        sample_rate_hz=target_sample_rate_hz,
        delay_ms=0.0,
    )

    # Playback Gate Check
    gate_playback = True
    if play_audio and playback_status != "COMPLETED":
        gate_playback = False

    # Audio Routing Gate Check
    gate_routing = True
    if is_physical and not audio_routing_verified:
        gate_routing = False

    # Overall Week 9 Gate Synthesis
    all_technical_gates_pass = (
        gate_data_integrity
        and gate_clipping
        and gate_snr
        and gate_alignment
        and gate_coherence
        and gate_s1s2
        and gate_playback
        and gate_routing
    )

    if is_physical:
        if all_technical_gates_pass:
            gate_status = "PHYSICAL_GATE_PASSED"
            hardware_status = "PHYSICAL_VERIFIED"
        else:
            gate_status = "PHYSICAL_GATE_INCONCLUSIVE"
            hardware_status = "PHYSICAL_INCONCLUSIVE"
    elif hardware_status == "OFFLINE_UNVERIFIED":
        gate_status = "OFFLINE_UNVERIFIED_PENDING_PROVENANCE"
    else:
        gate_status = (
            "SIMULATION_VERIFIED_PHYSICAL_PENDING"
            if (gate_data_integrity and gate_clipping and gate_alignment and gate_coherence and gate_s1s2)
            else "SIMULATION_INCONCLUSIVE"
        )

    # Structure Complete Audit Report
    report: dict[str, Any] = {
        "schema_version": "1.1.0",
        "trial_id": trial_id,
        "timestamp_utc": now_utc.isoformat(),
        "operator": operator,
        "notes": notes,
        "is_physical": is_physical,
        "hardware_status": hardware_status,
        "gate_status": gate_status,
        "playback": {
            "requested": play_audio,
            "status": playback_status,
            "audio_routing_verified": audio_routing_verified,
        },
        "stimulus": {
            "source_file": reference_wav_path.name,
            "sample_rate_hz": target_sample_rate_hz,
            "duration_s": round(len(stim_samples) / target_sample_rate_hz, 4),
            "samples_count": len(stim_samples),
            "sha256": stim_sha256,
            "peak_fs": round(float(np.max(np.abs(stim_samples))), 4),
            "rms_fs": round(float(rms(stim_samples)), 4),
            "stimulus_wav_path": str(stimulus_wav_path),
        },
        "capture": {
            "sample_rate_hz": target_sample_rate_hz,
            "samples_count": len(captured_samples),
            "duration_s": round(len(captured_samples) / target_sample_rate_hz, 4),
            "peak_fs": round(cap_peak, 4),
            "rms_fs": round(cap_rms, 4),
            "near_clipping_fraction": round(near_clip_frac, 6),
            "near_clipping_samples": clip_info["clipped_samples_count"],
            "clipping_detected": clip_info["clipping_detected"],
            "raw_wav_path": str(cap_wav_path) if cap_wav_path else None,
            "raw_wav_sha256": capture_meta.get("raw_wav_sha256"),
            "meta": capture_meta,
        },
        "gates": {
            "data_integrity": {"pass": gate_data_integrity, "status": data_integrity_status},
            "clipping_margin": {"pass": gate_clipping, "status": clipping_status},
            "acoustic_snr": {"pass": gate_snr, "status": snr_status, "detail": snr_detail},
            "cross_correlation": {"pass": gate_alignment, "status": alignment_status, "ncc": round(ncc, 5)},
            "passband_coherence": {"pass": gate_coherence, "status": coherence_status, "coherence_20_250": round(coherence_val, 4)},
            "s1_s2_morphology": {"pass": gate_s1s2, "status": s1s2_status, "detail": s1s2_detail},
            "audio_playback": {"pass": gate_playback, "status": playback_status},
            "audio_routing_verified": {"pass": gate_routing, "status": "VERIFIED" if audio_routing_verified else "UNVERIFIED"},
            "overall_pass": all_technical_gates_pass and is_physical,
        },
        "alignment_and_similarity": {
            "normalized_cross_correlation": round(ncc, 5),
            "estimated_delay_ms": round(alignment_res.estimated_delay_ms, 3),
            "estimated_delay_samples": alignment_res.estimated_delay_samples,
            "least_squares_gain": round(alignment_res.least_squares_gain, 4),
            "rms_gain_ratio": round(alignment_res.rms_gain_ratio, 4),
            "mean_coherence_20_250hz": round(coherence_val, 4),
            "nrmse": round(alignment_res.normalized_rmse, 5),
            "signal_to_error_ratio_db": round(alignment_res.signal_to_error_ratio_db, 2),
        },
        "metrological_disclaimer": METROLOGICAL_DISCLAIMER_PHANTOM,
    }

    # Write JSON Report
    report_json_path = run_dir / "phantom_pcg_experiment_report.json"
    with report_json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Write Markdown Report
    report_md_path = run_dir / "phantom_pcg_experiment_report.md"
    md_content = f"""# AuscultaForge — Acoustic Phantom PCG Feasibility Report

- **Trial ID:** `{trial_id}`
- **Date/Time (UTC):** {now_utc.strftime('%Y-%m-%d %H:%M:%S')}
- **Operators:** {operator}
- **Hardware Mode:** `{hardware_status}`
- **Overall Gate Status:** **{gate_status}**

## 1. Stimulus vs. Capture Ingest & Telemetry

| Gate Parameter | Evaluated Value | Threshold / Target | Status |
|---|---|---|---|
| Ingest Route | `{cap_wav_path.name if cap_wav_path else 'None'}` | `record_g2_session["raw_wav_path"]` | {'PASS' if cap_wav_path else 'FAIL'} |
| Packet Loss | `{dropped_frames} dropped frames` | Strictly 0 in-stream drops | {'PASS' if (dropped_frames == 0) else 'FAIL'} |
| CRC Check | `{crc_failures} CRC failures` | Strictly 0 errors | {'PASS' if (crc_failures == 0) else 'FAIL'} |
| FW Sample Drops | `{fw_drops} drops ({'post-target drain' if fw_drops == 256 else 'abnormal'})` | <= 256 post-target drain | {'PASS' if (fw_drops <= 256) else 'FAIL'} |
| Peak Amplitude | `{cap_peak:.4f} FS` | < 0.95 FS | {'PASS' if cap_peak < 0.95 else 'FAIL'} |
| Near-Clipping Fraction | `{near_clip_frac * 100:.4f}%` | < 0.05% | {'PASS' if gate_clipping else 'FAIL'} |
| Acoustic In-Band SNR | `{f'{snr_db:.1f} dB' if snr_db is not None else 'None (Missing Baseline)'}` | >= 12.0 dB in 20–500 Hz | {snr_status} |

## 2. Quantitative System Identification & Alignment

- **Acoustic Channel Delay:** `{alignment_res.estimated_delay_ms:.3f} ms` ({alignment_res.estimated_delay_samples} samples)
- **Normalized Cross-Correlation (NCC):** **`{ncc:.5f}`** (Target: $\\ge 0.35$) → **{alignment_status}**
- **Passband Coherence (20–250 Hz):** **`{coherence_val:.4f}`** (Target: $\\ge 0.40$) → **{coherence_status}**
- **Signal-to-Error Ratio (SER):** `{alignment_res.signal_to_error_ratio_db:.2f} dB`

## 3. S1/S2 Heart Sound Morphology & Rhythm Correspondence

- **Reference Peaks Identified:** `{s1s2_detail.get('ref_peak_count', 0)}`
- **Captured Peaks Identified:** `{s1s2_detail.get('cap_peak_count', 0)}`
- **Peak Match Fraction:** **`{s1s2_detail.get('matched_fraction', 0.0) * 100:.1f}%`** (Target: $\\ge 70.0\\%$)
- **Mean Timing Jitter:** **`{s1s2_detail.get('mean_timing_jitter_ms', 999.0):.1f} ms`** (Target: $\\le 45.0\\text{{ ms}}$)
- **Estimated Heart Rate:** `{s1s2_detail.get('estimated_heart_rate_bpm', 0.0):.1f} bpm`
- **Morphology Gate Status:** **{s1s2_status}**

## 4. Academic Milestone & Gate Verification

> **SDP4 Milestone (Week 9 Gate):**  
> *"Feasibility gate. A phonocardiogram played through the phantom must be captured with recognisable first and second heart sound structure."*

**Gate Evaluation:** **{gate_status}**  
{'All physical gates satisfied with recognizable S1/S2 heart sound morphology.' if (is_physical and all_technical_gates_pass) else 'Awaiting physical laboratory execution with assembled phantom, verified quiet baseline, and chestpiece.'}

---
*Notice: {METROLOGICAL_DISCLAIMER_PHANTOM}*
"""
    report_md_path.write_text(md_content, encoding="utf-8")

    # Terminal Summary Banner
    print("\n" + "=" * 76)
    print(f"  AUSCULTAFORGE — PHANTOM PCG EXPERIMENT SUMMARY")
    print("=" * 76)
    print(f"  Trial ID          : {trial_id}")
    print(f"  Execution Mode    : {hardware_status}")
    print(f"  Overall Gate      : {gate_status}")
    print(f"  Data Integrity    : {data_integrity_status}")
    print(f"  Acoustic Delay    : {alignment_res.estimated_delay_ms:.3f} ms")
    print(f"  Cross-Correlation : {ncc:.5f} ({alignment_status})")
    print(f"  Coherence (20-250): {coherence_val:.4f} ({coherence_status})")
    print(f"  Acoustic SNR      : {f'{snr_db:.1f} dB' if snr_db is not None else 'N/A'} ({snr_status})")
    print(f"  S1/S2 Morphology  : {s1s2_status} (Match: {s1s2_detail.get('matched_fraction', 0.0)*100:.1f}%, Jitter: {s1s2_detail.get('mean_timing_jitter_ms', 0):.1f}ms)")
    print(f"  Near-Clipping     : {near_clip_frac * 100:.4f}% ({clipping_status})")
    print(f"  Report JSON       : {report_json_path}")
    print(f"  Report Markdown   : {report_md_path}")
    print("=" * 76 + "\n")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AuscultaForge Automated Acoustic Phantom PCG Experiment Runner."
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Espressif USB CDC COM port for live ESP32-S3 acquisition (must be dynamically discovered, e.g. COM3).",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=ROOT / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav",
        help="Path to clinical reference PCG WAV file.",
    )
    parser.add_argument(
        "--captured-wav",
        type=Path,
        default=None,
        help="Path to pre-recorded captured WAV file for offline analysis.",
    )
    parser.add_argument(
        "--quiet-session",
        type=Path,
        default=None,
        help="Path to quiet baseline session JSON or WAV file for real 20-500 Hz SNR computation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiments/phantom",
        help="Directory where experiment trial outputs will be stored.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in deterministic simulated acoustic phantom channel mode (no hardware required).",
    )
    parser.add_argument(
        "--play-audio",
        action="store_true",
        help="Automatically trigger audio playback through default PC sound card during acquisition.",
    )
    parser.add_argument(
        "--verify-audio-routing",
        action="store_true",
        help="Operator attestation that PC line out is physically connected to PAM8403 and exciter is powered.",
    )
    parser.add_argument(
        "--operator",
        default="Ege_Kaan_Ozan",
        help="Operator names.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Optional trial notes.",
    )
    args = parser.parse_args()

    try:
        report = execute_phantom_pcg_experiment(
            reference_wav_path=args.reference,
            output_dir=args.output_dir,
            port=args.port,
            captured_wav_path=args.captured_wav,
            quiet_session_path=args.quiet_session,
            simulate=args.simulate,
            play_audio=args.play_audio,
            audio_routing_verified=args.verify_audio_routing,
            operator=args.operator,
            notes=args.notes,
        )
        if args.simulate:
            return 0 if report.get("gate_status") == "SIMULATION_VERIFIED_PHYSICAL_PENDING" else 1
        return 0 if report["gates"]["overall_pass"] else 1
    except Exception as exc:
        print(f"\n[ERROR] Experiment execution failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
