import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
import pytest

from pcg_core.experiment import ExperimentConfig, run_experiment, run_single_experiment


def make_test_wav(path: Path, fs: int = 2000, duration_s: float = 0.5, freq_hz: float = 60.0) -> Path:
    """Helper to generate a deterministic synthetic WAV file."""
    n_samples = int(fs * duration_s)
    t = np.arange(n_samples) / fs
    sig = (0.5 * np.sin(2 * np.pi * freq_hz * t) * 32767).astype(np.int16)
    wavfile.write(str(path), fs, sig)
    return path


def test_experiment_config_parsing(tmp_path: Path):
    """Verify ExperimentConfig parses valid JSON and rejects invalid parameters."""
    cfg_file = tmp_path / "test_config.json"
    cfg_data = {
        "name": "unit_test_cfg",
        "description": "Config for testing",
        "block_size": 128,
        "rolling_window_duration_s": 3.0,
        "filter": {
            "enabled": True,
            "filter_type": "butterworth_bandpass",
            "low_hz": 25.0,
            "high_hz": 400.0,
            "order": 4,
            "is_provisional": True
        },
        "spectral": {
            "nperseg": 128,
            "noverlap": 64
        }
    }
    cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

    cfg = ExperimentConfig.from_file(cfg_file)
    assert cfg.name == "unit_test_cfg"
    assert cfg.block_size == 128
    assert cfg.filter_low_hz == 25.0
    assert cfg.filter_high_hz == 400.0
    assert cfg.filter_order == 4

    # Invalid low >= high
    with pytest.raises(ValueError, match="Invalid filter frequencies"):
        invalid_data = dict(cfg_data)
        invalid_data["filter"] = {"enabled": True, "low_hz": 500.0, "high_hz": 200.0, "order": 4}
        ExperimentConfig.from_dict(invalid_data)

    # Invalid low <= 0
    with pytest.raises(ValueError, match="Invalid filter frequencies"):
        invalid_data = dict(cfg_data)
        invalid_data["filter"] = {"enabled": True, "low_hz": 0.0, "high_hz": 200.0, "order": 4}
        ExperimentConfig.from_dict(invalid_data)

    # Invalid block size
    with pytest.raises(ValueError, match="block_size must be positive"):
        invalid_data = dict(cfg_data)
        invalid_data["block_size"] = 0
        ExperimentConfig.from_dict(invalid_data)

    # Invalid spectral: noverlap >= nperseg
    with pytest.raises(ValueError, match="spectral_noverlap .* must be strictly less than"):
        invalid_data = dict(cfg_data)
        invalid_data["spectral"] = {"nperseg": 128, "noverlap": 128}
        ExperimentConfig.from_dict(invalid_data)

    # Malformed JSON file
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{this is not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed configuration JSON"):
        ExperimentConfig.from_file(bad_json)

    # Non-dict JSON file
    list_json = tmp_path / "list.json"
    list_json.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="Configuration root must be a JSON object"):
        ExperimentConfig.from_file(list_json)


def test_single_experiment_report_provenance(tmp_path: Path):
    """Verify generated experiment report contains all required provenance and metrics metadata."""
    wav_path = make_test_wav(tmp_path / "sample.wav", fs=2000, duration_s=0.5, freq_hz=50.0)
    out_dir = tmp_path / "exp_out"

    cfg = ExperimentConfig(
        name="provenance_test",
        filter_low_hz=20.0,
        filter_high_hz=200.0,
        filter_order=4,
    )

    report = run_single_experiment(wav_path, cfg, output_dir=out_dir)

    # 1. Experiment run info
    assert "experiment" in report
    assert "run_id" in report["experiment"]
    assert "processing_runtime_s" in report["experiment"]

    # 2. Provenance info
    assert "provenance" in report
    prov = report["provenance"]
    assert "python_version" in prov
    assert "numpy_version" in prov
    assert "scipy_version" in prov
    assert "git_commit_sha" in prov

    # 3. Input dataset info
    assert "input_dataset" in report
    inp = report["input_dataset"]
    assert inp["filename"] == "sample.wav"
    assert len(inp["sha256"]) == 64  # valid SHA-256 hex string
    assert inp["sample_rate_hz"] == 2000
    assert inp["total_samples"] == 1000
    assert inp["duration_s"] == pytest.approx(0.5)

    # 4. Results info
    res = report["results"]
    assert res["raw_metrics"]["rms"] > 0.0
    assert res["filtered_metrics"]["rms"] > 0.0
    assert abs(res["spectral_summary"]["peak_frequency_hz"] - 50.0) <= 15.0

    # 5. Output file on disk
    out_file = Path(report["_output_file"])
    assert out_file.exists()
    disk_data = json.loads(out_file.read_text(encoding="utf-8"))
    assert disk_data["experiment"]["run_id"] == report["experiment"]["run_id"]


def test_experiment_deterministic_execution(tmp_path: Path):
    """Verify identical inputs and configurations produce identical numerical metrics."""
    wav_path = make_test_wav(tmp_path / "det.wav", fs=2000, duration_s=0.4, freq_hz=70.0)
    cfg = ExperimentConfig(filter_low_hz=20.0, filter_high_hz=300.0)

    rep1 = run_single_experiment(wav_path, cfg, output_dir=tmp_path / "out1")
    rep2 = run_single_experiment(wav_path, cfg, output_dir=tmp_path / "out2")

    # Hashes and metrics must be bit-identical
    assert rep1["input_dataset"]["sha256"] == rep2["input_dataset"]["sha256"]
    assert rep1["results"]["raw_metrics"]["rms"] == rep2["results"]["raw_metrics"]["rms"]
    assert rep1["results"]["filtered_metrics"]["rms"] == rep2["results"]["filtered_metrics"]["rms"]
    assert rep1["results"]["filtered_metrics"]["peak_abs"] == rep2["results"]["filtered_metrics"]["peak_abs"]


def test_batch_experiment_directory(tmp_path: Path):
    """Verify batch processing over a directory of multiple WAV files."""
    audio_dir = tmp_path / "audio_batch"
    audio_dir.mkdir()
    make_test_wav(audio_dir / "rec1.wav", fs=2000, duration_s=0.2, freq_hz=40.0)
    make_test_wav(audio_dir / "rec2.wav", fs=2000, duration_s=0.3, freq_hz=80.0)

    cfg = ExperimentConfig()
    reports = run_experiment(audio_dir, cfg, output_dir=tmp_path / "batch_out")

    assert len(reports) == 2
    filenames = [r["input_dataset"]["filename"] for r in reports]
    assert "rec1.wav" in filenames
    assert "rec2.wav" in filenames


def test_experiment_missing_file_raises():
    """Verify non-existent input raises FileNotFoundError."""
    cfg = ExperimentConfig()
    with pytest.raises(FileNotFoundError):
        run_experiment("non_existent_recording.wav", cfg)


def test_git_commit_sha_fallback(monkeypatch, tmp_path: Path):
    """Verify that when git command fails, git_commit_sha gracefully falls back to None."""
    import subprocess
    def mock_check_output(*args, **kwargs):
        raise subprocess.SubprocessError("git not installed")

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    from pcg_core.experiment import get_git_commit_sha
    assert get_git_commit_sha() is None

    wav_path = make_test_wav(tmp_path / "fallback.wav", fs=2000, duration_s=0.2, freq_hz=50.0)
    cfg = ExperimentConfig()
    rep = run_single_experiment(wav_path, cfg, output_dir=tmp_path / "fb_out")
    assert rep["provenance"]["git_commit_sha"] is None
