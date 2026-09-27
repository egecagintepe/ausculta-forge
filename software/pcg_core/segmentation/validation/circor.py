"""AuscultaForge — CirCor DigiScope Dataset Adapter.

Parses and validates the PhysioNet CirCor DigiScope Phonocardiogram Dataset (v1.0.3).
Handles:
- Filename pattern extraction (SUBJECTID_LOCATION.wav / .tsv / .hea)
- Strict TSV segment validation (start, end, state in {0, 1, 2, 3, 4})
- Mandatory companion files (.wav, .tsv, .hea)
- Strict auscultation location verification ({AV, MV, PV, TV, Phc})
- Scan accounting (files_seen, records_eligible, records_excluded, exclusion_reasons)
- Duration alignment checks (with small tolerance)
- Integrity verification against SHA256SUMS.txt when present
- Safe subject ID grouping

Official Provenance:
- Dataset: The CirCor DigiScope Phonocardiogram Dataset
- Version: 1.0.3
- PhysioNet: https://physionet.org/content/circor-heart-sound/1.0.3/
- Official DOI: 10.13026/tshs-mw03
- Subjects: 1568
- Recordings: 5272
- Uncompressed Size: ~558.9 MB
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Optional, Sequence
import wave

from .models import AnnotatedPCGRecord, ReferenceStateInterval

CIRCOR_DATASET_ID = "CIRCOR_DIGISCOPE"
CIRCOR_DATASET_NAME = "The CirCor DigiScope Phonocardiogram Dataset"
CIRCOR_DATASET_VERSION = "1.0.3"
CIRCOR_DOI = "10.13026/tshs-mw03"
CIRCOR_URL = "https://physionet.org/content/circor-heart-sound/1.0.3/"
CIRCOR_TOTAL_SUBJECTS = 1568
CIRCOR_TOTAL_RECORDINGS = 5272
CIRCOR_UNCOMPRESSED_SIZE_MB = 558.9

KNOWN_LOCATIONS = {"AV", "MV", "PV", "TV", "Phc"}


@dataclass(slots=True)
class CirCorScanResult:
    """Detailed accounting of CirCor dataset scan outcomes for reproducibility."""
    records: list[AnnotatedPCGRecord]
    files_seen: int
    records_eligible: int
    records_excluded: int
    exclusion_reasons: dict[str, int] = field(default_factory=dict)

    def __iter__(self):
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> AnnotatedPCGRecord:
        return self.records[idx]

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_seen": self.files_seen,
            "records_eligible": self.records_eligible,
            "records_excluded": self.records_excluded,
            "exclusion_reasons": dict(self.exclusion_reasons),
        }


def parse_circor_filename(stem_or_filename: str) -> tuple[str, str]:
    """Extract numeric subject ID and auscultation location code from CirCor filename stem.

    Examples:
    - '2530_AV' -> ('2530', 'AV')
    - '2530_AV_1.wav' -> ('2530', 'AV')
    - '50782_MV_1' -> ('50782', 'MV')
    - '50782_MV_2' -> ('50782', 'MV')
    - '85340_MV.tsv' -> ('85340', 'MV')
    """
    stem = Path(stem_or_filename).stem
    parts = stem.split("_")
    if not parts or not parts[0].isdigit():
        raise ValueError(f"CirCor filename must begin with a numeric subject ID, got: '{stem_or_filename}'")

    subject_id = parts[0]
    if len(parts) < 2:
        raise ValueError(f"CirCor filename missing location code: '{stem_or_filename}'")
    location = parts[1]

    if location not in KNOWN_LOCATIONS:
        raise ValueError(
            f"Invalid auscultation location '{location}' in '{stem_or_filename}'. "
            f"Must be one of {sorted(KNOWN_LOCATIONS)}."
        )

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
) -> CirCorScanResult:
    """Discover, parse, and validate all eligible CirCor records in a directory.

    Accounting:
    Tracks files_seen, records_eligible, records_excluded, and explicit exclusion_reasons:
    - MISSING_TSV
    - MISSING_HEA
    - INVALID_FILENAME
    - INVALID_LOCATION
    - INVALID_WAV
    - INVALID_TSV
    - CHECKSUM_MISMATCH

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
    CirCorScanResult
        Container with validated records, counts, and exclusion reasons.
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
    files_seen = 0
    records_excluded = 0
    exclusion_reasons: dict[str, int] = {}

    for wav_file in wav_files:
        files_seen += 1
        stem = wav_file.stem

        # 1. Filename & Location Validation
        try:
            subject_id, location = parse_circor_filename(stem)
        except ValueError as e:
            err_msg = str(e)
            if "location" in err_msg.lower():
                exclusion_reasons["INVALID_LOCATION"] = exclusion_reasons.get("INVALID_LOCATION", 0) + 1
            else:
                exclusion_reasons["INVALID_FILENAME"] = exclusion_reasons.get("INVALID_FILENAME", 0) + 1
            records_excluded += 1
            continue

        # 2. Required .hea companion check
        hea_file = wav_file.with_suffix(".hea")
        if not hea_file.is_file():
            exclusion_reasons["MISSING_HEA"] = exclusion_reasons.get("MISSING_HEA", 0) + 1
            records_excluded += 1
            continue

        # 3. Required .tsv companion check
        tsv_file = wav_file.with_suffix(".tsv")
        if not tsv_file.is_file():
            exclusion_reasons["MISSING_TSV"] = exclusion_reasons.get("MISSING_TSV", 0) + 1
            records_excluded += 1
            continue

        # Check subject pilot limit before heavy audio I/O
        if max_subjects is not None and subject_id not in seen_subjects:
            if len(seen_subjects) >= max_subjects:
                continue

        # 4. Verify checksums if available and requested
        if verify_checksums and checksums:
            checksum_mismatch = False
            for f in (wav_file, tsv_file, hea_file):
                if f.name in checksums:
                    if not verify_sha256_checksum(f, checksums[f.name]):
                        checksum_mismatch = True
                        break
            if checksum_mismatch:
                exclusion_reasons["CHECKSUM_MISMATCH"] = exclusion_reasons.get("CHECKSUM_MISMATCH", 0) + 1
                records_excluded += 1
                continue

        # 5. Validate WAV header readability
        try:
            fs, duration_s, _ = read_wav_header_metadata(wav_file)
            if duration_s <= 0.0 or fs <= 0.0:
                raise ValueError("Non-positive duration or sample rate")
        except Exception:
            exclusion_reasons["INVALID_WAV"] = exclusion_reasons.get("INVALID_WAV", 0) + 1
            records_excluded += 1
            continue

        # 6. Validate TSV content and intervals
        try:
            intervals = parse_circor_tsv(tsv_file, wav_duration_s=duration_s)
        except Exception:
            exclusion_reasons["INVALID_TSV"] = exclusion_reasons.get("INVALID_TSV", 0) + 1
            records_excluded += 1
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

    return CirCorScanResult(
        records=records,
        files_seen=files_seen,
        records_eligible=len(records),
        records_excluded=records_excluded,
        exclusion_reasons=exclusion_reasons,
    )
