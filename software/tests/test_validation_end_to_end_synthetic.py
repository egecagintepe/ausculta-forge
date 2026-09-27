"""End-to-end synthetic benchmark integration test (Requirement 68)."""

import pytest
import numpy as np
from pathlib import Path
from scipy.io import wavfile

from pcg_core.segmentation.validation.models import (
    SegmentationBenchmarkConfig,
    BenchmarkStatus,
)
from pcg_core.segmentation.validation.benchmark import run_segmentation_benchmark
from pcg_core.segmentation.validation.circor import scan_circor_dataset
from pcg_core.segmentation.validation.training import train_fold_springer_model
from pcg_core.segmentation.springer_config import SPRINGER_PHYSIONET_REFERENCE_V1


def _create_mini_circor_dataset(root_dir: Path) -> None:
    """Create 5 synthetic subjects with realistic PCG cycles and CirCor TSVs."""
    fs = 4000
    duration_s = 3.2

    # Heart sound template pattern:
    # 0.0 - 0.2: State 1 (S1)
    # 0.2 - 0.5: State 2 (Systole)
    # 0.5 - 0.7: State 3 (S2)
    # 0.7 - 1.2: State 4 (Diastole)
    # Repeated for 3 full cycles
    tsv_lines = [
        "0.0\t0.15\t1",
        "0.15\t0.45\t2",
        "0.45\t0.60\t3",
        "0.60\t1.05\t4",
        "1.05\t1.20\t1",
        "1.20\t1.50\t2",
        "1.50\t1.65\t3",
        "1.65\t2.10\t4",
        "2.10\t2.25\t1",
        "2.25\t2.55\t2",
        "2.55\t2.70\t3",
        "2.70\t3.15\t4",
    ]
    tsv_content = "\n".join(tsv_lines) + "\n"

    # Synthetic signal: 50 Hz carrier active during S1/S2 bursts
    t = np.linspace(0, duration_s, int(duration_s * fs), endpoint=False)
    sig = 0.05 * np.sin(2 * np.pi * 30 * t)  # baseline
    # Add bursts
    for burst_start, burst_end in [(0.0, 0.15), (0.45, 0.60), (1.05, 1.20), (1.50, 1.65), (2.10, 2.25), (2.55, 2.70)]:
        idx = (t >= burst_start) & (t <= burst_end)
        sig[idx] += 0.4 * np.sin(2 * np.pi * 75 * t[idx])

    pcm16 = (sig * 32767).astype(np.int16)

    # 5 subjects: 101, 102, 103, 104, 105
    for s_idx in range(101, 106):
        wav_path = root_dir / f"{s_idx}_AV.wav"
        tsv_path = root_dir / f"{s_idx}_AV.tsv"
        hea_path = root_dir / f"{s_idx}_AV.hea"
        wavfile.write(str(wav_path), fs, pcm16)
        tsv_path.write_text(tsv_content, encoding="utf-8")
        hea_path.write_text(f"{s_idx}_AV 1 4000 12800\n", encoding="utf-8")


def test_miniature_end_to_end_benchmark(tmp_path):
    dataset_dir = tmp_path / "circor_data"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    _create_mini_circor_dataset(dataset_dir)

    out_dir = tmp_path / "benchmarks"
    cache_dir = tmp_path / "cache"

    cfg = SegmentationBenchmarkConfig(
        fold_count=5,
        random_seed=2026,
        feature_cache_enabled=True,
    )

    report = run_segmentation_benchmark(
        dataset_root=dataset_dir,
        config=cfg,
        output_root=out_dir,
        cache_dir=cache_dir,
    )

    # 1. Status must be COMPLETE_DATASET (all 5 subjects processed)
    assert report.status == BenchmarkStatus.COMPLETE_DATASET.value
    assert report.coverage["total_eligible_records"] == 5
    assert len(report.fold_summaries) == 5

    # 2. Check each fold summary & model provenance
    for f in report.fold_summaries:
        assert f.train_subject_count == 4
        assert f.eval_subject_count == 1
        assert "auscultaforge_circor_springer_ref_v1_fold" in f.model_id
        # Model must not be a demo model
        assert "demo" not in f.model_id.lower()

    # 3. Check artifacts were persisted
    assert out_dir.exists()
    bench_dirs = list(out_dir.glob("circor_springer_benchmark_*"))
    assert len(bench_dirs) == 1
    bench_p = bench_dirs[0]
    assert (bench_p / "benchmark.json").is_file()
    assert (bench_p / "summary.csv").is_file()
    assert (bench_p / "folds.csv").is_file()


def test_demo_model_refusal(tmp_path):
    dataset_dir = tmp_path / "circor_data"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    _create_mini_circor_dataset(dataset_dir)

    # If demo profile is requested, benchmark runner MUST refuse
    bad_cfg = SegmentationBenchmarkConfig(
        profile_id="springer_demo_3feature_v1",
    )
    with pytest.raises(ValueError, match="strictly forbidden"):
        run_segmentation_benchmark(dataset_root=dataset_dir, config=bad_cfg)
