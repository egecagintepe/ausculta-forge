"""AuscultaForge — CirCor DigiScope Dataset Adapter.

Parses and validates the PhysioNet CirCor DigiScope Phonocardiogram Dataset (v1.0.3).
Handles:
- Filename pattern extraction (SUBJECTID_LOCATION.wav / .tsv)
- Strict TSV segment validation (start, end, state in {0, 1, 2, 3, 4})
- Duration alignment checks (with small tolerance)
- Integrity verification against SHA256SUMS.txt when present
- Safe subject ID grouping

Official Provenance:
- Dataset: The CirCor DigiScope Phonocardiogram Dataset (Version 1.0.3)
- PhysioNet: https://physionet.org/content/circor-heart-sound/1.0.3/
- DOI: 10.13026/trmv-vx89
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from typing import Any, Optional, Sequence
import wave

from .models import AnnotatedPCGRecord, ReferenceStateInterval

CIRCOR_DATASET_ID = "CIRCOR_DIGISCOPE"
CIRCOR_DATASET_VERSION = "1.0.3"
CIRCOR_DOI = "10.13026/trmv-vx89"
CIRCOR_URL = "https://physionet.org/content/circor-heart-sound/1.0.3/"

KNOWN_LOCATIONS = {"AV", "MV", "PV", "TV", "Phc"}


def parse_circor_filename(stem_or_filename: str) -> tuple[str, Optional[str]]:
    """Extract numeric subject ID and auscultation location code from CirCor filename stem.
    
    Examples:
    - '2530_AV' -> ('2530', 'AV')
    - '2530_AV_1.wav' -> ('2530', 'AV')
    - '85340_MV.tsv' -> ('85340', 'MV')
    """
    stem = Path(stem_or_filename).stem
    parts = stem.split("_")
    if not parts or not parts[0].isdigit():
        raise ValueError(f"CirCor filename must begin with a numeric subject ID, got: '{stem_or_filename}'")

    subject_id = parts[0]
    if len(parts) < 2:
        raise ValueError(f"CirCor filename missing location code: '{stem_or_filename}'")
    location: Optional[str] = parts[1]

    return subject_id, location


def parse_circor_tsv(
    tsv_path: Path | str,
    wav_duration_s: float,
    tolerance_s: float = 0.05,
) -> list[ReferenceStateInterval]:
    """Strictly parse and validate a CirCor .tsv interval segmentation file.
    
    Columns:
    1: start time in seconds (float)
    2: end time in seconds (float)
    3: state (int in {0, 1, 2, 3, 4})
    
    Rules:
    - Finite float values
    - start <= end
    - Valid state code
    - Strictly sorted in time
    - Intervals do not grossly exceed WAV duration (+ tolerance_s)
    """
    tsv_p = Path(tsv_path)
    if not tsv_p.exists():
        raise FileNotFoundError(f"CirCor TSV file not found: {tsv_p}")

    intervals: list[ReferenceStateInterval] = []
    prev_end: float = -1.0

    with open(tsv_p, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            parts = re.split(r"[\t\s,]+", line_str)
            if len(parts) < 3:
                raise ValueError(
                    f"Invalid CirCor TSV line {line_num} in {tsv_p.name}: expected 3 columns, found {len(parts)}: '{line_str}'"
                )

            try:
                start_s = float(parts[0])
                end_s = float(parts[1])
                state_code = int(float(parts[2]))
            except ValueError as e:
                raise ValueError(
                    f"Malformed numeric values on line {line_num} in {tsv_p.name}: '{line_str}' ({e})"
                )

            if start_s < 0.0:
                raise ValueError(f"Negative start time on line {line_num} in {tsv_p.name}: {start_s}s")
            if end_s < start_s:
                raise ValueError(
                    f"Interval end precedes start on line {line_num} in {tsv_p.name}: start={start_s}s, end={end_s}s"
                )
            if state_code not in (0, 1, 2, 3, 4):
                raise ValueError(
                    f"Unsupported state identifier {state_code} on line {line_num} in {tsv_p.name}. "
                    f"Allowed states: 0=UNANNOTATED, 1=S1, 2=SYSTOLE, 3=S2, 4=DIASTOLE."
                )

            # Monotonic order check
            if start_s < prev_end - 1e-4:
                raise ValueError(
                    f"Unsorted or overlapping intervals on line {line_num} in {tsv_p.name}: "
                    f"start {start_s}s < previous end {prev_end}s"
                )

            # Bounds check against WAV duration
            if start_s > wav_duration_s + tolerance_s or end_s > wav_duration_s + tolerance_s:
                raise ValueError(
                    f"Interval ({start_s:.3f}s - {end_s:.3f}s) exceeds WAV duration ({wav_duration_s:.3f}s) "
                    f"beyond tolerance on line {line_num} in {tsv_p.name}"
                )

            duration_s = max(0.0, end_s - start_s)
            intervals.append(
                ReferenceStateInterval(
                    state=state_code,
                    start_s=start_s,
                    end_s=end_s,
                    duration_s=duration_s,
                )
            )
            prev_end = end_s

    if not intervals:
        raise ValueError(f"CirCor TSV file {tsv_p.name} contains zero valid interval entries.")

    return intervals


def read_wav_header_metadata(wav_path: Path | str) -> tuple[float, float, int]:
    """Read sample rate, duration in seconds, and total sample count from WAV header.
    
    Returns
    -------
    tuple[float, float, int]
        (sample_rate_hz, duration_s, total_samples)
    """
    p = Path(wav_path)
    if not p.exists():
        raise FileNotFoundError(f"WAV file not found: {p}")

    with wave.open(str(p), "rb") as wf:
        sample_rate = float(wf.getframerate())
        n_frames = wf.getnframes()
        duration_s = n_frames / sample_rate if sample_rate > 0 else 0.0

    return sample_rate, duration_s, n_frames


def verify_sha256_checksum(file_path: Path | str, expected_hash: str) -> bool:
    """Verify SHA256 hash of a local file against expected checksum."""
    p = Path(file_path)
    if not p.is_file():
        return False
    sha = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest().lower() == expected_hash.lower()


def load_circor_checksums(root_path: Path | str) -> dict[str, str]:
    """Parse SHA256SUMS.txt if present in the dataset root or parent directory."""
    root = Path(root_path)
    candidate_paths = [
        root / "SHA256SUMS.txt",
        root.parent / "SHA256SUMS.txt",
        root / "training_data" / "SHA256SUMS.txt",
    ]
    for cp in candidate_paths:
        if cp.is_file():
            checksums: dict[str, str] = {}
            with open(cp, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        chk = parts[0]
                        fname = os.path.basename(parts[1])
                        checksums[fname] = chk
            return checksums
    return {}


def scan_circor_dataset(
    root_path: Path | str,
    max_subjects: Optional[int] = None,
    max_records: Optional[int] = None,
    verify_checksums: bool = False,
) -> list[AnnotatedPCGRecord]:
    """Discover, parse, and validate all eligible CirCor records in a directory.
    
    Parameters
    ----------
    root_path : Path | str
        Root directory containing CirCor files (or a 'training_data' subfolder).
    max_subjects : Optional[int]
        Debug/pilot constraint: stop after collecting this many subjects.
    max_records : Optional[int]
        Debug/pilot constraint: stop after collecting this many records.
    verify_checksums : bool
        If True, verify available files against SHA256SUMS.txt if found.
        
    Returns
    -------
    list[AnnotatedPCGRecord]
        List of strictly validated CirCor records.
    """
    root = Path(root_path)
    if not root.exists():
        raise FileNotFoundError(f"CirCor dataset path does not exist: {root}")

    # If 'training_data' directory exists inside root, search inside it
    search_dir = root / "training_data" if (root / "training_data").is_dir() else root

    checksums = load_circor_checksums(root) if verify_checksums else {}

    # Find all .wav files in search directory
    wav_files = sorted(search_dir.glob("*.wav"))
    if not wav_files:
        # Also check subdirectories recursively
        wav_files = sorted(search_dir.rglob("*.wav"))

    records: list[AnnotatedPCGRecord] = []
    seen_subjects: set[str] = set()

    for wav_file in wav_files:
        stem = wav_file.stem
        tsv_file = wav_file.with_suffix(".tsv")

        # Skip if companion TSV does not exist
        if not tsv_file.exists():
            continue

        try:
            subject_id, location = parse_circor_filename(stem)
        except ValueError:
            # Skip files that don't match CirCor subject naming
            continue

        # Check subject pilot limit
        if max_subjects is not None and subject_id not in seen_subjects:
            if len(seen_subjects) >= max_subjects:
                continue

        # Verify checksums if available and requested
        if verify_checksums and checksums:
            if wav_file.name in checksums:
                if not verify_sha256_checksum(wav_file, checksums[wav_file.name]):
                    raise ValueError(f"Checksum mismatch for WAV: {wav_file.name}")
            if tsv_file.name in checksums:
                if not verify_sha256_checksum(tsv_file, checksums[tsv_file.name]):
                    raise ValueError(f"Checksum mismatch for TSV: {tsv_file.name}")

        try:
            fs, duration_s, _ = read_wav_header_metadata(wav_file)
            intervals = parse_circor_tsv(tsv_file, wav_duration_s=duration_s)
        except Exception:
            # Any unparsable or invalid file is excluded from eligibility
            continue

        rec = AnnotatedPCGRecord(
            dataset_id=CIRCOR_DATASET_ID,
            dataset_version=CIRCOR_DATASET_VERSION,
            record_id=stem,
            subject_id=subject_id,
            sample_rate_hz=fs,
            duration_s=duration_s,
            annotation_intervals=intervals,
            auscultation_location=location,
            wav_path=str(wav_file.resolve()),
            annotation_path=str(tsv_file.resolve()),
            metadata={
                "doi": CIRCOR_DOI,
                "url": CIRCOR_URL,
            },
        )
        records.append(rec)
        seen_subjects.add(subject_id)

        if max_records is not None and len(records) >= max_records:
            break

    return records
