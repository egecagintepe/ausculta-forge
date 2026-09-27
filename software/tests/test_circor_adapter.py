"""Tests for CirCor DigiScope PCG dataset adapter and verification semantics."""

import pytest
import numpy as np
from pathlib import Path
from scipy.io import wavfile

from pcg_core.segmentation.validation.circor import (
    parse_circor_filename,
    parse_circor_tsv,
    scan_circor_dataset,
)


def _write_synth_wav(path: Path, duration_s: float = 3.0, sample_rate_hz: int = 4000) -> None:
    t = np.linspace(0, duration_s, int(duration_s * sample_rate_hz), endpoint=False)
    sig = (0.3 * np.sin(2 * np.pi * 50 * t) * 32767).astype(np.int16)
    wavfile.write(str(path), sample_rate_hz, sig)


def test_parse_circor_filename_valid():
    subj, loc = parse_circor_filename("12345_AV.wav")
    assert subj == "12345"
    assert loc == "AV"

    subj, loc = parse_circor_filename("2530_MV_1.tsv")
    assert subj == "2530"
    assert loc == "MV"

    subj, loc = parse_circor_filename("999_Phc.wav")
    assert subj == "999"
    assert loc == "Phc"


def test_parse_circor_filename_invalid():
    with pytest.raises(ValueError):
        parse_circor_filename("not_a_valid_file.wav")

    with pytest.raises(ValueError):
        parse_circor_filename("12345.wav")


def test_parse_circor_tsv_valid_and_sorted(tmp_path):
    tsv_file = tmp_path / "test.tsv"
    content = (
        "0.0\t0.2\t0\n"
        "0.2\t0.32\t1\n"
        "0.32\t0.58\t2\n"
        "0.58\t0.70\t3\n"
        "0.70\t1.10\t4\n"
    )
    tsv_file.write_text(content, encoding="utf-8")

    intervals = parse_circor_tsv(tsv_file, wav_duration_s=1.2)
    assert len(intervals) == 5
    assert intervals[0].state == 0
    assert intervals[0].start_s == 0.0
    assert intervals[0].end_s == 0.2
    assert intervals[1].state == 1
    assert intervals[2].state == 2
    assert intervals[3].state == 3
    assert intervals[4].state == 4


def test_parse_circor_tsv_state_zero_preserved(tmp_path):
    tsv_file = tmp_path / "zero.tsv"
    content = "0.0\t0.5\t0\n0.5\t1.0\t1\n"
    tsv_file.write_text(content, encoding="utf-8")

    intervals = parse_circor_tsv(tsv_file, wav_duration_s=1.0)
    assert intervals[0].state == 0
    assert intervals[0].duration_s == 0.5


def test_parse_circor_tsv_malformed_columns(tmp_path):
    tsv_file = tmp_path / "bad_cols.tsv"
    tsv_file.write_text("0.0\t0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected 3 columns"):
        parse_circor_tsv(tsv_file, wav_duration_s=1.0)


def test_parse_circor_tsv_negative_time(tmp_path):
    tsv_file = tmp_path / "neg.tsv"
    tsv_file.write_text("-0.1\t0.5\t1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Negative start"):
        parse_circor_tsv(tsv_file, wav_duration_s=1.0)


def test_parse_circor_tsv_end_before_start(tmp_path):
    tsv_file = tmp_path / "inverted.tsv"
    tsv_file.write_text("0.5\t0.2\t1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="precedes start"):
        parse_circor_tsv(tsv_file, wav_duration_s=1.0)


def test_parse_circor_tsv_invalid_state_code(tmp_path):
    tsv_file = tmp_path / "invalid_state.tsv"
    tsv_file.write_text("0.0\t0.5\t5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported state"):
        parse_circor_tsv(tsv_file, wav_duration_s=1.0)


def test_parse_circor_tsv_exceeds_duration_tolerance(tmp_path):
    tsv_file = tmp_path / "exceed.tsv"
    tsv_file.write_text("0.0\t5.0\t1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exceeds WAV duration"):
        parse_circor_tsv(tsv_file, wav_duration_s=2.0)


def test_scan_circor_dataset_multi_location(tmp_path):
    # Subject 100 with AV and MV
    _write_synth_wav(tmp_path / "100_AV.wav", duration_s=2.0)
    (tmp_path / "100_AV.tsv").write_text("0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n", encoding="utf-8")

    _write_synth_wav(tmp_path / "100_MV.wav", duration_s=2.0)
    (tmp_path / "100_MV.tsv").write_text("0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n", encoding="utf-8")

    # Subject 200 with PV
    _write_synth_wav(tmp_path / "200_PV.wav", duration_s=2.0)
    (tmp_path / "200_PV.tsv").write_text("0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n", encoding="utf-8")

    # Missing TSV for 300_TV.wav
    _write_synth_wav(tmp_path / "300_TV.wav", duration_s=2.0)

    records = scan_circor_dataset(tmp_path)
    assert len(records) == 3
    # Check that subjects 100 and 200 are included
    subj_ids = {r.subject_id for r in records}
    assert subj_ids == {"100", "200"}

