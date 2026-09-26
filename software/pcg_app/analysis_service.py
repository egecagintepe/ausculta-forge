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
from .display_pipeline import decimate_min_max


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
        error_signal = aligned_cap - aligned_ref

        # 3. Decimated waveform series for visual comparison (bounded points)
        target_pts = max(32, min(max_waveform_points, 1200))
        dec_ref = decimate_min_max(aligned_ref, target_pts)
        dec_cap = decimate_min_max(aligned_cap, target_pts)
        dec_err = decimate_min_max(error_signal, target_pts)

        # Align length if rounding varied by 1 point
        min_pts = min(len(dec_ref), len(dec_cap), len(dec_err))
        dec_ref = dec_ref[:min_pts]
        dec_cap = dec_cap[:min_pts]
        dec_err = dec_err[:min_pts]

        time_axis_ms = [
            round(float(t), 3)
            for t in np.linspace(0, val_result.overlap_duration_s * 1000.0, min_pts)
        ]

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
