"""AuscultaForge — Measurement Automation Runner & Experiment Pipeline.

Coordinates the end-to-end execution of all six mandatory advisor measurements:
1. 20–500 Hz Phantom Frequency Response (H1 & Coherence)
2. Active-to-Quiescent Level Ratio (SNR Convention)
3. Repeatability Study (>= 10 Independent Runs)
4. 50 Hz Mains Interference & Harmonics (Delta f <= 0.5 Hz)
5. End-to-End Latency & Synchronization Evidence Verification
6. Dropped-Sample Rate & Continuous Acquisition Continuity (30-Minute Gate)

Loads real physical captures or synthetic test doubles, executes mathematical workflows,
and produces multi-format deliverables: JSON, tabular CSV, and Markdown.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Optional, Sequence
import uuid

import numpy as np
import scipy.signal
import scipy.io.wavfile as wavfile

from .models import (
    MeasurementStatus,
    SensorConfiguration,
    PhantomFrequencyResponseResult,
    SnrLevelRatioResult,
    RepeatabilityStudyResult,
    MainsInterferenceResult,
    LatencyMeasurementResult,
    PacketDropContinuityResult,
    AdvisorMetrologyReport,
)
from .workflows import (
    compute_phantom_frf,
    compute_active_quiescent_snr,
    compute_repeatability_study,
    compute_mains_interference,
    compute_latency_measurement,
    compute_continuity_drop_rate,
)
from .reports import (
    export_report_to_json,
    export_summary_to_csv,
    format_human_readable_summary,
)


def load_audio_wav(wav_path: str | Path) -> tuple[np.ndarray, int]:
    """Read a WAV file as normalized float32 array and return (signal, sample_rate_hz)."""
    p = Path(wav_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"WAV file not found: {p}")

    sr, data = wavfile.read(p)
    if data.ndim > 1:
        # Multi-channel: return as float array (channels along axis 1)
        if data.dtype == np.int16:
            data_f = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data_f = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.float32:
            data_f = data
        else:
            data_f = data.astype(np.float32)
    else:
        # Mono
        if data.dtype == np.int16:
            data_f = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data_f = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.float32:
            data_f = data
        elif data.dtype == np.uint8:
            data_f = (data.astype(np.float32) - 128.0) / 128.0
        else:
            data_f = data.astype(np.float32)

    return data_f, sr


# =============================================================================
# Experiment Configuration Schemas
# =============================================================================

@dataclass
class Workflow1Config:
    stimulus_wav_path: Optional[str] = None
    response_wav_path: Optional[str] = None
    sample_rate_hz: Optional[float] = None
    target_band_hz: list[float] = field(default_factory=lambda: [20.0, 500.0])


@dataclass
class Workflow2Config:
    active_wav_path: Optional[str] = None
    quiescent_wav_path: Optional[str] = None
    sample_rate_hz: Optional[float] = None
    filter_band_hz: list[float] = field(default_factory=lambda: [20.0, 500.0])
    room_acoustic_condition: str = "Quiet laboratory room (< 40 dBA ambient)"
    exciter_drive_level: str = "0 dBFS DAC unity level into PAM8403"
    sensor_model: str = "INMP441"
    sensor_interface: str = "I2S_DIGITAL"
    nominal_sensitivity: str = "-26 dBFS @ 94 dB SPL nominal"


@dataclass
class Workflow3Config:
    run_wav_paths: list[str] = field(default_factory=list)
    quiescent_wav_path: Optional[str] = None
    precomputed_values: list[float] = field(default_factory=list)
    run_labels: list[str] = field(default_factory=list)
    metric_name: str = "active_to_quiescent_ratio_db"
    outliers_documented: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Workflow4Config:
    quiescent_wav_path: Optional[str] = None
    sample_rate_hz: Optional[float] = None
    harmonics_hz: list[float] = field(default_factory=lambda: [50.0, 100.0, 150.0, 200.0, 250.0])
    power_source_condition: str = "Laptop running on AC mains adapter"
    shielding_condition: str = "Shielded twisted-pair transducer cable"


@dataclass
class Workflow5Config:
    trigger_timestamps_path: Optional[str] = None
    loopback_wav_path: Optional[str] = None
    acoustic_cross_corr_lag_ms: float = 0.0
    playback_buffer_delay_ms: float = 30.0


@dataclass
class Workflow6Config:
    stream_log_path: Optional[str] = None
    session_id: Optional[str] = None
    samples_per_packet: int = 128
    sample_rate_hz: int = 48000
    total_elapsed_seconds: Optional[float] = None


@dataclass
class MetrologyExperimentConfig:
    """Master Experiment Configuration for all Six Metrological Characterization Workflows."""
    schema_version: str = "1.0.0"
    experiment_id: str = field(default_factory=lambda: f"exp_metrology_{uuid.uuid4().hex[:8]}")
    title: str = "AuscultaForge Advisor Metrology Evaluation"
    author: str = "Ege — Module C"
    apparatus_id: str = "AUSCULTAFORGE_BENCH_V1"
    environment_notes: str = (
        "Laboratory bench with PAM8403 amplifier, 12-ohm exciter, "
        "and silicone/mechanical acoustic phantom at 22 deg C."
    )
    limitations_and_uncertainties: list[str] = field(default_factory=lambda: [
        "Uncalibrated relative FS quantities only; sound pressure level (dB SPL) is strictly prohibited.",
        "Exciter and transducer transfer functions are coupled with the silicone medium.",
        "ECMs and INMP441 are not calibrated physical equivalents.",
    ])
    sensor_declarations: list[SensorConfiguration] = field(default_factory=lambda: [
        SensorConfiguration("INMP441", "I2S_DIGITAL", "-26 dBFS @ 94 dB SPL nominal", preamp_gain_db=0.0),
        SensorConfiguration("ECM_GENERIC", "ANALOG_PREAMP", "Uncalibrated relative analog sensitivity", preamp_gain_db=20.0),
    ])
    workflow_1: Workflow1Config = field(default_factory=Workflow1Config)
    workflow_2: Workflow2Config = field(default_factory=Workflow2Config)
    workflow_3: Workflow3Config = field(default_factory=Workflow3Config)
    workflow_4: Workflow4Config = field(default_factory=Workflow4Config)
    workflow_5: Workflow5Config = field(default_factory=Workflow5Config)
    workflow_6: Workflow6Config = field(default_factory=Workflow6Config)
    run_synthetic_verification: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetrologyExperimentConfig:
        sensor_decls = [
            SensorConfiguration(**s) if isinstance(s, dict) else s
            for s in data.get("sensor_declarations", [])
        ]
        w1 = Workflow1Config(**data.get("workflow_1", {}))
        w2 = Workflow2Config(**data.get("workflow_2", {}))
        w3 = Workflow3Config(**data.get("workflow_3", {}))
        w4 = Workflow4Config(**data.get("workflow_4", {}))
        w5 = Workflow5Config(**data.get("workflow_5", {}))
        w6 = Workflow6Config(**data.get("workflow_6", {}))

        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            experiment_id=data.get("experiment_id", f"exp_metrology_{uuid.uuid4().hex[:8]}"),
            title=data.get("title", "AuscultaForge Advisor Metrology Evaluation"),
            author=data.get("author", "Ege — Module C"),
            apparatus_id=data.get("apparatus_id", "AUSCULTAFORGE_BENCH_V1"),
            environment_notes=data.get("environment_notes", ""),
            limitations_and_uncertainties=list(data.get("limitations_and_uncertainties", [])),
            sensor_declarations=sensor_decls or [
                SensorConfiguration("INMP441", "I2S_DIGITAL", "-26 dBFS @ 94 dB SPL nominal")
            ],
            workflow_1=w1,
            workflow_2=w2,
            workflow_3=w3,
            workflow_4=w4,
            workflow_5=w5,
            workflow_6=w6,
            run_synthetic_verification=bool(data.get("run_synthetic_verification", False)),
        )


# =============================================================================
# Metrology Experiment Runner
# =============================================================================

class MetrologyRunner:
    """Automates validation, execution, and reporting for the six advisor measurements."""

    def __init__(self, config: Optional[MetrologyExperimentConfig] = None):
        self.config = config or MetrologyExperimentConfig()

    def run(self, output_dir: Optional[str | Path] = None) -> AdvisorMetrologyReport:
        """Execute all six workflows according to configuration and export outputs."""
        cfg = self.config
        limitations = list(cfg.limitations_and_uncertainties)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Execute 6 workflows
        w1_res = self._execute_workflow_1(limitations)
        w2_res = self._execute_workflow_2(limitations)
        w3_res = self._execute_workflow_3(limitations)
        w4_res = self._execute_workflow_4(limitations)
        w5_res = self._execute_workflow_5(limitations)
        w6_res = self._execute_workflow_6(limitations)

        statuses = [
            w1_res.status,
            w2_res.status,
            w3_res.status,
            w4_res.status,
            w5_res.status,
            w6_res.status,
        ]

        if any(s == MeasurementStatus.FAILED.value for s in statuses):
            overall_status = "CONTAINS_FAILURES"
        elif all(s == MeasurementStatus.BENCH_MEASURED.value for s in statuses):
            overall_status = "ALL_MEASURED"
        elif any(s == MeasurementStatus.BENCH_MEASURED.value for s in statuses):
            overall_status = "PARTIAL_MEASURED"
        elif all(s == MeasurementStatus.SYNTHETIC_VERIFIED.value for s in statuses):
            overall_status = "SYNTHETIC_VERIFIED"
        else:
            overall_status = "NOT_YET_MEASURED"

        report = AdvisorMetrologyReport(
            schema_version=cfg.schema_version,
            report_id=cfg.experiment_id,
            created_at_utc=now_iso,
            author=cfg.author,
            apparatus_id=cfg.apparatus_id,
            overall_hardware_status=overall_status,
            workflow_1_frequency_response=w1_res,
            workflow_2_snr_level_ratio=w2_res,
            workflow_3_repeatability=w3_res,
            workflow_4_mains_interference=w4_res,
            workflow_5_latency=w5_res,
            workflow_6_dropped_samples=w6_res,
            sensor_declarations=cfg.sensor_declarations,
            environment_notes=cfg.environment_notes,
            limitations_and_uncertainties=limitations,
            provenance={
                "runner": "MetrologyRunner_v1",
                "run_synthetic_verification": cfg.run_synthetic_verification,
            },
        )

        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            export_report_to_json(report, out_p / "metrology_report.json")
            export_summary_to_csv(report, out_p / "metrology_summary.csv")
            md_content = format_human_readable_summary(report)
            with open(out_p / "metrology_report.md", "w", encoding="utf-8") as f:
                f.write(md_content)

        return report

    # -------------------------------------------------------------------------
    # Workflow Execution Methods
    # -------------------------------------------------------------------------

    def _execute_workflow_1(self, limitations: list[str]) -> PhantomFrequencyResponseResult:
        w_cfg = self.config.workflow_1
        target_band = (w_cfg.target_band_hz[0], w_cfg.target_band_hz[1])

        # 1. Synthetic verification execution
        if self.config.run_synthetic_verification:
            fs = w_cfg.sample_rate_hz or 4000.0
            n_samples = int(fs * 2.0)
            rng = np.random.default_rng(42)
            stim = rng.standard_normal(n_samples).astype(np.float32) * 0.5
            # Known lowpass phantom filter at 250 Hz
            sos = scipy.signal.butter(4, 250.0, btype="lowpass", fs=fs, output="sos")
            resp = scipy.signal.sosfilt(sos, stim) + rng.standard_normal(n_samples).astype(np.float32) * 0.01
            return compute_phantom_frf(
                input_stimulus=stim,
                output_response=resp,
                sample_rate_hz=fs,
                target_band_hz=target_band,
                status=MeasurementStatus.SYNTHETIC_VERIFIED,
            )

        # 2. Bench measurement execution
        if (
            w_cfg.stimulus_wav_path
            and w_cfg.response_wav_path
            and not w_cfg.stimulus_wav_path.startswith("path/to/")
            and not w_cfg.response_wav_path.startswith("path/to/")
        ):
            try:
                stim_sig, stim_sr = load_audio_wav(w_cfg.stimulus_wav_path)
                resp_sig, resp_sr = load_audio_wav(w_cfg.response_wav_path)
                if stim_sr != resp_sr:
                    raise ValueError(f"Sample rate mismatch: stim {stim_sr} Hz vs resp {resp_sr} Hz")
                return compute_phantom_frf(
                    input_stimulus=stim_sig,
                    output_response=resp_sig,
                    sample_rate_hz=float(stim_sr),
                    target_band_hz=target_band,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 1 physical execution failed: {e}")
                res = PhantomFrequencyResponseResult(status=MeasurementStatus.FAILED.value)
                res.disclaimer = f"Execution error: {e}"
                return res

        # 3. Default: Not Yet Measured
        return PhantomFrequencyResponseResult(
            status=MeasurementStatus.NOT_YET_MEASURED.value,
            target_band_hz=w_cfg.target_band_hz,
        )

    def _execute_workflow_2(self, limitations: list[str]) -> SnrLevelRatioResult:
        w_cfg = self.config.workflow_2
        sensor = SensorConfiguration(
            sensor_model=w_cfg.sensor_model,
            interface_type=w_cfg.sensor_interface,
            nominal_sensitivity_declared=w_cfg.nominal_sensitivity,
        )
        filter_band = (w_cfg.filter_band_hz[0], w_cfg.filter_band_hz[1])

        # 1. Synthetic verification
        if self.config.run_synthetic_verification:
            fs = w_cfg.sample_rate_hz or 4000.0
            n_samples = int(fs * 2.0)
            t = np.linspace(0, 2.0, n_samples, endpoint=False)
            rng = np.random.default_rng(101)
            # Active signal: 100 Hz tone + low noise
            act = (0.2 * np.sin(2 * np.pi * 100.0 * t) + rng.standard_normal(n_samples) * 0.005).astype(np.float32)
            # Quiescent signal: only noise floor
            qui = (rng.standard_normal(n_samples) * 0.005).astype(np.float32)
            return compute_active_quiescent_snr(
                active_signal=act,
                quiescent_signal=qui,
                sample_rate_hz=fs,
                filter_band_hz=filter_band,
                sensor_config=sensor,
                room_acoustic_condition="Simulated quiet room",
                exciter_drive_level="Simulated -14 dBFS drive",
                status=MeasurementStatus.SYNTHETIC_VERIFIED,
            )

        # 2. Bench execution
        if (
            w_cfg.active_wav_path
            and w_cfg.quiescent_wav_path
            and not w_cfg.active_wav_path.startswith("path/to/")
            and not w_cfg.quiescent_wav_path.startswith("path/to/")
        ):
            try:
                act_sig, act_sr = load_audio_wav(w_cfg.active_wav_path)
                qui_sig, qui_sr = load_audio_wav(w_cfg.quiescent_wav_path)
                if act_sr != qui_sr:
                    raise ValueError(f"Sample rate mismatch: active {act_sr} Hz vs quiescent {qui_sr} Hz")
                return compute_active_quiescent_snr(
                    active_signal=act_sig,
                    quiescent_signal=qui_sig,
                    sample_rate_hz=float(act_sr),
                    filter_band_hz=filter_band,
                    sensor_config=sensor,
                    room_acoustic_condition=w_cfg.room_acoustic_condition,
                    exciter_drive_level=w_cfg.exciter_drive_level,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 2 physical execution failed: {e}")
                res = SnrLevelRatioResult(status=MeasurementStatus.FAILED.value, sensor_config=sensor)
                res.notes = f"Execution error: {e}"
                return res

        # 3. Default: Not Yet Measured
        return SnrLevelRatioResult(
            status=MeasurementStatus.NOT_YET_MEASURED.value,
            filter_band_hz=w_cfg.filter_band_hz,
            sensor_config=sensor,
        )

    def _execute_workflow_3(self, limitations: list[str]) -> RepeatabilityStudyResult:
        w_cfg = self.config.workflow_3

        # 1. Synthetic verification: 12 known runs
        if self.config.run_synthetic_verification:
            rng = np.random.default_rng(202)
            sim_runs = [float(round(v, 2)) for v in rng.normal(loc=28.5, scale=0.8, size=12)]
            outliers = [{"run_index": 11, "value_db": sim_runs[11], "cause": "Simulated tactile contact test, retained per protocol"}]
            return compute_repeatability_study(
                run_values=sim_runs,
                metric_name="active_to_quiescent_ratio_db",
                outliers_documented=outliers,
                status=MeasurementStatus.SYNTHETIC_VERIFIED,
            )

        # 2. Bench execution with precomputed or measured runs
        if len(w_cfg.precomputed_values) > 0:
            return compute_repeatability_study(
                run_values=w_cfg.precomputed_values,
                metric_name=w_cfg.metric_name,
                run_labels=w_cfg.run_labels if w_cfg.run_labels else None,
                outliers_documented=w_cfg.outliers_documented,
                status=MeasurementStatus.BENCH_MEASURED,
            )

        real_run_paths = [p for p in w_cfg.run_wav_paths if not p.startswith("path/to/")]
        if len(real_run_paths) > 0:
            try:
                rms_values = []
                labels = []
                for idx, path in enumerate(real_run_paths):
                    sig, _ = load_audio_wav(path)
                    r = float(np.sqrt(np.mean(sig ** 2)))
                    rms_values.append(r)
                    labels.append(Path(path).stem)
                return compute_repeatability_study(
                    run_values=rms_values,
                    metric_name="rms_level_fs",
                    run_labels=labels,
                    outliers_documented=w_cfg.outliers_documented,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 3 physical execution failed: {e}")
                res = RepeatabilityStudyResult(status=MeasurementStatus.FAILED.value)
                res.notes = f"Execution error: {e}"
                return res

        # 3. Default: Not Yet Measured
        return RepeatabilityStudyResult(
            status=MeasurementStatus.NOT_YET_MEASURED.value,
            metric_name=w_cfg.metric_name,
        )

    def _execute_workflow_4(self, limitations: list[str]) -> MainsInterferenceResult:
        w_cfg = self.config.workflow_4

        # 1. Synthetic verification
        if self.config.run_synthetic_verification:
            fs = w_cfg.sample_rate_hz or 4000.0
            n_samples = int(fs * 4.0)  # 4 seconds
            t = np.linspace(0, 4.0, n_samples, endpoint=False)
            rng = np.random.default_rng(303)
            # White noise floor + injected 50 Hz and 150 Hz mains hum
            sig = rng.standard_normal(n_samples) * 0.002
            sig += 0.01 * np.sin(2 * np.pi * 50.0 * t)  # 50 Hz fundamental
            sig += 0.003 * np.sin(2 * np.pi * 150.0 * t)  # 3rd harmonic
            return compute_mains_interference(
                quiescent_signal=sig,
                sample_rate_hz=fs,
                harmonics_hz=w_cfg.harmonics_hz,
                power_source_condition="Simulated AC mains adapter",
                shielding_condition="Simulated unshielded wire pickup",
                status=MeasurementStatus.SYNTHETIC_VERIFIED,
            )

        # 2. Bench execution
        if w_cfg.quiescent_wav_path and not w_cfg.quiescent_wav_path.startswith("path/to/"):
            try:
                sig, sr = load_audio_wav(w_cfg.quiescent_wav_path)
                return compute_mains_interference(
                    quiescent_signal=sig,
                    sample_rate_hz=float(sr),
                    harmonics_hz=w_cfg.harmonics_hz,
                    power_source_condition=w_cfg.power_source_condition,
                    shielding_condition=w_cfg.shielding_condition,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 4 physical execution failed: {e}")
                res = MainsInterferenceResult(status=MeasurementStatus.FAILED.value)
                res.notes = f"Execution error: {e}"
                return res

        # 3. Default: Not Yet Measured
        return MainsInterferenceResult(
            status=MeasurementStatus.NOT_YET_MEASURED.value,
            harmonics_hz=w_cfg.harmonics_hz,
            power_source_condition=w_cfg.power_source_condition,
            shielding_condition=w_cfg.shielding_condition,
        )

    def _execute_workflow_5(self, limitations: list[str]) -> LatencyMeasurementResult:
        w_cfg = self.config.workflow_5

        # 1. Synthetic verification: 5 synchronized trials
        if self.config.run_synthetic_verification:
            tx = [0.100, 0.600, 1.100, 1.600, 2.100]
            # Mean transit latency of 24.3 ms with 0.4 ms jitter
            rx = [0.1242, 0.6245, 1.1241, 1.6244, 2.1243]
            return compute_latency_measurement(
                stimulus_trigger_timestamps_s=tx,
                received_timestamps_s=rx,
                acoustic_cross_corr_lag_ms=2.1,
                playback_buffer_delay_ms=20.0,
                status=MeasurementStatus.SYNTHETIC_VERIFIED,
            )

        # 2. Bench execution: timestamp file or loopback audio
        if w_cfg.trigger_timestamps_path and not w_cfg.trigger_timestamps_path.startswith("path/to/"):
            try:
                p = Path(w_cfg.trigger_timestamps_path)
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tx_list = data.get("stimulus_trigger_timestamps_s", [])
                rx_list = data.get("received_timestamps_s", [])
                return compute_latency_measurement(
                    stimulus_trigger_timestamps_s=tx_list,
                    received_timestamps_s=rx_list,
                    acoustic_cross_corr_lag_ms=w_cfg.acoustic_cross_corr_lag_ms,
                    playback_buffer_delay_ms=w_cfg.playback_buffer_delay_ms,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 5 physical execution failed: {e}")
                res = LatencyMeasurementResult(status=MeasurementStatus.FAILED.value)
                res.notes = f"Execution error: {e}"
                return res

        if w_cfg.loopback_wav_path and not w_cfg.loopback_wav_path.startswith("path/to/"):
            try:
                data, sr = load_audio_wav(w_cfg.loopback_wav_path)
                return compute_latency_measurement(
                    dual_channel_loopback=data,
                    sample_rate_hz=float(sr),
                    playback_buffer_delay_ms=w_cfg.playback_buffer_delay_ms,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 5 physical execution failed: {e}")
                res = LatencyMeasurementResult(status=MeasurementStatus.FAILED.value)
                res.notes = f"Execution error: {e}"
                return res

        # 3. Default: Not Yet Measured
        return LatencyMeasurementResult(
            status=MeasurementStatus.NOT_YET_MEASURED.value,
            acoustic_relative_lag_ms=w_cfg.acoustic_cross_corr_lag_ms,
            playback_buffer_delay_ms=w_cfg.playback_buffer_delay_ms,
        )

    def _execute_workflow_6(self, limitations: list[str]) -> PacketDropContinuityResult:
        w_cfg = self.config.workflow_6

        # 1. Synthetic verification: 14,065 packets (~1800s continuous stream)
        if self.config.run_synthetic_verification:
            sim_packets = 14065
            seqs = list(range(1000, 1000 + sim_packets))
            return compute_continuity_drop_rate(
                sequence_numbers=seqs,
                samples_per_packet=128,
                sample_rate_hz=1000,
                total_elapsed_seconds=1800.32,
                status=MeasurementStatus.SYNTHETIC_VERIFIED,
            )

        # 2. Bench execution: sequence log file or session
        if w_cfg.stream_log_path and not w_cfg.stream_log_path.startswith("path/to/"):
            try:
                p = Path(w_cfg.stream_log_path)
                with open(p, "r", encoding="utf-8") as f:
                    seqs = json.load(f)
                if isinstance(seqs, dict):
                    seqs = seqs.get("sequence_numbers", [])
                return compute_continuity_drop_rate(
                    sequence_numbers=seqs,
                    samples_per_packet=w_cfg.samples_per_packet,
                    sample_rate_hz=w_cfg.sample_rate_hz,
                    total_elapsed_seconds=w_cfg.total_elapsed_seconds,
                    status=MeasurementStatus.BENCH_MEASURED,
                )
            except Exception as e:
                limitations.append(f"Workflow 6 physical execution failed: {e}")
                res = PacketDropContinuityResult(status=MeasurementStatus.FAILED.value)
                res.notes = f"Execution error: {e}"
                return res

        # 3. Default: Not Yet Measured
        return PacketDropContinuityResult(
            status=MeasurementStatus.NOT_YET_MEASURED.value,
        )

