"""Tests for CinC 2016 secondary cross-database adapter."""

import pytest
import numpy as np
from pathlib import Path
from scipy.io import wavfile

from pcg_core.segmentation.validation.cinc2016 import (
    parse_cinc2016_state_annotation_file,
    scan_cinc2016_dataset,
    CINC2016_DATASET_ID,
    CINC2016_DATASET_VERSION,
)


def _write_synth_wav(path: Path, duration_s: float = 2.0, fs: int = 2000) -> None:
    t = np.linspace(0, duration_s, int(duration_s * fs), endpoint=False)
    sig = (0.2 * np.sin(2 * np.pi * 60 * t) * 32767).astype(np.int16)
    wavfile.write(str(path), fs, sig)


def test_parse_cinc2016_annotations_valid(tmp_path):
    tsv_file = tmp_path / "a0001.tsv"
    content = (
        "0.0\t0.15\t1\n"
        "0.15\t0.45\t2\n"
        "0.45\t0.60\t3\n"
        "0.60\t1.10\t4\n"
    )
    tsv_file.write_text(content, encoding="utf-8")

    intervals = parse_cinc2016_state_annotation_file(tsv_file, wav_duration_s=1.5)
    assert len(intervals) == 4
    assert intervals[0].state == 1
    assert intervals[1].state == 2
    assert intervals[2].state == 3
    assert intervals[3].state == 4


def test_scan_cinc2016_records(tmp_path):
    _write_synth_wav(tmp_path / "a0001.wav", duration_s=2.0)
    (tmp_path / "a0001.tsv").write_text("0.1\t0.25\t1\n0.25\t0.5\t2\n0.5\t0.65\t3\n0.65\t1.0\t4\n", encoding="utf-8")

    records = scan_cinc2016_dataset(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec.dataset_id == CINC2016_DATASET_ID
    assert rec.dataset_version == CINC2016_DATASET_VERSION
    assert rec.record_id == "a0001"
    # Prohibit unverified subject grouping claims:
    assert rec.subject_id == "cinc16_a0001"
