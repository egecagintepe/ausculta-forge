"""AuscultaForge — Signal Quality & Acoustic Diagnostics Doctor.

Performs bounded, mathematically rigorous signal-health characterization:
- Normalized RMS and peak digital headroom utilization
- Crest factor (dynamic burst vs continuous noise ratio)
- Digital rail saturation hits (>= 0.999 FS)
- DC bias offset detection
- Near-silence detection (< -60 dBFS)
- 50 Hz power-mains tonal frequency candidate detection
- I2S PCM container bit-alignment check

STRICT SCIENTIFIC BOUNDARIES:
1. Physical SPL (Pa or dB SPL) is NEVER reported without certified acoustic calibration.
2. Microphone self-noise is NEVER reported from arbitrary auscultation data.
3. Near silence is an electroacoustic signal symptom, NOT proof of physical sensor destruction.
4. A 50 Hz spectral peak is an unconfirmed hypothesis, NOT proven mains hum.
5. Signal quality is an engineering diagnostic, NEVER a medical or clinical diagnosis.
6. When insufficient data exists, reports NOT EVALUATED rather than GOOD.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import numpy as np

from .fault_catalog import Subsystem, Severity, EvidenceOrigin
from .event_model import DiagnosticEvent
from .flight_recorder import FlightRecorderJournal, get_flight_recorder


@dataclass(slots=True)
class SignalQualitySnapshot:
    """Scientific signal quality evaluation snapshot."""
    sample_count: int
    duration_s: float
    sample_rate_hz: int
    source_type: str
    rms_fs: float
    peak_fs: float
    crest_factor: float
    clipping_hits: int
    clipping_fraction: float
    dc_offset_fs: float
    zero_crossing_rate: float
    mains_50hz_ratio: Optional[float] = None
    repeated_sample_run_max: int = 1
    is_near_silence: bool = False
    is_clipping: bool = False
    is_excessive_dc: bool = False
    is_suspicious_alignment: bool = False
    is_evaluated: bool = True
    active_fault_codes: list[str] = field(default_factory=list)
    scientific_provenance: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SignalQualityDoctor:
    """Mathematical signal quality and acoustic anomaly detector."""

    def __init__(
        self,
        flight_recorder: Optional[FlightRecorderJournal] = None,
        silence_threshold_fs: float = 0.001,   # -60 dBFS
        clipping_threshold_fs: float = 0.999,  # >= 0.999 FS
        clipping_fraction_limit: float = 0.001, # 0.1% of samples
        dc_offset_limit_fs: float = 0.10,      # 10% FS
        min_evaluation_samples: int = 128,
    ) -> None:
        self.flight_recorder = flight_recorder or get_flight_recorder()
        self.silence_threshold_fs = silence_threshold_fs
        self.clipping_threshold_fs = clipping_threshold_fs
        self.clipping_fraction_limit = clipping_fraction_limit
        self.dc_offset_limit_fs = dc_offset_limit_fs
        self.min_evaluation_samples = min_evaluation_samples

    def analyze_window(
        self,
        samples: np.ndarray,
        sample_rate_hz: int,
        source_type: str = "device",
        session_id: Optional[str] = None,
    ) -> SignalQualitySnapshot:
        """Analyze a finite buffer of normalized float32 samples [-1.0, 1.0]."""
        evidence_origin = (
            EvidenceOrigin.INJECTED_SIMULATION
            if source_type in ("synthetic", "virtual_bench")
            else EvidenceOrigin.DERIVED_FROM_SAMPLES
        )

        n_samples = len(samples)
        if n_samples < self.min_evaluation_samples or sample_rate_hz <= 0:
            return SignalQualitySnapshot(
                sample_count=n_samples,
                duration_s=round(n_samples / max(1, sample_rate_hz), 4),
                sample_rate_hz=sample_rate_hz,
                source_type=source_type,
                rms_fs=0.0,
                peak_fs=0.0,
                crest_factor=0.0,
                clipping_hits=0,
                clipping_fraction=0.0,
                dc_offset_fs=0.0,
                zero_crossing_rate=0.0,
                is_evaluated=False,
                scientific_provenance={
                    "status": "NOT_EVALUATED",
                    "reason": f"Insufficient samples ({n_samples} < {self.min_evaluation_samples})",
                    "spl_calibrated": "false",
                    "medical_diagnosis": "forbidden",
                },
            )

        duration_s = float(n_samples / sample_rate_hz)
        arr = np.asarray(samples, dtype=np.float32)

        # 1. Digital dynamic range metrics
        peak = float(np.max(np.abs(arr)))
        rms = float(np.sqrt(np.mean(arr**2)))
        crest_factor = float(peak / rms) if rms > 1e-12 else 0.0
        dc_offset = float(np.mean(arr))

        # 2. Digital saturation (clipping) hits
        clip_hits = int(np.sum(np.abs(arr) >= self.clipping_threshold_fs))
        clip_fraction = float(clip_hits / n_samples)
        is_clipping = clip_fraction > self.clipping_fraction_limit

        # 3. Near silence check
        is_near_silence = rms < self.silence_threshold_fs

        # 4. Excessive DC offset check
        is_excessive_dc = abs(dc_offset) > self.dc_offset_limit_fs

        # 5. Zero-crossing rate on AC-coupled signal
        ac_arr = arr - dc_offset
        signs = np.sign(ac_arr)
        # Replace 0 signs with 1 to prevent false crossings
        signs[signs == 0] = 1
        zcr = float(np.sum(signs[:-1] != signs[1:]) / (n_samples - 1))

        # 6. Periodic alternating signs check (PCM container bit-shift symptom)
        is_suspicious_alignment = False
        if zcr > 0.85 and peak > 0.5:
            # Alternating high-frequency pattern characteristic of container MSB/LSB misalignment
            is_suspicious_alignment = True

        # 7. 50 Hz power-mains tonal hypothesis
        mains_ratio: Optional[float] = None
        if n_samples >= 512 and sample_rate_hz >= 200:
            mains_ratio = self._estimate_mains_ratio(arr, sample_rate_hz)

        # 8. Record fault events into Flight Recorder
        active_codes: list[str] = []

        if is_clipping:
            active_codes.append("AF-SIG-002")
            self.flight_recorder.record(
                fault_code="AF-SIG-002",
                message=f"Digital rail saturation detected: {clip_hits} samples ({clip_fraction*100:.2f}%) at +/- 1.0 FS.",
                subsystem=Subsystem.SIGNAL,
                severity=Severity.WARNING,
                source_type=source_type,
                evidence_origin=evidence_origin,
                session_id=session_id,
                observed_value=clip_fraction,
                expected_value=0.0,
                counter_snapshot={"clipping_hits": clip_hits, "total_samples": n_samples},
            )

        if is_near_silence and duration_s >= 1.0:
            active_codes.append("AF-SIG-001")
            self.flight_recorder.record(
                fault_code="AF-SIG-001",
                message=f"Near-silence detected: RMS {rms:.6f} FS (< -60 dBFS) across {duration_s:.1f} s.",
                subsystem=Subsystem.SIGNAL,
                severity=Severity.WARNING,
                source_type=source_type,
                evidence_origin=evidence_origin,
                session_id=session_id,
                observed_value=rms,
                expected_value=self.silence_threshold_fs,
            )

        if is_excessive_dc:
            active_codes.append("AF-SIG-003")
            self.flight_recorder.record(
                fault_code="AF-SIG-003",
                message=f"Excessive DC component detected: mean offset {dc_offset:.4f} FS (> 10% FS).",
                subsystem=Subsystem.SIGNAL,
                severity=Severity.WARNING,
                source_type=source_type,
                evidence_origin=evidence_origin,
                session_id=session_id,
                observed_value=dc_offset,
                expected_value=0.0,
            )

        if is_suspicious_alignment:
            active_codes.append("AF-SIG-007")
            self.flight_recorder.record(
                fault_code="AF-SIG-007",
                message="Possible I2S PCM container bit-alignment mismatch (alternating extreme sign transitions).",
                subsystem=Subsystem.SIGNAL,
                severity=Severity.WARNING,
                source_type=source_type,
                evidence_origin=evidence_origin,
                session_id=session_id,
                observed_value=zcr,
            )

        if mains_ratio is not None and mains_ratio > 8.0:
            # > 18 dB power above local background
            active_codes.append("AF-SIG-004")
            self.flight_recorder.record(
                fault_code="AF-SIG-004",
                message=f"Prominent 50 Hz tonal component detected (power ratio {mains_ratio:.1f}x above background).",
                subsystem=Subsystem.SIGNAL,
                severity=Severity.INFO,
                source_type=source_type,
                evidence_origin=evidence_origin,
                session_id=session_id,
                observed_value=mains_ratio,
            )

        return SignalQualitySnapshot(
            sample_count=n_samples,
            duration_s=round(duration_s, 4),
            sample_rate_hz=sample_rate_hz,
            source_type=source_type,
            rms_fs=round(rms, 6),
            peak_fs=round(peak, 6),
            crest_factor=round(crest_factor, 3),
            clipping_hits=clip_hits,
            clipping_fraction=round(clip_fraction, 6),
            dc_offset_fs=round(dc_offset, 6),
            zero_crossing_rate=round(zcr, 4),
            mains_50hz_ratio=round(mains_ratio, 2) if mains_ratio is not None else None,
            is_near_silence=is_near_silence,
            is_clipping=is_clipping,
            is_excessive_dc=is_excessive_dc,
            is_suspicious_alignment=is_suspicious_alignment,
            is_evaluated=True,
            active_fault_codes=active_codes,
            scientific_provenance={
                "status": "EVALUATED_MATHEMATICAL",
                "spl_calibrated": "false (Requires laboratory acoustic coupler & certified sound level meter)",
                "microphone_self_noise": "not_measured (Cannot be inferred from arbitrary recording)",
                "medical_diagnosis": "forbidden (Engineering quality assessment only)",
            },
        )

    def _estimate_mains_ratio(self, arr: np.ndarray, fs: int) -> float:
        """Estimate 50 Hz power peak ratio compared to adjacent background noise."""
        nfft = min(len(arr), 1024)
        if nfft < 128:
            return 1.0

        # Hann window FFT
        win = np.hanning(nfft)
        fft_mag = np.abs(np.fft.rfft(arr[:nfft] * win))
        freqs = np.fft.rfftfreq(nfft, d=1.0 / fs)

        mains_mask = (freqs >= 48.0) & (freqs <= 52.0)
        bg_mask = (freqs >= 30.0) & (freqs <= 80.0) & ~mains_mask

        if not np.any(mains_mask) or not np.any(bg_mask):
            return 1.0

        mains_power = float(np.max(fft_mag[mains_mask]))
        bg_median = float(np.median(fft_mag[bg_mask]))

        if bg_median < 1e-12:
            return 1.0
        return float(mains_power / bg_median)
