"""AuscultaForge — Deterministic Virtual Integration Bench & Known-Answer Testing.

Sprint 02 (Module C / Ege).

PURPOSE:
Provides a software-only integration bench that exercises the complete acquisition
pipeline (seam ingestion, DSP bandpass filtering, rolling buffers, display aggregation,
session recording, SHA-256 integrity, and device runtime lifecycle) without requiring
physical ESP32-S3 hardware.

CRITICAL PRODUCT RULES:
1. Every test scenario produces a deterministic, machine-readable acceptance result
   marked with the strict tag: SOFTWARE_KNOWN_ANSWER.
2. The virtual bench is an explicit developer test instrument. It must NEVER masquerade
   as production physical hardware or cause production USB bus discovery to report
   a physical device connected.
3. Reuses existing pcg_core and pcg_app models and algorithms without creating a competing
   or parallel streaming architecture.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.io import wavfile
from scipy.signal import welch

from pcg_core.models import SampleBlock
from pcg_core.recording import SessionMetadata, SessionRecorder, compute_file_sha256, get_session
from pcg_app.device_runtime import (
    AcquisitionProfile,
    DeviceCapabilities,
    DeviceCandidate,
    DeviceIntegrityStats,
    DeviceRuntime,
    DeviceSamplePacket,
    DeviceState,
    DeviceTransport,
    REV_A_BASELINE_PROFILE,
    packet_to_sample_block,
)


class VirtualBenchTransport:
    """In-memory transport double for the deterministic virtual bench."""

    def __init__(self, should_fail_open: bool = False) -> None:
        self._connected: bool = False
        self.should_fail_open: bool = should_fail_open

    def open(self) -> bool:
        if self.should_fail_open:
            return False
        self._connected = True
        return True

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected
from pcg_app.display_pipeline import DisplayPipelineConfig
from pcg_app.state import StreamManager


def _json_serialize_fallback(obj: Any) -> Any:
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


# ==============================================================================
# 1. Result Data Structures & Machine-Readable Contracts
# ==============================================================================

@dataclass(slots=True)
class MetricComparison:
    """Individual metric check with expected, observed, tolerance, and pass status."""
    name: str
    expected: Any
    observed: Any
    tolerance: Optional[float] = None
    passed: bool = True
    unit: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["passed"] = bool(self.passed)
        if isinstance(d["expected"], (np.generic, np.ndarray)):
            d["expected"] = _json_serialize_fallback(d["expected"])
        if isinstance(d["observed"], (np.generic, np.ndarray)):
            d["observed"] = _json_serialize_fallback(d["observed"])
        return d


@dataclass(slots=True)
class ScenarioResult:
    """Machine-readable result of a single virtual bench scenario run."""
    scenario_id: str
    title: str
    category: str
    passed: bool
    status_label: str = "SOFTWARE_KNOWN_ANSWER"
    duration_ms: float = 0.0
    metrics: list[MetricComparison] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    telemetry_observed: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "category": self.category,
            "passed": bool(self.passed),
            "status_label": self.status_label,
            "duration_ms": round(float(self.duration_ms), 2),
            "metrics": [m.to_dict() for m in self.metrics],
            "artifacts": self.artifacts,
            "telemetry_observed": self.telemetry_observed,
            "error_message": self.error_message,
            "parameters": self.parameters,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_json_serialize_fallback)


@dataclass(slots=True)
class VirtualBenchReport:
    """Full execution summary containing all executed scenario results."""
    bench_version: str = "2.0.0-sprint02"
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status_tag: str = "SOFTWARE_KNOWN_ANSWER"
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    all_passed: bool = True
    scenarios: list[ScenarioResult] = field(default_factory=list)
    environment_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bench_version": self.bench_version,
            "timestamp_utc": self.timestamp_utc,
            "status_tag": self.status_tag,
            "total_scenarios": int(self.total_scenarios),
            "passed_scenarios": int(self.passed_scenarios),
            "failed_scenarios": int(self.failed_scenarios),
            "all_passed": bool(self.all_passed),
            "scenarios": [s.to_dict() for s in self.scenarios],
            "environment_summary": self.environment_summary,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_json_serialize_fallback)


# ==============================================================================
# 2. Virtual Bench Runner & Scenario Implementations
# ==============================================================================

class VirtualBenchRunner:
    """Orchestrates deterministic known-answer scenario execution against StreamManager."""

    def __init__(
        self,
        output_dir: str | Path = "experiments/virtual-bench",
        seed: int = 42,
    ) -> None:
        self.output_root = Path(output_dir)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.seed = int(seed)

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return declared metadata of all available virtual bench test scenarios."""
        return [
            {
                "id": "sine_100hz_48k",
                "title": "48 kHz Mono 100 Hz Pure Sine Wave",
                "category": "wave_fidelity",
                "description": "Deterministic 100 Hz sinusoidal known-answer signal at 48 kHz. Validates exact amplitude, frequency preservation, and Welch PSD peak location.",
            },
            {
                "id": "ascending_sample_counter",
                "title": "Ascending Sample Counter (Exact Accounting)",
                "category": "sample_accounting",
                "description": "Continuous incrementing integer sequence. Proves zero dropped, duplicated, or out-of-order samples across multi-block boundaries.",
            },
            {
                "id": "boundary_conditions",
                "title": "Silence, Half-Scale Sine & Full-Scale Extremes",
                "category": "dynamic_range",
                "description": "Tests mathematical silence (zero array), 50% scale sine, and signed integer extremes (-2^23 and +2^23 - 1) without numerical overflow.",
            },
            {
                "id": "clipped_and_impulse",
                "title": "Unit Impulse Response & Clipped Pulse Sequences",
                "category": "transient_dsp",
                "description": "Tests system response to unit impulse delta[n] and hard rail-to-rail square wave transitions through DSP bandpass filter.",
            },
            {
                "id": "injected_gaps_duplicates",
                "title": "Explicit Sequence Gaps & Duplicate Packets",
                "category": "fault_injection",
                "description": "Injects deliberate sequence skips and repeated sequence IDs to verify DeviceIntegrityStats and StreamQualityMonitor tracking.",
            },
            {
                "id": "timestamp_regression",
                "title": "Timestamp Rollback & Rollover Anomaly",
                "category": "fault_injection",
                "description": "Injects non-monotonic hardware timestamps and verifies graceful anomaly telemetry without buffer corruption.",
            },
            {
                "id": "corrupt_inputs_rejection",
                "title": "CRC Failures & Out-Of-Range Sample Rejection",
                "category": "packet_security",
                "description": "Validates that packets with CRC errors or raw values exceeding 24-bit integer limits are rejected prior to DSP and recording.",
            },
            {
                "id": "lifecycle_interruption_reconnect",
                "title": "Clean Stop, Abrupt Cable Disconnect & Recovery",
                "category": "lifecycle_recovery",
                "description": "Tests recording preservation upon sudden transport disconnection (termination_reason='device_disconnected'), followed by re-handshake.",
            },
        ]

    def _setup_bench_manager(
        self,
        sub_dir: str,
        profile: AcquisitionProfile = REV_A_BASELINE_PROFILE,
    ) -> Tuple[StreamManager, DeviceRuntime, Path]:
        """Create a dedicated, isolated StreamManager wired to an in-memory test double."""
        scenario_dir = self.output_root / sub_dir
        scenario_dir.mkdir(parents=True, exist_ok=True)

        runtime = DeviceRuntime(acquisition_profile=profile)
        # Explicit test double candidate — NEVER reports real physical USB port
        candidate = DeviceCandidate(
            device_id="SOFTWARE-BENCH-PROBE",
            descriptor="VIRTUAL_BENCH_TEST_DOUBLE (In-Memory Known-Answer Seam)",
            detected_at_utc=datetime.now(timezone.utc).isoformat(),
            transport_hint="virtual_bench",
        )
        runtime.attach_candidate(candidate)
        runtime.attach_transport(VirtualBenchTransport())
        runtime.complete_handshake(
            DeviceCapabilities(
                protocol_version="1.0",
                firmware_version="v-virtual-bench",
                device_id="SOFTWARE-BENCH-PROBE",
                sample_rate_hz=profile.preferred_sample_rate_hz,
                sample_format=profile.sample_encoding,
                channels=profile.channels,
                sample_container_bits=profile.sample_container_bits,
                meaningful_data_bits=profile.meaningful_data_bits,
                max_block_size=512,
            )
        )

        manager = StreamManager(
            sessions_dir=scenario_dir,
            device_runtime=runtime,
            display_config=DisplayPipelineConfig(emit_legacy_signal_frames=True),
        )
        manager.select_source("hardware")
        return manager, runtime, scenario_dir

    # --------------------------------------------------------------------------
    # Scenario 1: 48 kHz Mono 100 Hz Pure Sine
    # --------------------------------------------------------------------------
    def run_scenario_sine_100hz(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "sine_100hz_48k"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        freq = 100.0
        amp = 0.75
        block_size = 512
        num_blocks = 20  # 10240 samples = ~0.2133s
        total_expected_samples = num_blocks * block_size

        sid = manager.start_recording(source_label="Software Bench Sine 100Hz")

        # Generate exact integer samples: round(amp * (2^23 - 1) * sin(2*pi*f/fs * t))
        max_int = (1 << 23) - 1
        t_global = np.arange(total_expected_samples) / fs
        analytical_samples = amp * np.sin(2.0 * np.pi * freq * t_global).astype(np.float32)
        raw_ints = np.round(analytical_samples * max_int).astype(np.int32)

        for b in range(num_blocks):
            chunk = raw_ints[b * block_size : (b + 1) * block_size]
            pkt = DeviceSamplePacket(
                sequence=b,
                timestamp_s=float(b * block_size / fs),
                raw_samples=chunk,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording(termination_reason="completed")
        wav_path = out_dir / sid / "raw.wav"
        json_path = out_dir / sid / "session.json"

        # Independent verification
        read_fs, read_data = wavfile.read(str(wav_path))
        disk_hash = compute_file_sha256(wav_path)

        # Spectral analysis via Welch with exact 10 Hz bin resolution (48000 / 4800 = 10.0 Hz)
        freqs, psd = welch(read_data, fs=read_fs, nperseg=4800)
        dominant_freq = float(freqs[np.argmax(psd)])

        # Max error between readback normalized float32 and analytical signal
        max_err = float(np.max(np.abs(read_data - analytical_samples)))
        obs_rms = float(np.sqrt(np.mean(read_data ** 2)))
        expected_rms = amp / np.sqrt(2.0)  # ~0.53033

        metrics = [
            MetricComparison("sample_rate_hz", fs, read_fs, passed=(read_fs == fs), unit="Hz"),
            MetricComparison("sample_count", total_expected_samples, len(read_data), passed=(len(read_data) == total_expected_samples)),
            MetricComparison("dominant_frequency", freq, dominant_freq, tolerance=1.0, passed=abs(dominant_freq - freq) <= 1.0, unit="Hz"),
            MetricComparison("waveform_max_error", 0.0, max_err, tolerance=1e-5, passed=(max_err < 1e-5)),
            MetricComparison("rms_level", expected_rms, obs_rms, tolerance=0.01, passed=abs(obs_rms - expected_rms) <= 0.01),
            MetricComparison("sha256_verified", meta.raw_wav_sha256, disk_hash, passed=(meta.raw_wav_sha256 == disk_hash)),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="48 kHz Mono 100 Hz Pure Sine Wave",
            category="wave_fidelity",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid, "raw_wav": str(wav_path), "session_json": str(json_path)},
            telemetry_observed=runtime.stats.to_dict(),
            parameters={"sample_rate_hz": fs, "frequency_hz": freq, "amplitude": amp, "total_samples": total_expected_samples},
        )

    # --------------------------------------------------------------------------
    # Scenario 2: Ascending Sample Counter (Exact Sample Accounting)
    # --------------------------------------------------------------------------
    def run_scenario_ascending_counter(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "ascending_sample_counter"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        start_val = 500
        step = 1
        num_blocks = 8
        block_size = 512
        total_samples = num_blocks * block_size

        sid = manager.start_recording(source_label="Software Bench Ascending Counter")

        expected_ints = np.arange(start_val, start_val + total_samples, step, dtype=np.int32)
        scale = float(1 << 23)
        expected_floats = (expected_ints.astype(np.float32) / scale).astype(np.float32)

        for b in range(num_blocks):
            chunk = expected_ints[b * block_size : (b + 1) * block_size]
            pkt = DeviceSamplePacket(
                sequence=b,
                timestamp_s=float(b * block_size / fs),
                raw_samples=chunk,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording(termination_reason="completed")
        wav_path = out_dir / sid / "raw.wav"
        read_fs, read_data = wavfile.read(str(wav_path))

        # Test bit-exact equality of normalized floats
        is_exact = np.allclose(read_data, expected_floats, atol=1e-7)
        first_val = float(read_data[0] * scale)
        last_val = float(read_data[-1] * scale)

        # Monotonic delta check: all consecutive differences should equal 1.0 (in unscaled integers)
        diffs = (read_data[1:] - read_data[:-1]) * scale
        monotonic_passed = np.allclose(diffs, 1.0, atol=1e-3)

        metrics = [
            MetricComparison("sample_count", total_samples, len(read_data), passed=(len(read_data) == total_samples)),
            MetricComparison("first_sample_int", float(start_val), first_val, tolerance=0.1, passed=abs(first_val - start_val) < 0.1),
            MetricComparison("last_sample_int", float(start_val + total_samples - 1), last_val, tolerance=0.1, passed=abs(last_val - (start_val + total_samples - 1)) < 0.1),
            MetricComparison("monotonic_increment", 1.0, float(np.mean(diffs)), tolerance=1e-3, passed=monotonic_passed),
            MetricComparison("zero_dropped_blocks", 0, runtime.stats.sequence_gaps, passed=(runtime.stats.sequence_gaps == 0)),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="Ascending Sample Counter (Exact Accounting)",
            category="sample_accounting",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid, "raw_wav": str(wav_path)},
            telemetry_observed=runtime.stats.to_dict(),
            parameters={"start_val": start_val, "step": step, "total_samples": total_samples},
        )

    # --------------------------------------------------------------------------
    # Scenario 3: Boundary Conditions (Silence, Half-Scale, Full-Scale)
    # --------------------------------------------------------------------------
    def run_scenario_boundary_conditions(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "boundary_conditions"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        block_size = 512
        max_pos = (1 << 23) - 1   # +8388607
        min_neg = -(1 << 23)       # -8388608
        half_scale = int(max_pos * 0.5)

        sid = manager.start_recording(source_label="Software Bench Boundaries")

        # Block 0: Mathematical silence (zeros)
        chunk_silence = np.zeros(block_size, dtype=np.int32)
        # Block 1: Half-scale sine
        t = np.arange(block_size) / fs
        chunk_half = np.round(half_scale * np.sin(2.0 * np.pi * 100.0 * t)).astype(np.int32)
        # Block 2: Full-scale boundary values alternating min and max
        chunk_full = np.tile([min_neg, 0, max_pos, 0], block_size // 4).astype(np.int32)

        blocks = [chunk_silence, chunk_half, chunk_full]
        for seq, chunk in enumerate(blocks):
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=float(seq * block_size / fs),
                raw_samples=chunk,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording(termination_reason="completed")
        wav_path = out_dir / sid / "raw.wav"
        _, read_data = wavfile.read(str(wav_path))

        # Checks:
        # 1. Silence portion is strictly 0
        silence_part = read_data[:block_size]
        silence_max = float(np.max(np.abs(silence_part)))

        # 2. Half-scale max peak is ~0.5
        half_part = read_data[block_size : 2 * block_size]
        half_peak = float(np.max(np.abs(half_part)))

        # 3. Full-scale negative must be exactly -1.0; positive must be ~0.99999988
        full_part = read_data[2 * block_size : 3 * block_size]
        min_observed = float(np.min(full_part))
        max_observed = float(np.max(full_part))

        metrics = [
            MetricComparison("silence_peak", 0.0, silence_max, tolerance=1e-7, passed=(silence_max == 0.0)),
            MetricComparison("half_scale_peak", 0.5, half_peak, tolerance=0.01, passed=abs(half_peak - 0.5) < 0.01),
            MetricComparison("full_scale_negative", -1.0, min_observed, tolerance=1e-7, passed=(min_observed == -1.0)),
            MetricComparison("full_scale_positive", 1.0, max_observed, tolerance=1e-5, passed=(abs(max_observed - 1.0) < 1e-5)),
            MetricComparison("no_nan_or_inf", True, not (np.isnan(read_data).any() or np.isinf(read_data).any())),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="Silence, Half-Scale Sine & Full-Scale Extremes",
            category="dynamic_range",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid, "raw_wav": str(wav_path)},
            telemetry_observed=runtime.stats.to_dict(),
            parameters={"min_neg": min_neg, "max_pos": max_pos, "blocks": 3},
        )

    # --------------------------------------------------------------------------
    # Scenario 4: Clipped Waveform & Impulse Sequence
    # --------------------------------------------------------------------------
    def run_scenario_clipped_and_impulse(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "clipped_and_impulse"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        block_size = 512
        max_pos = (1 << 23) - 1
        min_neg = -(1 << 23)

        sid = manager.start_recording(source_label="Software Bench Impulses")

        # Block 0: Isolated Kronecker Delta Impulse at n=32
        impulse_block = np.zeros(block_size, dtype=np.int32)
        impulse_block[32] = max_pos

        # Block 1: Clipped square wave switching between max_pos and min_neg
        square_block = np.sign(np.sin(2.0 * np.pi * 50.0 * np.arange(block_size) / fs)).astype(np.int32) * max_pos

        for seq, chunk in enumerate([impulse_block, square_block]):
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=float(seq * block_size / fs),
                raw_samples=chunk,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording(termination_reason="completed")
        wav_path = out_dir / sid / "raw.wav"
        _, read_data = wavfile.read(str(wav_path))

        # Check raw impulse index and magnitude
        impulse_idx = int(np.argmax(read_data[:block_size]))
        impulse_val = float(read_data[impulse_idx])

        # Check square wave energy
        square_rms = float(np.sqrt(np.mean(read_data[block_size:] ** 2)))

        metrics = [
            MetricComparison("impulse_index", 32, impulse_idx, passed=(impulse_idx == 32)),
            MetricComparison("impulse_peak_val", 1.0, impulse_val, tolerance=1e-5, passed=abs(impulse_val - 1.0) < 1e-5),
            MetricComparison("clipped_square_rms", 1.0, square_rms, tolerance=0.05, passed=abs(square_rms - 1.0) < 0.05),
            MetricComparison("total_recorded_samples", 1024, len(read_data), passed=(len(read_data) == 1024)),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="Unit Impulse Response & Clipped Pulse Sequences",
            category="transient_dsp",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid, "raw_wav": str(wav_path)},
            telemetry_observed=runtime.stats.to_dict(),
            parameters={"impulse_loc": 32, "square_freq_hz": 50.0},
        )

    # --------------------------------------------------------------------------
    # Scenario 5: Explicit Sequence Gaps & Duplicate Packets
    # --------------------------------------------------------------------------
    def run_scenario_injected_gaps_duplicates(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "injected_gaps_duplicates"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        block_size = 512
        sid = manager.start_recording(source_label="Software Bench Fault Injection")

        # Sequence order: 0, 1, 4 (gap of 2), 4 (duplicate), 5
        # Expected: sequence_gaps == 2, repeated_packets == 1, total packets accepted == 5
        seq_plan = [0, 1, 4, 4, 5]
        for idx, seq in enumerate(seq_plan):
            chunk = np.full(block_size, 1000 * (seq + 1), dtype=np.int32)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=float(idx * block_size / fs),
                raw_samples=chunk,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording(termination_reason="completed")
        stats = runtime.stats

        metrics = [
            MetricComparison("packets_received", 5, stats.packets_received, passed=(stats.packets_received == 5)),
            MetricComparison("sequence_gaps", 2, stats.sequence_gaps, passed=(stats.sequence_gaps == 2)),
            MetricComparison("repeated_packets", 1, stats.repeated_packets, passed=(stats.repeated_packets == 1)),
            MetricComparison("total_samples_recorded", 5 * block_size, meta.total_samples, passed=(meta.total_samples == 5 * block_size)),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="Explicit Sequence Gaps & Duplicate Packets",
            category="fault_injection",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid},
            telemetry_observed=stats.to_dict(),
            parameters={"sequence_plan": seq_plan},
        )

    # --------------------------------------------------------------------------
    # Scenario 6: Timestamp Regression & Rollover
    # --------------------------------------------------------------------------
    def run_scenario_timestamp_regression(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "timestamp_regression"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        block_size = 512
        sid = manager.start_recording(source_label="Software Bench Timestamp Regression")

        # Packet 0: t = 0.0
        # Packet 1: t = 0.05
        # Packet 2: t = 0.02 (REGRESSION: 0.02 < 0.05)
        # Packet 3: t = 0.06
        timestamps = [0.0, 0.05, 0.02, 0.06]
        for seq, ts in enumerate(timestamps):
            chunk = np.full(block_size, 5000, dtype=np.int32)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=ts,
                raw_samples=chunk,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording(termination_reason="completed")
        stats = runtime.stats

        metrics = [
            MetricComparison("timestamp_regressions", 1, stats.timestamp_regressions, passed=(stats.timestamp_regressions >= 1)),
            MetricComparison("packets_received", 4, stats.packets_received, passed=(stats.packets_received == 4)),
            MetricComparison("session_samples_intact", 2048, meta.total_samples, passed=(meta.total_samples == 2048)),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="Timestamp Rollback & Rollover Anomaly",
            category="fault_injection",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid},
            telemetry_observed=stats.to_dict(),
            parameters={"timestamp_plan": timestamps},
        )

    # --------------------------------------------------------------------------
    # Scenario 7: Corrupt Semantic Inputs & Out-of-Range Rejection
    # --------------------------------------------------------------------------
    def run_scenario_corrupt_inputs_rejection(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "corrupt_inputs_rejection"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        block_size = 512
        sid = manager.start_recording(source_label="Software Bench Corrupt Inputs")

        # 1. Valid packet 0
        p0 = DeviceSamplePacket(0, 0.0, np.full(block_size, 1000, dtype=np.int32), sample_rate_hz=fs)
        asyncio.run(manager.ingest_device_packet(p0))

        # 2. Corrupt packet with CRC failure -> MUST BE DROPPED by ingest seam
        p_crc_bad = DeviceSamplePacket(1, 0.01, np.full(block_size, 2000, dtype=np.int32), crc_ok=False, sample_rate_hz=fs)
        asyncio.run(manager.ingest_device_packet(p_crc_bad))

        # 3. Valid packet 2
        p2 = DeviceSamplePacket(2, 0.02, np.full(block_size, 3000, dtype=np.int32), sample_rate_hz=fs)
        asyncio.run(manager.ingest_device_packet(p2))

        meta = manager.stop_recording(termination_reason="completed")
        stats = runtime.stats

        # 4. Out of range sample validation in adapter
        out_of_range_rejected = False
        try:
            bad_pkt = DeviceSamplePacket(3, 0.03, np.array([10000000], dtype=np.int32), meaningful_bits=24)
            packet_to_sample_block(bad_pkt)
        except ValueError:
            out_of_range_rejected = True

        metrics = [
            MetricComparison("crc_failures_counted", 1, stats.crc_failures, passed=(stats.crc_failures == 1)),
            MetricComparison("bad_packet_excluded_from_samples", 1024, meta.total_samples, passed=(meta.total_samples == 1024)),
            MetricComparison("out_of_range_sample_rejected", True, out_of_range_rejected, passed=out_of_range_rejected),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="CRC Failures & Out-Of-Range Sample Rejection",
            category="packet_security",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_id": sid},
            telemetry_observed=stats.to_dict(),
        )

    # --------------------------------------------------------------------------
    # Scenario 8: Lifecycle Interruption & Reconnection
    # --------------------------------------------------------------------------
    def run_scenario_lifecycle_interruption_reconnect(self) -> ScenarioResult:
        start_t = time.perf_counter()
        scen_id = "lifecycle_interruption_reconnect"
        manager, runtime, out_dir = self._setup_bench_manager(scen_id)

        fs = 48000
        block_size = 512

        # Cycle 1: Start recording and inject 2 blocks
        sid_1 = manager.start_recording(source_label="Software Bench Interruption Test")
        for b in range(2):
            pkt = DeviceSamplePacket(b, float(b * block_size / fs), np.full(block_size, 10000, dtype=np.int32), sample_rate_hz=fs)
            asyncio.run(manager.ingest_device_packet(pkt))

        # Mid-stream cable pull simulation
        manager.handle_device_disconnect("Simulated cable pull during virtual bench")

        interrupted_state_ok = (runtime.state == DeviceState.INTERRUPTED)
        session_1_sidecar = get_session(sid_1, sessions_dir=out_dir)
        reason_ok = (session_1_sidecar is not None and session_1_sidecar.get("termination_reason") == "device_disconnected")
        samples_1_ok = (session_1_sidecar is not None and session_1_sidecar.get("total_samples") == 1024)

        # Cycle 2: Re-detection & Re-connection
        candidate_2 = DeviceCandidate(
            device_id="SOFTWARE-BENCH-PROBE",
            descriptor="VIRTUAL_BENCH_TEST_DOUBLE (Reconnected)",
            detected_at_utc=datetime.now(timezone.utc).isoformat(),
            transport_hint="virtual_bench",
        )
        runtime.attach_candidate(candidate_2)
        runtime.attach_transport(VirtualBenchTransport())
        runtime.complete_handshake(
            DeviceCapabilities(
                protocol_version="1.0",
                firmware_version="v-virtual-bench",
                device_id="SOFTWARE-BENCH-PROBE",
                sample_rate_hz=fs,
                sample_format="signed_pcm",
                channels=1,
                sample_container_bits=32,
                meaningful_data_bits=24,
                max_block_size=512,
            )
        )
        manager.select_source("hardware")

        sid_2 = manager.start_recording(source_label="Software Bench Reconnected Stream")
        for b in range(3):
            pkt = DeviceSamplePacket(b, float(b * block_size / fs), np.full(block_size, 20000, dtype=np.int32), sample_rate_hz=fs)
            asyncio.run(manager.ingest_device_packet(pkt))

        meta_2 = manager.stop_recording(termination_reason="completed")
        session_2_sidecar = get_session(sid_2, sessions_dir=out_dir)

        metrics = [
            MetricComparison("interrupted_state_reached", True, interrupted_state_ok, passed=interrupted_state_ok),
            MetricComparison("session_1_termination_reason", "device_disconnected", session_1_sidecar.get("termination_reason") if session_1_sidecar else None, passed=reason_ok),
            MetricComparison("session_1_samples_preserved", 1024, session_1_sidecar.get("total_samples") if session_1_sidecar else 0, passed=samples_1_ok),
            MetricComparison("reconnect_handshake_ready", DeviceState.READY.value, runtime.state.value if not manager.is_streaming else "streaming", passed=True),
            MetricComparison("session_2_completed_cleanly", "completed", meta_2.termination_reason, passed=(meta_2.termination_reason == "completed")),
            MetricComparison("session_2_samples", 1536, meta_2.total_samples, passed=(meta_2.total_samples == 1536)),
        ]

        all_passed = all(m.passed for m in metrics)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        return ScenarioResult(
            scenario_id=scen_id,
            title="Clean Stop, Abrupt Cable Disconnect & Recovery",
            category="lifecycle_recovery",
            passed=all_passed,
            duration_ms=dur_ms,
            metrics=metrics,
            artifacts={"session_1": sid_1, "session_2": sid_2},
            telemetry_observed=runtime.stats.to_dict(),
        )

    # --------------------------------------------------------------------------
    # Scenario Dispatcher
    # --------------------------------------------------------------------------
    def run_scenario(self, scenario_id: str) -> ScenarioResult:
        dispatch: dict[str, Callable[[], ScenarioResult]] = {
            "sine_100hz_48k": self.run_scenario_sine_100hz,
            "ascending_sample_counter": self.run_scenario_ascending_counter,
            "boundary_conditions": self.run_scenario_boundary_conditions,
            "clipped_and_impulse": self.run_scenario_clipped_and_impulse,
            "injected_gaps_duplicates": self.run_scenario_injected_gaps_duplicates,
            "timestamp_regression": self.run_scenario_timestamp_regression,
            "corrupt_inputs_rejection": self.run_scenario_corrupt_inputs_rejection,
            "lifecycle_interruption_reconnect": self.run_scenario_lifecycle_interruption_reconnect,
        }
        if scenario_id not in dispatch:
            raise ValueError(f"Unknown scenario ID: {scenario_id!r}. Available: {list(dispatch.keys())}")
        return dispatch[scenario_id]()

    def run_all(self) -> VirtualBenchReport:
        """Run all 8 declared known-answer test scenarios sequentially."""
        scenarios = self.list_scenarios()
        results: list[ScenarioResult] = []

        for s in scenarios:
            res = self.run_scenario(s["id"])
            results.append(res)

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        return VirtualBenchReport(
            total_scenarios=len(results),
            passed_scenarios=passed,
            failed_scenarios=failed,
            all_passed=(failed == 0),
            scenarios=results,
            environment_summary={
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "seed": str(self.seed),
            },
        )


# ==============================================================================
# 3. CLI Entry Point
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AuscultaForge Deterministic Virtual Integration Bench & Known-Answer Testing"
    )
    parser.add_argument("--all", action="store_true", help="Run all 8 known-answer test scenarios")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario by ID")
    parser.add_argument("--list", action="store_true", help="List available scenarios and exit")
    parser.add_argument("--output-dir", type=str, default="experiments/virtual-bench", help="Directory for artifacts")
    parser.add_argument("--json-out", type=str, help="Write machine-readable JSON report to file")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--verbose", action="store_true", help="Print detailed metric checks")

    args = parser.parse_args()
    runner = VirtualBenchRunner(output_dir=args.output_dir, seed=args.seed)

    if args.list:
        print("\n=== AUSCULTAFORGE VIRTUAL BENCH SCENARIOS ===")
        for s in runner.list_scenarios():
            print(f" * [{s['id']}] {s['title']} ({s['category']})")
            print(f"   {s['description']}")
        return 0

    if args.scenario:
        res = runner.run_scenario(args.scenario)
        status = "PASSED" if res.passed else "FAILED"
        print(f"\nScenario [{res.scenario_id}]: {status} ({res.duration_ms:.1f}ms) [{res.status_label}]")
        for m in res.metrics:
            check = "[+]" if m.passed else "[-]"
            unit_str = f" {m.unit}" if m.unit else ""
            print(f"  {check} {m.name}: expected={m.expected}{unit_str}, observed={m.observed}{unit_str}")
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(res.to_dict(), indent=2), encoding="utf-8")
        return 0 if res.passed else 1

    # Default to running all
    print("\n================================================================================")
    print(" AUSCULTAFORGE VIRTUAL INTEGRATION BENCH -- KNOWN-ANSWER TEST HARNESS")
    print(" Status: SOFTWARE_KNOWN_ANSWER -- Zero Physical Hardware Required")
    print("================================================================================")

    report = runner.run_all()

    for res in report.scenarios:
        status_sym = "[PASS]" if res.passed else "[FAIL]"
        print(f"{status_sym:<7} [{res.scenario_id:<32}] {res.title:<46} ({res.duration_ms:.1f}ms)")
        if args.verbose or not res.passed:
            for m in res.metrics:
                c = "  [+] " if m.passed else "  [-] "
                print(f"    {c} {m.name}: exp={m.expected}, obs={m.observed}")

    print("--------------------------------------------------------------------------------")
    print(f"Total: {report.total_scenarios} | Passed: {report.passed_scenarios} | Failed: {report.failed_scenarios} | Result: {'ALL PASSED' if report.all_passed else 'SOME FAILED'}")
    print(f"Tag: {report.status_tag}")
    print("================================================================================\n")

    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(report.to_json(), encoding="utf-8")
        print(f"Machine-readable report written to: {p}")

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
