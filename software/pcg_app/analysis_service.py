"""AuscultaForge — Session Analysis & Reference-vs-Capture Service.

Orchestrates offline PCG session inspection, safe reference WAV asset importation,
and quantitative engineering comparison (reference-vs-capture validation) without
reinventing DSP mathematics.

All quantitative algorithms delegate to pcg_core (validation, analysis, metrics, dsp).
Results strictly report objective engineering metrics (delay, cross-correlation,
least-squares gain, RMSE, NRMSE, SER, spectral differences, coherence). No clinical
diagnoses or subjective health scores are produced.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import re
from typing import Any, Optional
import uuid

import numpy as np
import scipy.signal
from scipy.io import wavfile

from pcg_core.validation import (
    validate_signals,
    estimate_delay_and_align,
    compute_least_squares_gain,
    load_wav_as_float32,
    ValidationResult,
)
from pcg_core.analysis import compute_spectrogram_data
from pcg_core.metrics import rms, peak_abs, crest_factor
from pcg_core.dsp import StreamingBandpass
from pcg_core.recording import validate_session_id, get_session
from pcg_core.experiment import get_git_commit_sha
from pcg_core.scientific import (
    SignalQualityConfig,
    SignalCharacterizationResult,
    compute_signal_quality,
    WelchConfig,
    SpectralAnalysisResult,
    compute_welch_psd,
    resample_analysis_signal,
    EnvelopeLabConfig,
    EnvelopeLabResult,
    compute_envelope_lab,
    SystemIdConfig,
    SystemIdentificationResult,
    estimate_siso_system_id,
)
from pcg_core.scientific_config import (
    get_analysis_profile,
    list_analysis_profiles,
    GENERAL_PCG_V1,
    RAW_INTEGRITY_V1,
    BROADBAND_SYSTEM_ID_V1,
)
from .display_pipeline import decimate_min_max


def subsample_curve(
    x_vals: np.ndarray | list[float],
    y_vals: np.ndarray | list[float],
    max_points: int = 300,
) -> tuple[list[float], list[float]]:
    """Subsample an (x, y) continuous curve to at most max_points monotonically."""
    x_arr = np.asarray(x_vals, dtype=np.float64)
    y_arr = np.asarray(y_vals, dtype=np.float64)
    n = len(x_arr)
    if n <= max_points or max_points < 2:
        return [round(float(x), 4) for x in x_arr], [round(float(y), 4) for y in y_arr]
    indices = np.round(np.linspace(0, n - 1, max_points)).astype(int)
    indices = np.unique(indices)
    return [round(float(x_arr[i]), 4) for i in indices], [round(float(y_arr[i]), 4) for i in indices]


SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_identifier(identifier: str, entity_name: str = "id", base_dir: Optional[Path] = None) -> str:
    """Validate that an ID contains strictly safe characters and does not escape base_dir."""
    if not identifier or not isinstance(identifier, str):
        raise ValueError(f"{entity_name} must be a non-empty string.")

    clean_id = identifier.strip()
    if not clean_id or not SAFE_ID_PATTERN.match(clean_id):
        raise ValueError(
            f"Invalid {entity_name} format: {identifier!r}. Only alphanumeric, '_', and '-' characters allowed."
        )

    if base_dir is not None:
        root = base_dir.resolve()
        target = (root / clean_id).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            raise ValueError(f"Path traversal detected: {identifier!r} escapes {base_dir}")

    return clean_id


def decimate_aligned_traces_shared_time(
    reference: np.ndarray,
    capture: np.ndarray,
    sample_rate_hz: float,
    max_display_points: int = 600,
) -> tuple[list[float], list[float], list[float], list[float]]:
    """Produce a shared-time, peak-preserving decimated trace representation.

    Every array element in time_ms, reference, capture, and error refers to the
    EXACT SAME original aligned sample index/time, ensuring truthful pointwise temporal
    alignment without independent bucket offsets.

    Algorithm:
    1. Divide aligned samples into bounded buckets (n_buckets <= (max_display_points - 2) // 4).
    2. In each bucket, find candidate extrema indices (argmin and argmax) from BOTH reference and capture.
    3. Take the union of candidate indices plus boundary points (0 and N-1).
    4. Sort chronologically.
    5. Sample reference, capture, and error = (capture - reference) at those exact common indices.
    6. Compute exact time_ms from sample indices.

    Returns:
        (time_ms, reference_pts, capture_pts, error_pts) where all arrays share
        the same length and timestamps, and error[i] == capture[i] - reference[i].
    """
    n_samples = min(len(reference), len(capture))
    if n_samples == 0:
        return [], [], [], []

    ref_arr = np.asarray(reference[:n_samples], dtype=np.float32)
    cap_arr = np.asarray(capture[:n_samples], dtype=np.float32)

    if n_samples <= max_display_points:
        chosen_indices = np.arange(n_samples, dtype=int)
    else:
        # Each bucket produces up to 4 candidate indices: argmin/argmax of ref and cap.
        # Allocate buckets so candidate count <= max_display_points.
        n_buckets = max(1, (max_display_points - 2) // 4)
        bucket_edges = np.linspace(0, n_samples, n_buckets + 1, dtype=int)

        candidate_set: set[int] = {0, n_samples - 1}

        for b in range(n_buckets):
            start_idx = int(bucket_edges[b])
            end_idx = int(bucket_edges[b + 1])
            if start_idx >= end_idx:
                continue

            ref_slice = ref_arr[start_idx:end_idx]
            cap_slice = cap_arr[start_idx:end_idx]

            candidate_set.add(start_idx + int(np.argmin(ref_slice)))
            candidate_set.add(start_idx + int(np.argmax(ref_slice)))
            candidate_set.add(start_idx + int(np.argmin(cap_slice)))
            candidate_set.add(start_idx + int(np.argmax(cap_slice)))

        chosen_indices = np.array(sorted(candidate_set), dtype=int)

        if len(chosen_indices) > max_display_points:
            step = (len(chosen_indices) - 1) / (max_display_points - 1)
            sub_idx = [int(round(i * step)) for i in range(max_display_points)]
            chosen_indices = np.unique(chosen_indices[sub_idx])

    t_ms = (chosen_indices / float(sample_rate_hz)) * 1000.0
    ref_sampled = ref_arr[chosen_indices]
    cap_sampled = cap_arr[chosen_indices]

    time_ms_list = [round(float(t), 3) for t in t_ms]
    ref_list = [round(float(v), 5) for v in ref_sampled]
    cap_list = [round(float(v), 5) for v in cap_sampled]
    err_list = [round(float(c - r), 5) for c, r in zip(cap_list, ref_list)]

    return time_ms_list, ref_list, cap_list, err_list


class AnalysisService:
    """Application-layer service orchestrating PCG analysis and reference-vs-capture workbench."""

    def __init__(
        self,
        assets_dir: str | Path = "experiments/analysis-assets",
        analysis_dir: str | Path = "experiments/analysis",
        sessions_dir: str | Path = "experiments/sessions",
    ) -> None:
        self.assets_dir = Path(assets_dir)
        self.analysis_dir = Path(analysis_dir)
        self.sessions_dir = Path(sessions_dir)

        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Reference WAV Asset Management
    # =========================================================================

    def import_reference_wav(
        self,
        file_bytes: bytes,
        original_filename: str = "reference.wav",
    ) -> dict[str, Any]:
        """Import, validate, and store a known PCG reference WAV file.

        Requirements:
        - WAV format only (checked via wavfile header).
        - Reject empty or corrupt files (< 16 samples).
        - Inspect sample rate, channels, and duration.
        - Enforce mono channel policy for this milestone (reject stereo with clear error).
        - Compute SHA-256 and generate safe internal asset ID.
        - Do not trust original filename or server filesystem paths.
        """
        if not file_bytes or len(file_bytes) < 44:
            raise ValueError("Invalid WAV file: data is empty or too short for a valid WAV header.")

        # Read WAV bytes
        try:
            buf = io.BytesIO(file_bytes)
            fs, data = wavfile.read(buf)
        except Exception as e:
            raise ValueError(f"Corrupt or unsupported WAV format: {e}") from e

        if fs <= 0:
            raise ValueError(f"Invalid WAV sample rate: {fs} Hz. Sample rate must be positive.")

        # Check channels policy: Mono required
        if data.ndim > 1:
            n_channels = data.shape[1] if data.ndim >= 2 else 2
            if n_channels > 1:
                raise ValueError(
                    f"Stereo/multichannel audio ({n_channels} channels) is not supported in this milestone. "
                    "Please provide a single-channel mono PCG WAV file."
                )
            data = data.squeeze()

        total_samples = len(data)
        if total_samples < 16:
            raise ValueError(f"Audio signal too short: only {total_samples} samples found (minimum 16 required).")

        duration_s = float(total_samples / fs)

        # Compute SHA-256
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # Generate safe asset ID based on hash prefix
        asset_id = f"ref_{sha256_hash[:12]}"

        # Sanitize display filename (keep clean basename only, no directory components)
        clean_name = Path(original_filename).name.strip()
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", clean_name)
        if not clean_name:
            clean_name = f"{asset_id}.wav"

        # Save WAV file and metadata sidecar
        wav_target = self.assets_dir / f"{asset_id}.wav"
        meta_target = self.assets_dir / f"{asset_id}.json"

        # Write WAV to disk if not already present with identical hash
        if not wav_target.exists():
            with open(wav_target, "wb") as f:
                f.write(file_bytes)

        metadata: dict[str, Any] = {
            "asset_id": asset_id,
            "filename": clean_name,
            "sha256": sha256_hash,
            "sample_rate_hz": int(fs),
            "channels": 1,
            "total_samples": int(total_samples),
            "duration_s": round(duration_s, 4),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        with open(meta_target, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def list_reference_assets(self) -> list[dict[str, Any]]:
        """List all imported reference WAV assets sorted by creation timestamp descending."""
        assets: list[dict[str, Any]] = []
        for meta_path in self.assets_dir.glob("ref_*.json"):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    assets.append(data)
            except Exception:
                pass

        assets.sort(key=lambda a: a.get("created_at_utc", ""), reverse=True)
        return assets

    def get_reference_asset(self, asset_id: str) -> Optional[dict[str, Any]]:
        """Retrieve metadata for a reference asset safely."""
        valid_id = validate_identifier(asset_id, "asset_id", self.assets_dir)
        meta_path = self.assets_dir / f"{valid_id}.json"
        if not meta_path.exists():
            return None

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete_reference_asset(self, asset_id: str) -> bool:
        """Delete an imported reference WAV asset and its metadata sidecar."""
        valid_id = validate_identifier(asset_id, "asset_id", self.assets_dir)
        wav_path = self.assets_dir / f"{valid_id}.wav"
        meta_path = self.assets_dir / f"{valid_id}.json"

        removed = False
        if wav_path.exists():
            wav_path.unlink()
            removed = True
        if meta_path.exists():
            meta_path.unlink()
            removed = True

        return removed

    # =========================================================================
    # Individual Session Analysis Summary
    # =========================================================================

    def get_session_analysis_summary(
        self,
        session_id: str,
        max_waveform_points: int = 600,
    ) -> dict[str, Any]:
        """Compute an offline engineering analysis summary and decimated preview for a recorded session.

        Does NOT load raw full-rate arrays into the frontend; returns bounded,
        peak-preserving decimated series and factual engineering metrics.
        """
        valid_id = validate_session_id(session_id, self.sessions_dir)
        sess_dict = get_session(valid_id, self.sessions_dir)
        if sess_dict is None:
            raise FileNotFoundError(f"Recorded session not found: {session_id}")

        wav_path = self.sessions_dir / valid_id / "raw.wav"
        if not wav_path.exists():
            raise FileNotFoundError(f"Session audio file not found: {wav_path}")

        raw_samples, fs = load_wav_as_float32(wav_path)
        if len(raw_samples) == 0:
            raise ValueError(f"Session {session_id} audio contains zero samples.")

        # Filter the signal through provisional PCG bandpass (20-600 Hz)
        nyq = fs / 2.0
        high_cut = min(600.0, nyq - 1.0)
        low_cut = min(20.0, high_cut * 0.5)
        sos = scipy.signal.butter(4, [low_cut, high_cut], btype="bandpass", fs=fs, output="sos")
        filtered_samples = scipy.signal.sosfilt(sos, raw_samples).astype(np.float32)

        # Raw metrics
        raw_rms_val = float(rms(raw_samples))
        raw_pk_val = float(peak_abs(raw_samples))
        raw_cf_val = float(crest_factor(raw_samples))

        # Filtered metrics
        filt_rms_val = float(rms(filtered_samples))
        filt_pk_val = float(peak_abs(filtered_samples))
        filt_cf_val = float(crest_factor(filtered_samples))

        # Spectral analysis via pcg_core.analysis
        spec_data = compute_spectrogram_data(filtered_samples, fs=fs)

        # Bounded peak-preserving waveform decimation for UI rendering
        target_pts = max(32, min(max_waveform_points, 1200))
        decimated_raw = decimate_min_max(raw_samples, target_pts)
        decimated_filt = decimate_min_max(filtered_samples, target_pts)

        duration_s = float(len(raw_samples) / fs)
        n_pts = len(decimated_raw)
        time_points_s = [round(float(t), 4) for t in np.linspace(0, duration_s, n_pts)]

        # Decimated Welch PSD for spectral preview (0-1000 Hz)
        nperseg = min(512, len(filtered_samples))
        if nperseg >= 32:
            f_welch, pxx = scipy.signal.welch(filtered_samples, fs=fs, nperseg=nperseg)
            mask = f_welch <= 1000.0
            f_welch = f_welch[mask]
            pxx = pxx[mask]
            # Convert to dB relative to full-scale
            pxx_db = 10.0 * np.log10(np.maximum(pxx, 1e-12))
            # Subsample if more than 128 points
            if len(f_welch) > 128:
                step = len(f_welch) / 128.0
                indices = [int(i * step) for i in range(128)]
                spec_freqs = [round(float(f_welch[i]), 1) for i in indices]
                spec_powers = [round(float(pxx_db[i]), 2) for i in indices]
            else:
                spec_freqs = [round(float(f), 1) for f in f_welch]
                spec_powers = [round(float(p), 2) for p in pxx_db]
        else:
            spec_freqs = []
            spec_powers = []

        return {
            "session_id": valid_id,
            "started_at_utc": sess_dict.get("started_at_utc", ""),
            "ended_at_utc": sess_dict.get("ended_at_utc", ""),
            "duration_s": round(duration_s, 4),
            "sample_rate_hz": fs,
            "total_samples": len(raw_samples),
            "total_blocks": sess_dict.get("total_blocks", 0),
            "acquisition_mode": sess_dict.get("acquisition_mode", "offline"),
            "source": sess_dict.get("source", "unknown"),
            "termination_reason": sess_dict.get("termination_reason", "completed"),
            "raw_wav_sha256": sess_dict.get("raw_wav_sha256", ""),
            "git_commit_sha": sess_dict.get("git_commit_sha"),
            "device_info": sess_dict.get("device_info"),
            "stream_quality": sess_dict.get("stream_quality", {}),
            "metrics": {
                "raw_rms": round(raw_rms_val, 5),
                "raw_peak": round(raw_pk_val, 5),
                "raw_crest_factor": round(raw_cf_val, 3),
                "filtered_rms": round(filt_rms_val, 5),
                "filtered_peak": round(filt_pk_val, 5),
                "filtered_crest_factor": round(filt_cf_val, 3),
                "dominant_frequency_hz": round(spec_data.peak_frequency_hz, 2),
                "band_energy_ratios": spec_data.band_energy_ratios,
            },
            "display": {
                "time_points_s": time_points_s,
                "raw_points": [round(float(v), 5) for v in decimated_raw],
                "filtered_points": [round(float(v), 5) for v in decimated_filt],
                "spectrum_frequencies_hz": spec_freqs,
                "spectrum_power_db": spec_powers,
            },
        }

    # =========================================================================
    # Reference vs Capture Comparison
    # =========================================================================

    def compare_reference_and_capture(
        self,
        asset_id: str,
        session_id: str,
        max_waveform_points: int = 600,
    ) -> dict[str, Any]:
        """Perform quantitative engineering validation comparing a reference asset against a captured session.

        Reuses pcg_core.validation mathematics:
        - Resampling capture if sample rates differ
        - Delay estimation and alignment via cross-correlation
        - Least-squares gain estimation and RMS/peak gain ratios
        - Normalized cross-correlation, RMSE, NRMSE, SER
        - Spectral difference and magnitude-squared coherence
        - Peak-preserving decimated display series (aligned reference, capture, and error)

        Persists a versioned JSON report under experiments/analysis/<analysis_id>/comparison.json.
        """
        valid_asset_id = validate_identifier(asset_id, "asset_id", self.assets_dir)
        valid_sess_id = validate_session_id(session_id, self.sessions_dir)

        asset_meta = self.get_reference_asset(valid_asset_id)
        if asset_meta is None:
            raise FileNotFoundError(f"Reference asset not found: {asset_id}")

        sess_meta = get_session(valid_sess_id, self.sessions_dir)
        if sess_meta is None:
            raise FileNotFoundError(f"Capture session not found: {session_id}")

        ref_path = self.assets_dir / f"{valid_asset_id}.wav"
        cap_path = self.sessions_dir / valid_sess_id / "raw.wav"

        ref_samples, ref_fs = load_wav_as_float32(ref_path)
        cap_samples, cap_fs = load_wav_as_float32(cap_path)

        # 1. Core validation mathematics via pcg_core.validation
        val_result = validate_signals(
            reference=ref_samples,
            captured=cap_samples,
            reference_fs=ref_fs,
            captured_fs=cap_fs,
            reference_name=asset_meta["filename"],
            captured_name=valid_sess_id,
        )

        # 2. Extract aligned signals for visualization
        cap_matched = cap_samples
        if ref_fs != cap_fs:
            gcd = math.gcd(ref_fs, cap_fs)
            up = ref_fs // gcd
            down = cap_fs // gcd
            cap_matched = scipy.signal.resample_poly(cap_samples, up, down).astype(np.float32)

        aligned_ref, aligned_cap, delay_samples, delay_ms = estimate_delay_and_align(
            ref_samples, cap_matched, val_result.effective_fs
        )
        # 3. Decimated waveform series for visual comparison (shared-time common indices)
        target_pts = max(32, min(max_waveform_points, 1200))
        time_axis_ms, dec_ref, dec_cap, dec_err = decimate_aligned_traces_shared_time(
            aligned_ref, aligned_cap, val_result.effective_fs, target_pts
        )

        # 4. Decimated Spectral comparison curves (Welch PSD, 0–1000 Hz)
        n_samples = len(aligned_ref)
        nperseg = min(512, n_samples)
        if nperseg >= 32:
            f_ref, pxx_ref = scipy.signal.welch(aligned_ref, fs=val_result.effective_fs, nperseg=nperseg)
            f_cap, pxx_cap = scipy.signal.welch(aligned_cap, fs=val_result.effective_fs, nperseg=nperseg)

            mask = f_ref <= 1000.0
            f_eval = f_ref[mask]
            p_ref_db = 10.0 * np.log10(np.maximum(pxx_ref[mask], 1e-12))
            p_cap_db = 10.0 * np.log10(np.maximum(pxx_cap[mask], 1e-12))

            if len(f_eval) > 128:
                step = len(f_eval) / 128.0
                indices = [int(i * step) for i in range(128)]
                spec_freqs = [round(float(f_eval[i]), 1) for i in indices]
                spec_ref = [round(float(p_ref_db[i]), 2) for i in indices]
                spec_cap = [round(float(p_cap_db[i]), 2) for i in indices]
            else:
                spec_freqs = [round(float(f), 1) for f in f_eval]
                spec_ref = [round(float(p), 2) for p in p_ref_db]
                spec_cap = [round(float(p), 2) for p in p_cap_db]
        else:
            spec_freqs, spec_ref, spec_cap = [], [], []

        # 5. Magnitude-Squared Coherence curve (20–1000 Hz)
        coh_nperseg = min(256, n_samples)
        if coh_nperseg >= 32:
            f_coh, cxy = scipy.signal.coherence(
                aligned_ref, aligned_cap, fs=val_result.effective_fs, nperseg=coh_nperseg
            )
            mask_coh = (f_coh >= 0.0) & (f_coh <= 1000.0)
            f_coh_eval = f_coh[mask_coh]
            cxy_eval = cxy[mask_coh]

            if len(f_coh_eval) > 128:
                step = len(f_coh_eval) / 128.0
                indices = [int(i * step) for i in range(128)]
                coh_freqs = [round(float(f_coh_eval[i]), 1) for i in indices]
                coh_values = [round(float(cxy_eval[i]), 4) for i in indices]
            else:
                coh_freqs = [round(float(f), 1) for f in f_coh_eval]
                coh_values = [round(float(c), 4) for c in cxy_eval]
        else:
            coh_freqs, coh_values = [], []

        # 6. Build versioned result model
        now_utc = datetime.now(timezone.utc)
        analysis_id = f"cmp_{now_utc.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        result: dict[str, Any] = {
            "version": "1.0",
            "analysis_id": analysis_id,
            "created_at_utc": now_utc.isoformat(),
            "reference": {
                "asset_id": valid_asset_id,
                "filename": asset_meta["filename"],
                "sha256": asset_meta["sha256"],
                "sample_rate_hz": ref_fs,
                "duration_s": round(float(len(ref_samples) / ref_fs), 4),
                "total_samples": len(ref_samples),
            },
            "capture": {
                "session_id": valid_sess_id,
                "wav_sha256": sess_meta.get("raw_wav_sha256", ""),
                "sample_rate_hz": cap_fs,
                "duration_s": sess_meta.get("duration_s", round(float(len(cap_samples) / cap_fs), 4)),
                "total_samples": sess_meta.get("total_samples", len(cap_samples)),
                "acquisition_mode": sess_meta.get("acquisition_mode", "offline"),
                "source": sess_meta.get("source", "unknown"),
                "termination_reason": sess_meta.get("termination_reason", "completed"),
                "device_info": sess_meta.get("device_info"),
            },
            "alignment": {
                "resampled": val_result.resampled,
                "effective_sample_rate_hz": val_result.effective_fs,
                "delay_samples": val_result.delay_samples,
                "delay_ms": val_result.delay_ms,
                "overlap_samples": val_result.overlap_samples,
                "overlap_duration_s": val_result.overlap_duration_s,
            },
            "metrics": {
                "normalized_cross_correlation": val_result.normalized_cross_correlation,
                "rms_gain_ratio": val_result.gain_ratio_rms,
                "gain_ratio_rms": val_result.gain_ratio_rms,
                "peak_gain_ratio": val_result.gain_ratio_peak,
                "gain_ratio_peak": val_result.gain_ratio_peak,
                "least_squares_gain": val_result.least_squares_gain,
                "rmse": val_result.rmse,
                "normalized_rmse": val_result.normalized_rmse,
                "nrmse": val_result.normalized_rmse,
                "signal_to_error_ratio_db": val_result.signal_to_error_ratio_db,
                "ser_db": val_result.signal_to_error_ratio_db,
                "dominant_frequency_reference_hz": val_result.reference_dominant_hz,
                "dominant_frequency_capture_hz": val_result.captured_dominant_hz,
                "dominant_frequency_difference_hz": val_result.dominant_frequency_diff_hz,
                "band_energy_ratio_diffs": val_result.band_energy_ratio_diffs,
                "mean_coherence_pcg_band": val_result.mean_coherence_pcg_band,
            },
            "display": {
                "time_ms": time_axis_ms,
                "aligned_reference": [round(float(v), 5) for v in dec_ref],
                "aligned_capture": [round(float(v), 5) for v in dec_cap],
                "error": [round(float(v), 5) for v in dec_err],
                "spectrum_frequencies_hz": spec_freqs,
                "spectrum_reference_db": spec_ref,
                "spectrum_capture_db": spec_cap,
                "coherence_frequencies_hz": coh_freqs,
                "coherence_values": coh_values,
            },
            "provenance": {
                "app_version": "1.0.0",
                "git_commit_sha": get_git_commit_sha(),
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "scipy_version": scipy.__version__,
                "analysis_profile_id": "PHANTOM_VALIDATION_V1",
                "analysis_profile_version": "1.0.0",
            },
        }

        # 7. Persist to experiments/analysis/<analysis_id>/comparison.json
        report_dir = self.analysis_dir / analysis_id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "comparison.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return result

    def get_comparison_report(self, analysis_id: str) -> Optional[dict[str, Any]]:
        """Load a persisted comparison report safely."""
        valid_id = validate_identifier(analysis_id, "analysis_id", self.analysis_dir)
        report_file = self.analysis_dir / valid_id / "comparison.json"
        if not report_file.exists():
            return None

        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_comparison_reports(self) -> list[dict[str, Any]]:
        """List summary metadata of all persisted comparison reports sorted newest first."""
        reports: list[dict[str, Any]] = []
        for report_file in self.analysis_dir.glob("cmp_*/comparison.json"):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    reports.append({
                        "analysis_id": data.get("analysis_id", report_file.parent.name),
                        "created_at_utc": data.get("created_at_utc", ""),
                        "reference_asset_id": data.get("reference", {}).get("asset_id"),
                        "reference_filename": data.get("reference", {}).get("filename"),
                        "capture_session_id": data.get("capture", {}).get("session_id"),
                        "normalized_cross_correlation": data.get("metrics", {}).get("normalized_cross_correlation"),
                        "least_squares_gain": data.get("metrics", {}).get("least_squares_gain"),
                        "delay_ms": data.get("alignment", {}).get("delay_ms"),
                        "signal_to_error_ratio_db": data.get("metrics", {}).get("signal_to_error_ratio_db"),
                    })
            except Exception:
                pass

        reports.sort(key=lambda r: r.get("created_at_utc", ""), reverse=True)
        return reports

    # =========================================================================
    # Scientific Signal Characterization & Envelope Lab
    # =========================================================================

    def analyze_session_scientific(
        self,
        session_id: str,
        profile_id: str = "GENERAL_PCG_V1",
        welch_nperseg: int = 2048,
        welch_noverlap: Optional[int] = None,
        max_display_points: int = 600,
    ) -> dict[str, Any]:
        """Perform full-rate scientific signal quality, Welch spectral analysis, and Envelope Lab extraction.

        Strict Separation Rules Enforced:
        1. All quantitative metrics are computed on complete full-rate NumPy arrays.
        2. Display arrays are peak-preserved decimated strictly for browser UI rendering.
        3. Never use decimated display points for scientific conclusions.
        4. Distinguishes digital full-scale saturation hits from physical acoustic overload.
        """
        valid_id = validate_session_id(session_id, self.sessions_dir)
        sess_dict = get_session(valid_id, self.sessions_dir)
        if sess_dict is None:
            raise FileNotFoundError(f"Recorded session not found: {session_id}")

        wav_path = self.sessions_dir / valid_id / "raw.wav"
        if not wav_path.exists():
            raise FileNotFoundError(f"Session audio file not found: {wav_path}")

        raw_samples, fs = load_wav_as_float32(wav_path)
        if len(raw_samples) == 0:
            raise ValueError(f"Session {session_id} audio contains zero samples.")

        # Determine analysis profile and construct Analysis Signal
        try:
            profile = get_analysis_profile(profile_id)
        except KeyError:
            profile = GENERAL_PCG_V1
            profile_id = GENERAL_PCG_V1.profile_id

        if profile_id == "GENERAL_PCG_V1":
            nyq = fs / 2.0
            high_cut = min(600.0, nyq - 1.0)
            low_cut = min(20.0, high_cut * 0.5)
            sos = scipy.signal.butter(4, [low_cut, high_cut], btype="bandpass", fs=fs, output="sos")
            analysis_samples = scipy.signal.sosfilt(sos, raw_samples).astype(np.float32)
        else:
            # RAW or BROADBAND profiles preserve the full bandwidth
            analysis_samples = raw_samples.copy()

        # 1. Full-rate Signal Quality Characterization on Acquisition Representation
        quality_cfg = SignalQualityConfig()
        quality_result = compute_signal_quality(
            signal=raw_samples,
            sample_rate_hz=fs,
            config=quality_cfg,
        )

        # 2. Welch Power Spectral Density on Analysis Signal
        nperseg = min(welch_nperseg, len(analysis_samples))
        if nperseg < 32:
            nperseg = max(16, len(analysis_samples))
        spectral_cfg = WelchConfig(
            nperseg=nperseg,
            noverlap=welch_noverlap,
            window="hann",
            scaling="density",
            detrend="constant",
        )
        spectral_result = compute_welch_psd(
            signal=analysis_samples,
            sample_rate_hz=fs,
            config=spectral_cfg,
        )

        # 3. Envelope Lab on Analysis Signal
        envelope_cfg = EnvelopeLabConfig(
            rms_window_duration_s=0.025,
            tkeo_boundary_policy="replicate",
            psd_band_hz=(40.0, 60.0),
            psd_window_duration_s=0.05,
            psd_overlap_fraction=0.5,
        )
        envelope_result = compute_envelope_lab(
            signal=analysis_samples,
            sample_rate_hz=fs,
            config=envelope_cfg,
        )

        # 4. Generate bounded decimated display representations
        target_pts = max(32, min(max_display_points, 1200))
        dec_raw = decimate_min_max(raw_samples, target_pts)
        dec_analysis = decimate_min_max(analysis_samples, target_pts)
        duration_s = float(len(raw_samples) / fs)
        time_points_s = [round(float(t), 4) for t in np.linspace(0.0, duration_s, len(dec_raw))]

        disp_envelopes: dict[str, Any] = {}
        for env in envelope_result.envelopes.values():
            env_vals = np.array(env.values, dtype=np.float32)
            if len(env_vals) > target_pts:
                dec_env = decimate_min_max(env_vals, target_pts)
                env_t = [round(float(t), 4) for t in np.linspace(0.0, duration_s, len(dec_env))]
            else:
                dec_env = env_vals
                env_t = [round(float(t), 4) for t in env.time_s]
            disp_envelopes[env.algorithm] = {
                "algorithm": env.algorithm,
                "time_s": env_t,
                "values": [round(float(v), 5) for v in dec_env],
            }

        # Subsample spectral PSD for responsive SVG plotting (max 256 points)
        spec_freqs, spec_psd_db = subsample_curve(
            spectral_result.frequencies_hz,
            spectral_result.psd_relative_db,
            max_points=256,
        )

        return {
            "schema_version": "1.0.0",
            "session_id": valid_id,
            "sample_rate_hz": fs,
            "total_samples": len(raw_samples),
            "duration_s": round(duration_s, 4),
            "analysis_profile": profile_id,
            "signal_quality": quality_result.to_dict(),
            "spectral": spectral_result.to_dict(),
            "envelope_lab": envelope_result.to_dict(),
            "display": {
                "time_points_s": time_points_s,
                "raw_signal": [round(float(v), 5) for v in dec_raw],
                "analysis_signal": [round(float(v), 5) for v in dec_analysis],
                "envelopes": disp_envelopes,
                "psd": {
                    "frequencies_hz": spec_freqs,
                    "psd_db": spec_psd_db,
                    "delta_f_hz": spectral_result.frequency_bin_spacing_hz,
                    "n_segments": spectral_result.actual_segments,
                    "db_reference": spectral_result.config.get("relative_db_ref", 1.0),
                },
            },
            "provenance": {
                "app_version": "1.0.0",
                "git_commit_sha": get_git_commit_sha(),
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "scipy_version": scipy.__version__,
                "metrology_notes": [
                    "Full-rate quantitative analysis performed on complete NumPy arrays.",
                    "Display curves are peak-preserved decimated strictly for UI rendering and not used for metrics.",
                    "No clinical diagnosis or acoustic ENOB is inferred.",
                    "Digital saturation reflects full-scale amplitude hits, not proven physical acoustic microphone overload.",
                ],
            },
        }

    # =========================================================================
    # System Identification Foundation (SISO H1 & Coherence)
    # =========================================================================

    def run_system_id(
        self,
        asset_id: str,
        session_id: str,
        config: Optional[SystemIdConfig] = None,
        max_display_points: int = 300,
    ) -> dict[str, Any]:
        """Perform conservative SISO best-linear system identification.

        Estimates H1 FRF, ordinary magnitude-squared coherence, input/output autospectra,
        cross-spectrum, and coherent/residual output spectra.
        """
        valid_asset_id = validate_identifier(asset_id, "asset_id", self.assets_dir)
        valid_sess_id = validate_session_id(session_id, self.sessions_dir)

        asset_meta = self.get_reference_asset(valid_asset_id)
        if asset_meta is None:
            raise FileNotFoundError(f"Reference asset not found: {asset_id}")

        sess_meta = get_session(valid_sess_id, self.sessions_dir)
        if sess_meta is None:
            raise FileNotFoundError(f"Capture session not found: {session_id}")

        ref_path = self.assets_dir / f"{valid_asset_id}.wav"
        cap_path = self.sessions_dir / valid_sess_id / "raw.wav"

        ref_samples, ref_fs = load_wav_as_float32(ref_path)
        cap_samples, cap_fs = load_wav_as_float32(cap_path)

        resampled = False
        working_fs = ref_fs
        if ref_fs != cap_fs:
            cap_samples = resample_analysis_signal(cap_samples, original_fs=cap_fs, target_fs=ref_fs)
            resampled = True
            working_fs = ref_fs

        cfg = config or SystemIdConfig()
        sys_result = estimate_siso_system_id(
            input_signal=ref_samples,
            output_signal=cap_samples,
            sample_rate_hz=working_fs,
            config=cfg,
        )

        # Generate bounded decimated display curves for UI rendering
        f_sub, mag_sub = subsample_curve(sys_result.frequencies_hz, sys_result.h1_magnitude_db, max_points=max_display_points)
        _, phase_sub = subsample_curve(sys_result.frequencies_hz, sys_result.h1_phase_rad, max_points=max_display_points)
        _, phase_deg_sub = subsample_curve(sys_result.frequencies_hz, sys_result.h1_phase_deg, max_points=max_display_points)
        _, coh_sub = subsample_curve(sys_result.frequencies_hz, sys_result.coherence, max_points=max_display_points)
        _, gxx_sub = subsample_curve(sys_result.frequencies_hz, sys_result.gxx_autospectrum, max_points=max_display_points)
        _, gyy_sub = subsample_curve(sys_result.frequencies_hz, sys_result.gyy_autospectrum, max_points=max_display_points)
        _, coh_out_sub = subsample_curve(sys_result.frequencies_hz, sys_result.coherent_output_spectrum, max_points=max_display_points)
        _, res_out_sub = subsample_curve(sys_result.frequencies_hz, sys_result.residual_output_spectrum, max_points=max_display_points)
        _, mask_sub = subsample_curve(
            sys_result.frequencies_hz,
            [1.0 if m else 0.0 for m in sys_result.excited_frequency_mask],
            max_points=max_display_points,
        )

        now_utc = datetime.now(timezone.utc)
        analysis_id = f"sysid_{now_utc.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        report: dict[str, Any] = {
            "schema_version": "1.0.0",
            "analysis_id": analysis_id,
            "created_at_utc": now_utc.isoformat(),
            "reference": {
                "asset_id": valid_asset_id,
                "filename": asset_meta["filename"],
                "sha256": asset_meta["sha256"],
                "sample_rate_hz": ref_fs,
                "duration_s": round(float(len(ref_samples) / ref_fs), 4),
                "total_samples": len(ref_samples),
            },
            "capture": {
                "session_id": valid_sess_id,
                "wav_sha256": sess_meta.get("raw_wav_sha256", ""),
                "sample_rate_hz": cap_fs,
                "resampled": resampled,
                "duration_s": sess_meta.get("duration_s", round(float(len(cap_samples) / cap_fs), 4)),
                "total_samples": sess_meta.get("total_samples", len(cap_samples)),
            },
            "system_id": sys_result.to_dict(),
            "display": {
                "frequency_hz": f_sub,
                "h1_magnitude_db": mag_sub,
                "h1_phase_rad": phase_sub,
                "h1_phase_deg": phase_deg_sub,
                "coherence": coh_sub,
                "gxx": gxx_sub,
                "gyy": gyy_sub,
                "coherent_output_psd": coh_out_sub,
                "residual_output_psd": res_out_sub,
                "excited_energy_mask": [bool(v > 0.5) for v in mask_sub],
            },
            "provenance": {
                "app_version": "1.0.0",
                "git_commit_sha": get_git_commit_sha(),
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "scipy_version": scipy.__version__,
                "analysis_profile_id": "BROADBAND_SYSTEM_ID_V1",
            },
        }

        # Persist report
        report_dir = self.analysis_dir / analysis_id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "system_id.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

    def get_system_id_report(self, analysis_id: str) -> Optional[dict[str, Any]]:
        """Load a persisted system identification report safely."""
        valid_id = validate_identifier(analysis_id, "analysis_id", self.analysis_dir)
        report_file = self.analysis_dir / valid_id / "system_id.json"
        if not report_file.exists():
            return None

        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_system_id_reports(self) -> list[dict[str, Any]]:
        """List summary metadata of all persisted system-ID reports sorted newest first."""
        reports: list[dict[str, Any]] = []
        for report_file in self.analysis_dir.glob("sysid_*/system_id.json"):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sys_dict = data.get("system_id", {})
                    reports.append({
                        "analysis_id": data.get("analysis_id", report_file.parent.name),
                        "created_at_utc": data.get("created_at_utc", ""),
                        "reference_asset_id": data.get("reference", {}).get("asset_id"),
                        "reference_filename": data.get("reference", {}).get("filename"),
                        "capture_session_id": data.get("capture", {}).get("session_id"),
                        "mean_coherence_over_excited_band": sys_dict.get("mean_coherence_over_excited_band"),
                        "excited_bins_count": sys_dict.get("excited_bins_count"),
                        "notes": sys_dict.get("notes", ""),
                    })
            except Exception:
                pass

        reports.sort(key=lambda r: r.get("created_at_utc", ""), reverse=True)
        return reports
