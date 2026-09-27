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


def parse_cinc2016_state_annotation_file(
    annot_path: Path | str,
    wav_duration_s: float,
) -> list[ReferenceStateInterval]:
    """Parse verified CinC 2016 hand-corrected segmentation annotations.
    
    Accepts three-column TSV/CSV format:
    col 1: start_s
    col 2: end_s
    col 3: state code in {0, 1, 2, 3, 4}
    """
    p = Path(annot_path)
    if not p.is_file():
        raise FileNotFoundError(f"CinC 2016 annotation file not found: {p}")

    intervals: list[ReferenceStateInterval] = []
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            parts = line_str.replace(",", "\t").split("\t")
            if len(parts) < 3:
                parts = line_str.split()
            if len(parts) < 3:
                continue

            try:
                start_s = float(parts[0])
                end_s = float(parts[1])
                st = int(float(parts[2]))
            except ValueError:
                continue

            if 0.0 <= start_s <= end_s and st in (0, 1, 2, 3, 4):
                intervals.append(
                    ReferenceStateInterval(
                        state=st,
                        start_s=start_s,
                        end_s=end_s,
                        duration_s=end_s - start_s,
                    )
                )

    if not intervals:
        raise ValueError(f"No valid intervals found in CinC 2016 annotation: {p.name}")

    return sorted(intervals, key=lambda iv: iv.start_s)


def scan_cinc2016_dataset(
    root_path: Path | str,
    max_records: Optional[int] = None,
) -> list[AnnotatedPCGRecord]:
    """Scan and parse CinC 2016 records for secondary cross-database evaluation."""
    root = Path(root_path)
    if not root.exists():
        raise FileNotFoundError(f"CinC 2016 dataset path does not exist: {root}")

    wav_files = sorted(root.glob("*.wav"))
    if not wav_files:
        wav_files = sorted(root.rglob("*.wav"))

    records: list[AnnotatedPCGRecord] = []

    for wav_file in wav_files:
        stem = wav_file.stem
        # Look for matching .tsv or .csv annotation
        tsv_file = wav_file.with_suffix(".tsv")
        if not tsv_file.exists():
            tsv_file = wav_file.with_suffix(".csv")
        if not tsv_file.exists():
            continue

        try:
            fs, duration_s, _ = read_wav_header_metadata(wav_file)
            intervals = parse_cinc2016_state_annotation_file(tsv_file, duration_s)
        except Exception:
            continue

        # In CinC 2016, public stems like a0001, b0002 are recording IDs,
        # but subject mapping is not disclosed. We explicitly record this limitation.
        rec = AnnotatedPCGRecord(
            dataset_id=CINC2016_DATASET_ID,
            dataset_version=CINC2016_DATASET_VERSION,
            record_id=stem,
            subject_id=f"cinc16_{stem}",  # Conservative unique key; not safe for within-dataset splits
            sample_rate_hz=fs,
            duration_s=duration_s,
            annotation_intervals=intervals,
            auscultation_location=None,
            wav_path=str(wav_file.resolve()),
            annotation_path=str(tsv_file.resolve()),
            metadata={
                "doi": CINC2016_DOI,
                "url": CINC2016_URL,
                "usage_role": "CROSS_DATABASE_EVALUATION_ONLY",
                "subject_identity_warning": "No verified subject grouping available in public training subset.",
            },
        )
        records.append(rec)
        if max_records is not None and len(records) >= max_records:
            break

    return records
