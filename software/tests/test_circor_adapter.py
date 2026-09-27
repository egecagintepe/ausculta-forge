"""Tests for CirCor DigiScope PCG dataset adapter and verification semantics."""

import pytest
import numpy as np
from pathlib import Path
from scipy.io import wavfile

from pcg_core.segmentation.validation.circor import (
    parse_circor_filename,
    parse_circor_tsv,
    scan_circor_dataset,
    CirCorScanResult,
    CIRCOR_DATASET_NAME,
    CIRCOR_DATASET_VERSION,
    CIRCOR_DOI,
    CIRCOR_TOTAL_SUBJECTS,
    CIRCOR_TOTAL_RECORDINGS,
    CIRCOR_UNCOMPRESSED_SIZE_MB,
    KNOWN_LOCATIONS,
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
    with pytest.raises(ValueError, match="must begin with a numeric subject ID"):
        parse_circor_filename("not_a_valid_file.wav")

    with pytest.raises(ValueError, match="missing location code"):
        parse_circor_filename("12345.wav")

    with pytest.raises(ValueError, match="Invalid auscultation location"):
        parse_circor_filename("12345_XX.wav")


def test_parse_circor_repeated_suffixes():
    subj1, loc1 = parse_circor_filename("50782_MV_1.wav")
    subj2, loc2 = parse_circor_filename("50782_MV_2.wav")
    assert subj1 == "50782" and loc1 == "MV"
    assert subj2 == "50782" and loc2 == "MV"


def test_circor_v103_metadata_constants():
    """Verify official PhysioNet CirCor v1.0.3 metadata."""
    assert CIRCOR_DATASET_NAME == "The CirCor DigiScope Phonocardiogram Dataset"
    assert CIRCOR_DATASET_VERSION == "1.0.3"
    assert CIRCOR_DOI == "10.13026/tshs-mw03"
    assert CIRCOR_DOI != "10.13026/trmv-vx89"
    assert CIRCOR_TOTAL_SUBJECTS == 1568
    assert CIRCOR_TOTAL_RECORDINGS == 5272
    assert CIRCOR_UNCOMPRESSED_SIZE_MB == 558.9
    assert KNOWN_LOCATIONS == {"AV", "MV", "PV", "TV", "Phc"}


def test_scan_circor_dataset_multi_location(tmp_path):
    tsv_content = "0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n"
    hea_content = "dummy header line\n"

    # Subject 100 with AV and MV
    _write_synth_wav(tmp_path / "100_AV.wav", duration_s=2.0)
    (tmp_path / "100_AV.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "100_AV.hea").write_text(hea_content, encoding="utf-8")

    _write_synth_wav(tmp_path / "100_MV.wav", duration_s=2.0)
    (tmp_path / "100_MV.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "100_MV.hea").write_text(hea_content, encoding="utf-8")

    # Subject 200 with PV
    _write_synth_wav(tmp_path / "200_PV.wav", duration_s=2.0)
    (tmp_path / "200_PV.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "200_PV.hea").write_text(hea_content, encoding="utf-8")

    # Missing TSV for 300_TV.wav (has .hea)
    _write_synth_wav(tmp_path / "300_TV.wav", duration_s=2.0)
    (tmp_path / "300_TV.hea").write_text(hea_content, encoding="utf-8")

    scan_res = scan_circor_dataset(tmp_path)
    assert isinstance(scan_res, CirCorScanResult)
    assert len(scan_res) == 3
    assert scan_res.records_eligible == 3
    assert scan_res.files_seen == 4
    assert scan_res.records_excluded == 1
    assert scan_res.exclusion_reasons.get("MISSING_TSV") == 1

    subj_ids = {r.subject_id for r in scan_res}
    assert subj_ids == {"100", "200"}


def test_scan_circor_requires_hea_companion(tmp_path):
    tsv_content = "0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n"
    # Create WAV and TSV but NO .hea
    _write_synth_wav(tmp_path / "400_AV.wav", duration_s=2.0)
    (tmp_path / "400_AV.tsv").write_text(tsv_content, encoding="utf-8")

    scan_res = scan_circor_dataset(tmp_path)
    assert len(scan_res) == 0
    assert scan_res.records_excluded == 1
    assert scan_res.exclusion_reasons.get("MISSING_HEA") == 1


def test_scan_circor_repeated_files_no_collision(tmp_path):
    tsv_content = "0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n"
    hea_content = "dummy header line\n"

    # 50782_MV_1 and 50782_MV_2
    _write_synth_wav(tmp_path / "50782_MV_1.wav", duration_s=2.0)
    (tmp_path / "50782_MV_1.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "50782_MV_1.hea").write_text(hea_content, encoding="utf-8")

    _write_synth_wav(tmp_path / "50782_MV_2.wav", duration_s=2.0)
    (tmp_path / "50782_MV_2.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "50782_MV_2.hea").write_text(hea_content, encoding="utf-8")

    scan_res = scan_circor_dataset(tmp_path)
    assert len(scan_res) == 2
    rec_ids = {r.record_id for r in scan_res}
    assert rec_ids == {"50782_MV_1", "50782_MV_2"}
    for r in scan_res:
        assert r.subject_id == "50782"
        assert r.auscultation_location == "MV"


def test_scan_circor_accounting_exclusions(tmp_path):
    hea_content = "header\n"
    tsv_content = "0.0\t0.2\t1\n0.2\t0.5\t2\n0.5\t0.7\t3\n0.7\t1.2\t4\n"

    # 1. Valid record
    _write_synth_wav(tmp_path / "10_AV.wav", duration_s=2.0)
    (tmp_path / "10_AV.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "10_AV.hea").write_text(hea_content, encoding="utf-8")

    # 2. MISSING_HEA
    _write_synth_wav(tmp_path / "20_AV.wav", duration_s=2.0)
    (tmp_path / "20_AV.tsv").write_text(tsv_content, encoding="utf-8")

    # 3. MISSING_TSV
    _write_synth_wav(tmp_path / "30_AV.wav", duration_s=2.0)
    (tmp_path / "30_AV.hea").write_text(hea_content, encoding="utf-8")

    # 4. INVALID_LOCATION
    _write_synth_wav(tmp_path / "40_XX.wav", duration_s=2.0)
    (tmp_path / "40_XX.tsv").write_text(tsv_content, encoding="utf-8")
    (tmp_path / "40_XX.hea").write_text(hea_content, encoding="utf-8")

    # 5. INVALID_FILENAME
    _write_synth_wav(tmp_path / "invalidfilename.wav", duration_s=2.0)

    # 6. INVALID_TSV (malformed TSV)
    _write_synth_wav(tmp_path / "50_AV.wav", duration_s=2.0)
    (tmp_path / "50_AV.tsv").write_text("invalid tsv content\n", encoding="utf-8")
    (tmp_path / "50_AV.hea").write_text(hea_content, encoding="utf-8")

    scan_res = scan_circor_dataset(tmp_path)
    assert scan_res.files_seen == 6
    assert scan_res.records_eligible == 1
    assert scan_res.records_excluded == 5
    assert scan_res.exclusion_reasons["MISSING_HEA"] == 1
    assert scan_res.exclusion_reasons["MISSING_TSV"] == 1
    assert scan_res.exclusion_reasons["INVALID_LOCATION"] == 1
    assert scan_res.exclusion_reasons["INVALID_FILENAME"] == 1
    assert scan_res.exclusion_reasons["INVALID_TSV"] == 1
