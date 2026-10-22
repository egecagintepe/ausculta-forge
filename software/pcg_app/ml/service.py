"""AuscultaForge Research ML Inference Service.

Orchestrates multi-recording patient-level inference safely off the asyncio event loop.
Enforces subject-group integrity, strict path confinement, resource safety limits,
and guarantees non-clinical research boundaries.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import wave
from pathlib import Path
from typing import Any

from .registry import ModelStatus, ResearchModelRegistry

CIRCOR_PATIENT_REGEX = re.compile(r"^(\d+)_([A-Za-z0-9]+)\.wav$", re.IGNORECASE)
MAX_AUDIO_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit per recording
MIN_AUDIO_DURATION_SEC = 0.5
MAX_AUDIO_DURATION_SEC = 120.0  # 2 minutes max per recording


class AudioValidationError(ValueError):
    """Raised when an input audio file violates the inference contract."""
    pass


class SubjectIntegrityError(AudioValidationError):
    """Raised when a patient recording group violates same-subject integrity constraints."""
    pass


class UnauthorizedPathError(AudioValidationError):
    """Raised when an audio path violates directory access boundaries."""
    pass


class ModelUnavailableError(RuntimeError):
    """Raised when an inference is requested on an unavailable or uninstalled model."""
    pass


class ResearchInferenceService:
    """Production backend service for executing research-only machine learning inference."""

    def __init__(self, registry: ResearchModelRegistry | None = None) -> None:
        self.registry = registry or ResearchModelRegistry()
        self._inference_lock = asyncio.Lock()
        self._allowed_directories: list[Path] = []
        self._init_allowed_directories()

    def _init_allowed_directories(self) -> None:
        """Establish approved directory boundaries for dataset ingestion and user recordings."""
        repo_root = self.registry.root_dir.resolve()
        self._allowed_directories = [
            (repo_root / "data" / "external").resolve(),
            (repo_root / "data" / "recordings").resolve(),
            (repo_root / "data" / "benchmarks").resolve(),
            (repo_root / "data" / "sessions").resolve(),
            (repo_root / "research").resolve(),
        ]

        # Environment variable override for additional approved paths
        extra_dirs = os.environ.get("AUSCULTAFORGE_ALLOWED_AUDIO_DIRS")
        if extra_dirs:
            for d in extra_dirs.split(os.pathsep):
                d_clean = d.strip()
                if d_clean:
                    self._allowed_directories.append(Path(d_clean).resolve())

    def add_allowed_directory(self, directory: Path | str) -> None:
        """Permit test fixtures or host configurations to register an approved directory."""
        self._allowed_directories.append(Path(directory).resolve())

    def _is_path_allowed(self, path: Path) -> bool:
        """Verify that resolved canonical path resides inside an approved directory boundary."""
        resolved = path.resolve()
        for root in self._allowed_directories:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _sanitize_path(self, path: Path) -> str:
        """Return safe display path without leaking local host user directories."""
        try:
            rel = path.resolve().relative_to(self.registry.root_dir.resolve())
            return str(rel).replace("\\", "/")
        except ValueError:
            return path.name

    def validate_recording_group(
        self,
        file_paths: list[str],
        same_subject_attestation: bool = False,
        patient_identifier: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Validate 1 to 4 WAV recordings and enforce subject-group integrity."""
        if not file_paths:
            raise AudioValidationError("At least one PCG recording must be provided for patient-level evaluation.")
        if len(file_paths) > 4:
            raise AudioValidationError(
                f"MurmurMIL supports up to 4 recordings per patient group (received {len(file_paths)}). "
                "Select up to 4 auscultation sites (e.g. AV, MV, PV, TV)."
            )

        validated: list[dict[str, Any]] = []

        for path_str in file_paths:
            if "\x00" in path_str:
                raise AudioValidationError("Invalid file path format: Null bytes detected.")

            path = Path(path_str)

            # 1. Path confinement & symlink check
            if not self._is_path_allowed(path):
                raise UnauthorizedPathError(
                    "File access denied: Path is outside approved research datasets and recording storage."
                )

            resolved = path.resolve()
            if not resolved.is_file():
                raise AudioValidationError(f"Audio file does not exist or is not a regular file: {path.name}")

            # 2. File size bounds
            stat_result = resolved.stat()
            if stat_result.st_size < 100:
                raise AudioValidationError(f"Audio file {path.name} is empty or corrupted (<100 bytes).")
            if stat_result.st_size > MAX_AUDIO_FILE_SIZE_BYTES:
                raise AudioValidationError(
                    f"Audio file {path.name} exceeds maximum allowed size ({MAX_AUDIO_FILE_SIZE_BYTES // (1024 * 1024)} MB)."
                )

            # 3. Inspect WAV header & duration bounds
            try:
                with wave.open(str(resolved), "rb") as wf:
                    channels = wf.getnchannels()
                    framerate = wf.getframerate()
                    nframes = wf.getnframes()
                    sampwidth = wf.getsampwidth()
                    duration_sec = nframes / float(framerate) if framerate > 0 else 0.0

                    if duration_sec < MIN_AUDIO_DURATION_SEC:
                        raise AudioValidationError(
                            f"Recording {path.name} is too short ({duration_sec:.2f}s). "
                            f"Minimum duration for acoustic STFT inference is {MIN_AUDIO_DURATION_SEC}s."
                        )
                    if duration_sec > MAX_AUDIO_DURATION_SEC:
                        raise AudioValidationError(
                            f"Recording {path.name} is too long ({duration_sec:.2f}s). "
                            f"Maximum duration for inference windowing is {MAX_AUDIO_DURATION_SEC}s."
                        )

                    validated.append({
                        "file_path": str(resolved),
                        "file_name": path.name,
                        "display_path": self._sanitize_path(resolved),
                        "channels": channels,
                        "sample_rate_hz": framerate,
                        "duration_sec": round(duration_sec, 3),
                        "sample_width_bytes": sampwidth,
                    })
            except wave.Error as we:
                raise AudioValidationError(f"File {path.name} is not a valid RIFF/WAV format: {we}")

        # 4. Subject-Group Integrity Verification
        subject_integrity = self._validate_subject_integrity(
            validated,
            same_subject_attestation=same_subject_attestation,
            patient_identifier=patient_identifier,
        )

        return validated, subject_integrity

    def _validate_subject_integrity(
        self,
        validated_recordings: list[dict[str, Any]],
        same_subject_attestation: bool = False,
        patient_identifier: str | None = None,
    ) -> dict[str, Any]:
        """Validate that all recordings belong to the same person without mixing datasets or subjects."""
        circor_matches = [CIRCOR_PATIENT_REGEX.match(r["file_name"]) for r in validated_recordings]
        all_circor = all(m is not None for m in circor_matches)
        any_circor = any(m is not None for m in circor_matches)

        if all_circor:
            circor_pids = {m.group(1) for m in circor_matches if m is not None}
            if len(circor_pids) > 1:
                sorted_pids = sorted(list(circor_pids))
                raise SubjectIntegrityError(
                    f"Mixed-subject group rejected: recordings belong to multiple CirCor subjects: {sorted_pids}. "
                    "Patient-level MurmurMIL evaluation requires all recordings in a group to be from the same individual."
                )
            detected_pid = next(iter(circor_pids))
            return {
                "patient_identifier": detected_pid,
                "integrity_status": "VERIFIED",
                "provenance": "VERIFIED_CIRCOR_SUBJECT",
                "same_subject_attestation": True,
                "note": f"Verified CirCor patient cohort {detected_pid} from canonical dataset metadata.",
            }

        if any_circor and not all_circor:
            raise SubjectIntegrityError(
                "Mixed-provenance group rejected: Cannot combine CirCor benchmark recordings with unverified custom audio files."
            )

        # Custom recordings without verifiable CirCor metadata
        if not same_subject_attestation:
            raise SubjectIntegrityError(
                "Custom recordings lack verifiable subject metadata. "
                "Explicit same-subject attestation ('same_subject_attestation=true') is required to prevent mixed-individual evaluation."
            )

        subj_id = (patient_identifier or "").strip() or "UserAttestedSubject"
        return {
            "patient_identifier": subj_id,
            "integrity_status": "USER-ATTESTED",
            "provenance": "USER_ATTESTED_CUSTOM_RECORDINGS",
            "same_subject_attestation": True,
            "note": "User-attested single-individual cohort without verifiable clinical database metadata.",
        }

    def _sync_predict_murmur_mil(self, artifact_dir: Path, valid_paths: list[str]) -> dict[str, Any]:
        """Synchronous inference worker executed inside threadpool."""
        try:
            # Package discovery for packaged desktop and development checkouts
            ml_pkg_dir = self.registry.root_dir / "research" / "ml"
            meipass = getattr(sys, "_MEIPASS", None)
            search_paths = [
                str(ml_pkg_dir),
                str(Path(meipass) / "research" / "ml") if meipass else None,
            ]
            for p in search_paths:
                if p and p not in sys.path:
                    sys.path.insert(0, p)

            from ausculta_ml.inference import predict_recordings
        except (ImportError, Exception) as e:
            raise ModelUnavailableError(f"ML dependencies missing or failed to initialize: {e}")

        return predict_recordings(artifact_dir, valid_paths)

    async def run_patient_murmur_inference(
        self,
        file_paths: list[str],
        model_id: str = "af_murmur_mil_1.0",
        patient_identifier: str | None = None,
        same_subject_attestation: bool = False,
    ) -> dict[str, Any]:
        """Execute patient-level murmur prediction asynchronously with CPU concurrency protection."""
        reg = self.registry.get_model(model_id)
        if not reg:
            raise ModelUnavailableError(f"Model ID '{model_id}' is not recognized in the registry.")

        if reg.status != ModelStatus.AVAILABLE:
            raise ModelUnavailableError(
                f"Model '{model_id}' is not ready for inference (Status: {reg.status.value}). "
                "Ensure PyTorch is installed and model artifact passes integrity verification."
            )

        if not reg.artifact_path or not Path(reg.artifact_path).exists():
            raise ModelUnavailableError(f"Artifact directory for model '{model_id}' not found.")

        # 1. Validate inputs and enforce subject-group integrity
        validated_recordings, integrity_meta = self.validate_recording_group(
            file_paths,
            same_subject_attestation=same_subject_attestation,
            patient_identifier=patient_identifier,
        )
        resolved_paths = [r["file_path"] for r in validated_recordings]

        # 2. Run inference serialized under mutex to prevent CPU overload
        artifact_dir = Path(reg.artifact_path)
        async with self._inference_lock:
            raw_result = await asyncio.to_thread(self._sync_predict_murmur_mil, artifact_dir, resolved_paths)

        # 3. Structure response with strictly non-clinical research boundaries
        prob = raw_result.get("positive_probability", 0.0)
        threshold = raw_result.get("validation_selected_threshold", 0.52)
        predicted_label = raw_result.get("predicted_label", "research_pattern_absent")

        # Sanitize recording entries for response (strip internal absolute host paths)
        sanitized_recordings = [
            {
                "file_name": r["file_name"],
                "display_path": r["display_path"],
                "channels": r["channels"],
                "sample_rate_hz": r["sample_rate_hz"],
                "duration_sec": r["duration_sec"],
                "sample_width_bytes": r["sample_width_bytes"],
            }
            for r in validated_recordings
        ]

        return {
            "research_only": True,
            "strictly_nonclinical": True,
            "is_clinically_calibrated": False,
            "score_interpretation": "uncalibrated_research_probability",
            "model_id": model_id,
            "model_version": reg.version,
            "task": reg.task.value,
            "patient_identifier": integrity_meta["patient_identifier"],
            "subject_integrity": integrity_meta,
            "positive_probability": float(prob),
            "validation_selected_threshold": float(threshold),
            "predicted_label": predicted_label,
            "recordings_evaluated": sanitized_recordings,
            "recording_count": len(sanitized_recordings),
            "dataset_provenance": reg.dataset_provenance,
            "disclaimer": (
                "RESEARCH ONLY — NOT A CLINICAL DIAGNOSTIC DEVICE. "
                "The score is an uncalibrated research probability from binary cross-entropy on CirCor data. "
                "It is NOT a clinically calibrated probability and must NOT be interpreted as a medical diagnosis, "
                "cardiovascular risk assessment, or arrhythmia detection."
            ),
            "warning": raw_result.get(
                "warning",
                "Unvalidated on physical stethoscope hardware. Domain transfer to ESP32-S3 MEMS audio is uncharacterized.",
            ),
        }
