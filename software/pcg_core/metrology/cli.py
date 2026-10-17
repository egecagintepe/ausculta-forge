"""AuscultaForge — Metrology Experiment CLI Runner.

Command-line entrypoint to execute, verify, or template the six mandatory advisor measurements:
    python -m pcg_core.metrology.cli --generate-template template_config.json
    python -m pcg_core.metrology.cli --config experiment.json --output-dir reports/
    python -m pcg_core.metrology.cli --synthetic --output-dir reports/synthetic/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .models import SensorConfiguration
from .runner import (
    MetrologyExperimentConfig,
    MetrologyRunner,
    Workflow1Config,
    Workflow2Config,
    Workflow3Config,
    Workflow4Config,
    Workflow5Config,
    Workflow6Config,
)
from .reports import format_human_readable_summary


def create_template_config() -> dict:
    """Generate a clean, documented template configuration for physical laboratory experiments."""
    cfg = MetrologyExperimentConfig(
        title="Physical Bench Characterization — 6 Mandatory Measurements",
        apparatus_id="AUSCULTAFORGE_LAB_STATION_01",
        environment_notes="Laboratory bench at 22 C; quiet room ambient < 40 dBA.",
        sensor_declarations=[
            SensorConfiguration("INMP441", "I2S_DIGITAL", "-26 dBFS @ 94 dB SPL nominal", preamp_gain_db=0.0),
            SensorConfiguration("ECM_GENERIC", "ANALOG_PREAMP", "Relative sensitivity", preamp_gain_db=20.0),
        ],
        workflow_1=Workflow1Config(
            stimulus_wav_path="path/to/stimulus.wav",
            response_wav_path="path/to/phantom_response.wav",
            target_band_hz=[20.0, 500.0],
        ),
        workflow_2=Workflow2Config(
            active_wav_path="path/to/active_capture.wav",
            quiescent_wav_path="path/to/quiescent_capture.wav",
            filter_band_hz=[20.0, 500.0],
            room_acoustic_condition="Quiet laboratory ambient (< 40 dBA)",
            exciter_drive_level="PAM8403 unity gain, 0 dBFS digital output",
            sensor_model="INMP441",
            sensor_interface="I2S_DIGITAL",
            nominal_sensitivity="-26 dBFS nominal",
        ),
        workflow_3=Workflow3Config(
            run_wav_paths=[f"path/to/run_{i+1:02d}.wav" for i in range(10)],
            metric_name="rms_level_fs",
            outliers_documented=[],
        ),
        workflow_4=Workflow4Config(
            quiescent_wav_path="path/to/quiescent_capture.wav",
            harmonics_hz=[50.0, 100.0, 150.0, 200.0, 250.0],
            power_source_condition="AC mains adapter connected to test PC",
            shielding_condition="Twisted shielded sensor cable",
        ),
        workflow_5=Workflow5Config(
            trigger_timestamps_path="path/to/sync_timestamps.json",
            loopback_wav_path=None,
            acoustic_cross_corr_lag_ms=2.5,
            playback_buffer_delay_ms=25.0,
        ),
        workflow_6=Workflow6Config(
            stream_log_path="path/to/stream_sequence_log.json",
            samples_per_packet=128,
            sample_rate_hz=48000,
            total_elapsed_seconds=1800.0,
        ),
        run_synthetic_verification=False,
    )
    return cfg.to_dict()


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AuscultaForge Advisor Metrology Report Pipeline (Sprint 08)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to experiment JSON configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save JSON, CSV, and Markdown report artifacts.",
    )
    parser.add_argument(
        "--generate-template",
        type=str,
        default=None,
        help="Path where a template experiment configuration JSON should be written.",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Execute synthetic numerical verification mode (for pipeline validation without hardware).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress printing the markdown summary to stdout.",
    )

    parsed = parser.parse_args(args)

    if parsed.generate_template:
        t_path = Path(parsed.generate_template)
        t_path.parent.mkdir(parents=True, exist_ok=True)
        template_data = create_template_config()
        with open(t_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2)
        print(f"[OK] Generated metrology experiment template configuration at: {t_path}")
        return 0

    if parsed.config:
        cfg_path = Path(parsed.config)
        if not cfg_path.exists():
            print(f"[ERROR] Config file not found: {cfg_path}", file=sys.stderr)
            return 1
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = MetrologyExperimentConfig.from_dict(data)
    else:
        config = MetrologyExperimentConfig()

    if parsed.synthetic:
        config.run_synthetic_verification = True

    runner = MetrologyRunner(config)
    report = runner.run(output_dir=parsed.output_dir)

    if not parsed.quiet:
        summary_md = format_human_readable_summary(report)
        print("\n" + summary_md)

    if parsed.output_dir:
        print(f"\n[OK] Metrology reports generated in: {Path(parsed.output_dir).resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
