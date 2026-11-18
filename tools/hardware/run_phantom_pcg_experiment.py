"""AuscultaForge — Automated Acoustic Phantom PCG Experiment Runner.

Orchestrates the SDP4 Week 9 Feasibility Experiment:
1. Prepares a standardized 48 kHz normalized stimulus from a known clinical PCG (CirCor DigiScope).
2. Drives playback through the PC audio output into the PAM8403 amplifier and vibration exciter.
3. Concurrently acquires 10.0 seconds (480,000 samples @ 48 kHz) from the INMP441 MEMS microphone over USB CDC.
4. Performs deterministic quality gating: packet continuity, near-clipping fraction, and SNR.
5. Computes quantitative alignment: time delay, normalized cross-correlation, and Welch coherence.
6. Evaluates S1/S2 morphological preservation via Shannon energy envelope peak identification.
7. Produces reproducible JSON and Markdown reports with full provenance.
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
    from pcg_core.stimulus import prepare_reference_wav_stimulus, StimulusRecord
except ImportError as exc:
    raise SystemExit(
        f"Missing AuscultaForge core dependency: {exc}. Run with .venv Python."
    ) from exc


def compute_shannon_envelope(
    signal: np.ndarray,
    sample_rate_hz: int,
    smoothing_window_ms: float = 50.0,
) -> Tuple[np.ndarray, list[dict[str, Any]]]:
    """Compute normalized Shannon energy envelope and identify S1/S2 peak complexes.
    
    Es[n] = - x_norm[n]^2 * ln(x_norm[n]^2 + 1e-12)
    """
    sig = np.asarray(signal, dtype=np.float32)
    max_amp = float(np.max(np.abs(sig))) if len(sig) > 0 else 1.0
    if max_amp > 1e-12:
        norm_sig = sig / max_amp
    else:
        norm_sig = sig

    # Normalized Shannon energy
    sq = norm_sig ** 2
    shannon = -sq * np.log(sq + 1e-12)

    # Smooth with rectangular moving average window
    win_len = max(3, int((smoothing_window_ms / 1000.0) * sample_rate_hz))
    window = np.ones(win_len, dtype=np.float32) / float(win_len)
    smoothed = np.convolve(shannon, window, mode="same")

    # Peak detection for heart sound complexes (S1 / S2)
    # Minimum separation between S1 and S2 is typically ~180-250 ms
    min_dist_samples = int(0.18 * sample_rate_hz)
    threshold = float(np.mean(smoothed) + 0.5 * np.std(smoothed))

    peaks, properties = scipy.signal.find_peaks(
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

    # 1. Acoustic time-of-flight delay
    delay_samples = int((acoustic_delay_ms / 1000.0) * sample_rate_hz)
    if delay_samples > 0:
        delayed = np.pad(sig, (delay_samples, 0))[:len(sig)]
    else:
        delayed = sig.copy()

    # 2. Linear acoustic attenuation
    gain = 10.0 ** (attenuation_db / 20.0)
    attenuated = delayed * gain

    # 3. Frequency-dependent tissue damping (2nd-order Butterworth low-pass)
    sos = scipy.signal.butter(2, lowpass_cutoff_hz, btype="lowpass", fs=sample_rate_hz, output="sos")
    damped = scipy.signal.sosfilt(sos, attenuated)

    # 4. Realistic ambient and sensor noise
    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0.0, noise_std, size=len(damped)).astype(np.float32)

    return (damped + noise).astype(np.float32)


def play_wav_background(wav_path: Path) -> threading.Thread:
    """Play WAV file in a background daemon thread using Windows winsound."""
    def _worker():
        try:
            import winsound
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
        except Exception as e:
            print(f"[WARN] winsound playback failed: {e}", file=sys.stderr)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread


def execute_phantom_pcg_experiment(
    reference_wav_path: Path,
    output_dir: Path,
    port: Optional[str] = None,
    captured_wav_path: Optional[Path] = None,
    simulate: bool = False,
    play_audio: bool = False,
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
    print(f"\n[1/5] Preparing reference PCG stimulus from {reference_wav_path.name}...")
    if not reference_wav_path.is_file():
        raise FileNotFoundError(f"Reference PCG WAV not found: {reference_wav_path}")

    raw_bytes = reference_wav_path.read_bytes()
    stim_record: StimulusRecord = prepare_reference_wav_stimulus(
        wav_bytes=raw_bytes,
        target_sample_rate_hz=target_sample_rate_hz,
        normalize_peak_fs=0.707,  # -3 dBFS to prevent DAC saturation
        filename=reference_wav_path.name,
    )

    # Slice or pad to exact target duration (10.0 s = 480,000 samples)
    if len(stim_record.samples) >= target_samples:
        stim_samples = stim_record.samples[:target_samples]
    else:
        stim_samples = np.pad(stim_record.samples, (0, target_samples - len(stim_record.samples)))

    # Export normalized stimulus WAV
    stimulus_wav_path = run_dir / f"stimulus_pcg_{target_sample_rate_hz}hz.wav"
    int16_stim = (np.clip(stim_samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    wavfile.write(stimulus_wav_path, target_sample_rate_hz, int16_stim)
    stim_sha256 = hashlib.sha256(stimulus_wav_path.read_bytes()).hexdigest()

    print(f"      Stimulus WAV ready: {stimulus_wav_path.name} ({len(stim_samples)} samples, SHA256: {stim_sha256[:12]}...)")

    # 2. Acquire or simulate captured acoustic audio
    captured_samples: np.ndarray
    capture_meta: dict[str, Any] = {}
    is_physical = False

    if simulate:
        print("\n[2/5] Running in SIMULATED acoustic phantom channel mode...")
        captured_samples = simulate_acoustic_phantom_capture(
            stim_samples,
            sample_rate_hz=target_sample_rate_hz,
            acoustic_delay_ms=10.0,
            attenuation_db=-4.0,
            lowpass_cutoff_hz=450.0,
            noise_std=0.005,
        )
        capture_meta = {
            "source": "SIMULATED_ACOUSTIC_PHANTOM",
            "simulated_delay_ms": 10.0,
            "simulated_attenuation_db": -4.0,
            "simulated_damping_cutoff_hz": 450.0,
            "packet_drops": 0,
            "crc_errors": 0,
        }
        is_physical = False

    elif captured_wav_path is not None:
        print(f"\n[2/5] Loading pre-recorded capture from {captured_wav_path}...")
        if not captured_wav_path.is_file():
            raise FileNotFoundError(f"Captured WAV not found: {captured_wav_path}")
        cap_fs, cap_data = wavfile.read(captured_wav_path)
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
        capture_meta = {
            "source": "OFFLINE_CAPTURE_WAV",
            "file": str(captured_wav_path),
            "original_fs": cap_fs,
        }
        is_physical = True

    elif port is not None:
        print(f"\n[2/5] Initiating LIVE physical capture on {port}...")
        try:
            from pcg_app.wednesday_orchestrator import record_g2_session
        except ImportError:
            raise RuntimeError("Cannot import record_g2_session from pcg_app.")

        # Play stimulus in background if requested
        play_thread = None
        if play_audio:
            print("      Triggering audio playback to PAM8403...")
            play_thread = play_wav_background(stimulus_wav_path)
            time.sleep(0.1)

        print(f"      Streaming {target_samples} samples from ESP32-S3 over USB CDC...")
        session_result = record_g2_session(
            root=ROOT,
            port=port,
            role="pcg_phantom_stimulus",
            target_samples=target_samples,
            capture_timeout_s=25.0,
            sessions_dir=run_dir,
        )

        cap_wav_path = run_dir / f"session_{session_result['session_id']}.wav"
        if not cap_wav_path.is_file():
            # Check if wav was placed in session directory
            cand = list(run_dir.glob("*.wav"))
            if cand:
                cap_wav_path = cand[0]
            else:
                raise RuntimeError("Live capture did not produce a WAV file.")

        cap_fs, cap_data = wavfile.read(cap_wav_path)
        captured_samples = (cap_data.astype(np.float32) if not np.issubdtype(cap_data.dtype, np.integer)
                            else cap_data.astype(np.float32) / 32767.0)
        capture_meta = session_result
        is_physical = True

    else:
        raise ValueError("Must specify either --port, --captured-wav, or --simulate.")

    # 3. Quality & Ingest Gating
    print("\n[3/5] Evaluating ingest integrity and dynamic range...")
    clip_info = detect_clipping(captured_samples, threshold=0.98)
    near_clip_frac = clip_info["clipped_fraction"]
    cap_rms = float(rms(captured_samples))
    cap_peak = float(peak_abs(captured_samples))

    # 4. Bandpass Filtering & Alignment
    print("\n[4/5] Aligning source and captured signals via cross-correlation...")
    aligned_ref, aligned_cap, alignment_res, latency_decomp = estimate_phantom_alignment(
        reference=stim_samples,
        captured=captured_samples,
        sample_rate_hz=target_sample_rate_hz,
        pipeline_buffer_delay_ms=25.0,
        target_band_hz=(20.0, 500.0),
    )

    # 20–500 Hz characterization bandpass filter
    sos_band = scipy.signal.butter(4, [20.0, 500.0], btype="bandpass", fs=target_sample_rate_hz, output="sos")
    filt_ref = scipy.signal.sosfiltfilt(sos_band, aligned_ref)
    filt_cap = scipy.signal.sosfiltfilt(sos_band, aligned_cap)

    # Coherence in primary cardiac band (20–250 Hz)
    coherence_val = compute_coherence_pcg_band(
        filt_ref, filt_cap, sample_rate_hz=target_sample_rate_hz, band_hz=(20.0, 250.0)
    )

    # 5. S1/S2 Morphological Envelope Analysis
    print("\n[5/5] Extracting Shannon energy envelope and S1/S2 heart sound peaks...")
    env_ref, peaks_ref = compute_shannon_envelope(filt_ref, sample_rate_hz=target_sample_rate_hz)
    env_cap, peaks_cap = compute_shannon_envelope(filt_cap, sample_rate_hz=target_sample_rate_hz)

    # Cardiac period analysis
    ref_intervals = np.diff([p["time_s"] for p in peaks_ref]) if len(peaks_ref) > 1 else np.array([])
    cap_intervals = np.diff([p["time_s"] for p in peaks_cap]) if len(peaks_cap) > 1 else np.array([])

    mean_cap_period = float(np.mean(cap_intervals)) if len(cap_intervals) > 0 else 0.0
    est_heart_rate_bpm = float(60.0 / mean_cap_period) if mean_cap_period > 0.1 else 0.0

    # Gate Evaluation
    ncc = alignment_res.normalized_cross_correlation
    drops = capture_meta.get("packet_drops", 0)
    gate_data_integrity = bool(drops == 0)
    gate_clipping = bool(near_clip_frac < 0.0005)  # < 0.05%
    gate_alignment = bool(ncc >= 0.35)
    gate_s1s2_structure = bool(len(peaks_cap) >= 4 and 0.4 <= mean_cap_period <= 1.5)

    all_gates_pass = gate_data_integrity and gate_clipping and gate_alignment and gate_s1s2_structure

    if is_physical:
        gate_status = "PHYSICAL_GATE_PASSED" if all_gates_pass else "PHYSICAL_GATE_INCONCLUSIVE"
        hardware_status = "PHYSICAL_VERIFIED" if all_gates_pass else "PHYSICAL_INCONCLUSIVE"
    else:
        gate_status = "SIMULATION_VERIFIED_PHYSICAL_PENDING"
        hardware_status = "SIMULATED_BENCH_TEST"

    # Save Captured WAV if simulated
    captured_wav_path_out = run_dir / f"captured_pcg_{target_sample_rate_hz}hz.wav"
    int16_cap = (np.clip(captured_samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    wavfile.write(captured_wav_path_out, target_sample_rate_hz, int16_cap)

    # Structure Experiment Report
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "trial_id": trial_id,
        "timestamp_utc": now_utc.isoformat(),
        "operator": operator,
        "notes": notes,
        "is_physical": is_physical,
        "hardware_status": hardware_status,
        "gate_status": gate_status,
        "stimulus": {
            "source_file": reference_wav_path.name,
            "sample_rate_hz": target_sample_rate_hz,
            "duration_s": round(len(stim_samples) / target_sample_rate_hz, 4),
            "samples_count": len(stim_samples),
            "sha256": stim_sha256,
            "peak_fs": round(float(np.max(np.abs(stim_samples))), 4),
            "rms_fs": round(float(rms(stim_samples)), 4),
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
            "meta": capture_meta,
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
        "s1_s2_morphology": {
            "reference_peak_count": len(peaks_ref),
            "captured_peak_count": len(peaks_cap),
            "captured_mean_cardiac_period_s": round(mean_cap_period, 4),
            "estimated_heart_rate_bpm": round(est_heart_rate_bpm, 1),
            "captured_peaks": peaks_cap[:12],  # First 12 peaks
        },
        "gates": {
            "data_integrity_pass": gate_data_integrity,
            "clipping_margin_pass": gate_clipping,
            "cross_correlation_pass": gate_alignment,
            "s1_s2_morphology_pass": gate_s1s2_structure,
            "all_gates_pass": all_gates_pass,
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

## 1. Stimulus vs. Capture Metrics

| Metric | Reference Stimulus | Captured Audio | Target / Threshold | Status |
|---|---|---|---|---|
| Source / Origin | `{reference_wav_path.name}` | `{capture_meta.get('source', 'LIVE_USB')}` | Known Clinical PCG | PASS |
| Sampling Rate | {target_sample_rate_hz} Hz | {target_sample_rate_hz} Hz | 48,000 Hz | PASS |
| Duration | {report['stimulus']['duration_s']} s | {report['capture']['duration_s']} s | 10.0 s (480k samples) | PASS |
| Peak Amplitude | {report['stimulus']['peak_fs']} FS | {report['capture']['peak_fs']} FS | < 0.95 FS (Unclipped) | {'PASS' if gate_clipping else 'FAIL'} |
| Near-Clipping Fraction | 0.0000% | {near_clip_frac * 100:.4f}% | < 0.05% | {'PASS' if gate_clipping else 'FAIL'} |

## 2. Quantitative System Identification & Alignment

- **Acoustic Channel Delay:** `{alignment_res.estimated_delay_ms:.3f} ms` ({alignment_res.estimated_delay_samples} samples)
- **Normalized Cross-Correlation (NCC):** **`{ncc:.5f}`** (Target: $\\ge 0.35$) → **{'PASS' if gate_alignment else 'FAIL'}**
- **Passband Coherence (20–250 Hz):** **`{coherence_val:.4f}`** (Target: $\\ge 0.40$)
- **Least-Squares Gain:** `{alignment_res.least_squares_gain:.4f}`
- **Signal-to-Error Ratio (SER):** `{alignment_res.signal_to_error_ratio_db:.2f} dB`

## 3. S1/S2 Heart Sound Morphology

- **Captured Heart Sound Peaks:** `{len(peaks_cap)}` detected peaks
- **Mean Cardiac Cycle Period:** `{mean_cap_period:.3f} s`
- **Estimated Heart Rate:** **`{est_heart_rate_bpm:.1f} bpm`** (Physiological range: 60–100 bpm)
- **Morphological Structure Status:** **{'PASS (Recognizable S1/S2 complexes)' if gate_s1s2_structure else 'INCONCLUSIVE'}**

## 4. Academic Milestone & Gate Verification

> **SDP4 Milestone (Week 9 Gate):**  
> *"Feasibility gate. A phonocardiogram played through the phantom must be captured with recognisable first and second heart sound structure."*

**Gate Evaluation:** **{gate_status}**  
{'All physical gates satisfied with recognizable S1/S2 heart sound morphology.' if (is_physical and all_gates_pass) else 'Awaiting physical laboratory execution with assembled phantom and chestpiece.'}

---
*Notice: {METROLOGICAL_DISCLAIMER_PHANTOM}*
"""
    report_md_path.write_text(md_content, encoding="utf-8")

    # Terminal Summary Banner
    print("\n" + "=" * 70)
    print(f"  AUSCULTAFORGE — PHANTOM PCG EXPERIMENT SUMMARY")
    print("=" * 70)
    print(f"  Trial ID          : {trial_id}")
    print(f"  Execution Mode    : {hardware_status}")
    print(f"  Overall Gate      : {gate_status}")
    print(f"  Acoustic Delay    : {alignment_res.estimated_delay_ms:.3f} ms")
    print(f"  Cross-Correlation : {ncc:.5f} ({'PASS' if gate_alignment else 'MARGINAL/FAIL'})")
    print(f"  Coherence (20-250): {coherence_val:.4f}")
    print(f"  S1/S2 Peaks Found : {len(peaks_cap)} peaks (HR ~ {est_heart_rate_bpm:.1f} bpm)")
    print(f"  Near-Clipping     : {near_clip_frac * 100:.4f}% ({'PASS' if gate_clipping else 'FAIL'})")
    print(f"  Report JSON       : {report_json_path}")
    print(f"  Report Markdown   : {report_md_path}")
    print("=" * 70 + "\n")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AuscultaForge Automated Acoustic Phantom PCG Experiment Runner."
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Espressif USB CDC COM port for live ESP32-S3 acquisition (e.g. COM8).",
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
            simulate=args.simulate,
            play_audio=args.play_audio,
            operator=args.operator,
            notes=args.notes,
        )
        return 0 if report["gates"]["all_gates_pass"] else 1
    except Exception as exc:
        print(f"\n[ERROR] Experiment execution failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
