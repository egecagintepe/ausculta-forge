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
    CINC2016_ADAPTER_STATUS,
)


def test_cinc2016_adapter_status_is_deferred():
    """Verify adapter explicitly advertises DEFERRED_FORMAT_ADAPTER."""
    assert CINC2016_ADAPTER_STATUS == "DEFERRED_FORMAT_ADAPTER"


def test_parse_cinc2016_annotations_refuses_with_truthful_error(tmp_path):
    """Verify parse function refuses because official format is *_StateAns.mat."""
    tsv_file = tmp_path / "a0001.tsv"
    tsv_file.write_text("0.0\t0.15\t1\n", encoding="utf-8")
    with pytest.raises(NotImplementedError, match="DEFERRED_FORMAT_ADAPTER.*_StateAns\\.mat"):
        parse_cinc2016_state_annotation_file(tsv_file, wav_duration_s=1.5)


def test_scan_cinc2016_records_refuses_with_truthful_error(tmp_path):
    """Verify scanner refuses because official format is *_StateAns.mat."""
    with pytest.raises(NotImplementedError, match="DEFERRED_FORMAT_ADAPTER.*_StateAns\\.mat"):
        scan_cinc2016_dataset(tmp_path)
