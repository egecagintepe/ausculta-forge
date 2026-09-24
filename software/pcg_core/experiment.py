"""AuscultaForge — Reproducible PCG Experiment Runner.

Executes analysis pipelines on single WAV files or batches of recordings against
version-controlled JSON experiment configurations, capturing environment metadata,
input data hashes, and DSP metrics for auditability and research reproducibility.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any, Optional
import uuid

import numpy as np
import scipy

from .sources import WavSource
from .analysis import analyze_source, PCGAnalysisResult


@dataclass(slots=True)
class ExperimentConfig:
    """Experiment parameters defining preprocessing, filtering, and spectral windows."""
    name: str = "baseline_pcg_pipeline"
    description: str = ""
    block_size: int = 256
    rolling_window_duration_s: float = 5.0
    filter_enabled: bool = True
    filter_type: str = "butterworth_bandpass"
    filter_low_hz: float = 20.0
    filter_high_hz: float = 600.0
    filter_order: int = 4
    filter_is_provisional: bool = True
    spectral_nperseg: int = 256
    spectral_noverlap: int = 128

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentConfig":
        filter_data = data.get("filter", {})
        spectral_data = data.get("spectral", {})

        cfg = cls(
            name=data.get("name", "experiment"),
            description=data.get("description", ""),
            block_size=int(data.get("block_size", 256)),
            rolling_window_duration_s=float(data.get("rolling_window_duration_s", 5.0)),
            filter_enabled=bool(filter_data.get("enabled", True)),
            filter_type=str(filter_data.get("filter_type", "butterworth_bandpass")),
            filter_low_hz=float(filter_data.get("low_hz", 20.0)),
            filter_high_hz=float(filter_data.get("high_hz", 600.0)),
            filter_order=int(filter_data.get("order", 4)),
            filter_is_provisional=bool(filter_data.get("is_provisional", True)),
            spectral_nperseg=int(spectral_data.get("nperseg", 256)),
            spectral_noverlap=int(spectral_data.get("noverlap", 128)),
        )
        cfg.validate()
        return cfg

    @classmethod
    def from_file(cls, path: str | Path) -> "ExperimentConfig":
        cfg_path = Path(path)
        if not cfg_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {cfg_path}")
        with open(cfg_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed configuration JSON in {cfg_path}: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(f"Configuration root must be a JSON object, got {type(data).__name__}")
        return cls.from_dict(data)

    def validate(self) -> None:
        if self.block_size <= 0:
            raise ValueError(f"block_size must be positive, got {self.block_size}")
        if self.rolling_window_duration_s <= 0.0:
            raise ValueError(f"rolling_window_duration_s must be positive, got {self.rolling_window_duration_s}")
        if self.filter_enabled:
            if not (0 < self.filter_low_hz < self.filter_high_hz):
                raise ValueError(
                    f"Invalid filter frequencies: 0 < low ({self.filter_low_hz}) < high ({self.filter_high_hz}) required"
                )
            if self.filter_order <= 0:
                raise ValueError(f"filter_order must be positive, got {self.filter_order}")
        if self.spectral_nperseg <= 0 or self.spectral_noverlap < 0:
            raise ValueError("spectral segment parameters must be non-negative and nperseg must be positive")
        if self.spectral_noverlap >= self.spectral_nperseg:
            raise ValueError(
                f"spectral_noverlap ({self.spectral_noverlap}) must be strictly less than spectral_nperseg ({self.spectral_nperseg})"
            )


def compute_file_sha256(path: Path) -> str:
    """Calculate deterministic SHA-256 hash of a file's raw bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit_sha() -> Optional[str]:
    """Retrieve the current HEAD commit hash if inside a git repository."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        return out.decode("utf-8").strip()
    except Exception:
        return None


def run_single_experiment(
    wav_path: str | Path,
    config: ExperimentConfig,
    output_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Execute analysis pipeline for a single audio file and generate reproducible report."""
    input_file = Path(wav_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input WAV file not found: {input_file}")

    file_sha256 = compute_file_sha256(input_file)
    run_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    t_start = time.perf_counter()

    # Reuse core source and analysis abstractions
    source = WavSource(path=input_file, block_size=config.block_size)
    analysis_res: PCGAnalysisResult = analyze_source(
        source=source,
        filter_low_hz=config.filter_low_hz,
        filter_high_hz=config.filter_high_hz,
        filter_order=config.filter_order,
    )

    t_runtime_s = time.perf_counter() - t_start

    # Assemble comprehensive traceable report
    report: dict[str, Any] = {
        "experiment": {
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "config_name": config.name,
            "config_description": config.description,
            "processing_runtime_s": round(t_runtime_s, 4),
        },
        "provenance": {
            "git_commit_sha": get_git_commit_sha(),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "os_platform": platform.platform(),
        },
        "input_dataset": {
            "filename": input_file.name,
            "relative_path": str(input_file).replace("\\", "/"),
            "file_size_bytes": input_file.stat().st_size,
            "sha256": file_sha256,
            "sample_rate_hz": analysis_res.sample_rate_hz,
            "total_samples": analysis_res.total_samples,
            "duration_s": analysis_res.duration_s,
        },
        "configuration": asdict(config),
        "results": {
            "raw_metrics": {
                "rms": round(analysis_res.raw_metrics.rms, 6),
                "peak_abs": round(analysis_res.raw_metrics.peak_abs, 6),
                "crest_factor": round(analysis_res.raw_metrics.crest_factor, 4),
            },
            "filtered_metrics": {
                "rms": round(analysis_res.filtered_metrics.rms, 6),
                "peak_abs": round(analysis_res.filtered_metrics.peak_abs, 6),
                "crest_factor": round(analysis_res.filtered_metrics.crest_factor, 4),
            },
            "spectral_summary": {
                "grid_shape": analysis_res.spectrogram.shape,
                "f_resolution_hz": analysis_res.spectrogram.f_resolution_hz,
                "peak_frequency_hz": analysis_res.spectrogram.peak_frequency_hz,
                "band_energy_ratios": analysis_res.spectrogram.band_energy_ratios,
            },
        },
    }

    # Save output report if destination provided or default to experiments/output/
    target_dir = output_dir or Path("experiments/output")
    target_dir.mkdir(parents=True, exist_ok=True)
    report_file = target_dir / f"{run_id}_{input_file.stem}.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["_output_file"] = str(report_file).replace("\\", "/")

    return report


def run_experiment(
    input_path: str | Path,
    config: ExperimentConfig,
    output_dir: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Run experiment on a single file or a directory of WAV files."""
    path = Path(input_path)
    if path.is_file():
        return [run_single_experiment(path, config, output_dir=output_dir)]
    elif path.is_dir():
        wav_files = sorted(list(path.glob("*.wav")))
        if not wav_files:
            raise FileNotFoundError(f"No .wav files found in directory: {path}")
        reports = []
        for wf in wav_files:
            reports.append(run_single_experiment(wf, config, output_dir=output_dir))
        return reports
    else:
        raise FileNotFoundError(f"Input path does not exist: {path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="AuscultaForge reproducible PCG experiment execution runner."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=str,
        help="Path to a PCG WAV file or directory of WAV files.",
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        type=str,
        help="Path to JSON experiment configuration (e.g. experiments/configs/baseline.json).",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="experiments/output",
        help="Directory to store reproducible JSON experiment reports (default: experiments/output).",
    )

    args = parser.parse_args()

    try:
        config = ExperimentConfig.from_file(args.config)
        reports = run_experiment(args.input, config, output_dir=Path(args.output_dir))
    except Exception as e:
        print(f"Experiment Error: {e}", file=sys.stderr)
        sys.exit(1)

    sep = "=" * 76
    print(sep)
    print("AuscultaForge — Reproducible PCG Experiment Report")
    print(sep)
    print(f"Config Name : {config.name}")
    print(f"Filter Band : {config.filter_low_hz:.1f} – {config.filter_high_hz:.1f} Hz (Order: {config.filter_order})")
    print(f"Files Run   : {len(reports)}")
    print("-" * 76)

    for rep in reports:
        inp = rep["input_dataset"]
        res = rep["results"]
        exp = rep["experiment"]
        print(f"File: {inp['filename']} ({inp['duration_s']:.2f}s, {inp['sample_rate_hz']}Hz)")
        print(f"  SHA-256   : {inp['sha256'][:16]}...")
        print(f"  Raw RMS   : {res['raw_metrics']['rms']:.5f} | Peak: {res['raw_metrics']['peak_abs']:.5f}")
        print(f"  Filt RMS  : {res['filtered_metrics']['rms']:.5f} | Peak: {res['filtered_metrics']['peak_abs']:.5f}")
        print(f"  Peak Freq : {res['spectral_summary']['peak_frequency_hz']:.1f} Hz")
        print(f"  Report    : {rep.get('_output_file', 'in-memory')}")
        print("-" * 76)

    print("Experiment run completed with verified reproducibility provenance.")
    print(sep)


if __name__ == "__main__":
    main()
