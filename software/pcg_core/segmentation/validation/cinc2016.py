"""AuscultaForge — CinC 2016 Secondary Cross-Database Dataset Adapter.

Provides loading and verification for the PhysioNet / Computing in Cardiology
Challenge 2016 heart sound segmentation dataset.

Primary Purpose:
- SECONDARY / CROSS-DATABASE evaluation of models trained on CirCor.
- Does NOT pool CinC 2016 metrics with CirCor metrics.
- Explicitly flags that CinC 2016 public training records (e.g. a0001, b0002)
  lack verified subject-to-recording mappings; within-dataset random splitting is
  prohibited to prevent unverified subject leakage.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Sequence
import scipy.io.wavfile

from .models import AnnotatedPCGRecord, ReferenceStateInterval
from .circor import read_wav_header_metadata

CINC2016_DATASET_ID = "CINC_2016"
CINC2016_DATASET_VERSION = "1.0.0"
CINC2016_DOI = "10.13026/C2Z012"
CINC2016_URL = "https://physionet.org/content/challenge-2016/1.0.0/"
CINC2016_ADAPTER_STATUS = "DEFERRED_FORMAT_ADAPTER"


def parse_cinc2016_state_annotation_file(
    annot_path: Path | str,
    wav_duration_s: float,
) -> list[ReferenceStateInterval]:
    """Parse CinC 2016 hand-corrected segmentation annotations.

    Status: DEFERRED_FORMAT_ADAPTER
    Official PhysioNet Challenge 2016 hand-corrected annotations are stored as
    *_StateAns.mat files (e.g. annotations/hand_corrected/training-a_StateAns/a0001_StateAns.mat),
    NOT sibling .tsv/.csv files.
    """
    raise NotImplementedError(
        "CinC 2016 format adapter is marked DEFERRED_FORMAT_ADAPTER: "
        "Official PhysioNet Challenge 2016 hand-corrected annotations are stored as "
        "*_StateAns.mat files (e.g., annotations/hand_corrected/training-a_StateAns/a0001_StateAns.mat) "
        "in MATLAB format, not sibling .tsv/.csv. Cross-database execution is refused until "
        "the official *_StateAns.mat parser is implemented."
    )


def scan_cinc2016_dataset(
    root_path: Path | str,
    max_records: Optional[int] = None,
) -> list[AnnotatedPCGRecord]:
    """Scan and parse CinC 2016 records for secondary cross-database evaluation.

    Status: DEFERRED_FORMAT_ADAPTER
    Refuses execution truthfully until official *_StateAns.mat parser is implemented.
    """
    raise NotImplementedError(
        "CinC 2016 format adapter is marked DEFERRED_FORMAT_ADAPTER: "
        "Official PhysioNet Challenge 2016 hand-corrected annotations are stored as "
        "*_StateAns.mat files (e.g., annotations/hand_corrected/training-a_StateAns/a0001_StateAns.mat) "
        "in MATLAB format, not sibling .tsv/.csv. Cross-database execution is refused until "
        "the official *_StateAns.mat parser is implemented."
    )
