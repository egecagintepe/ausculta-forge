"""AuscultaForge Research ML Inference Service.

Orchestrates multi-recording patient-level inference safely off the asyncio event loop.
Validates input WAV constraints, prevents capture blocking, and attaches nonclinical disclosures.
"""
from __future__ import annotations

import asyncio
import os
import wave
from pathlib import Path
from typing import Any

from .registry import ModelStatus, ResearchModelRegistry


class AudioValidationError(ValueError):
    """Raised when an input audio file violates the inference contract."""
    pass


class ModelUnavailableError(RuntimeError):
    """Raised when an inference is requested on an unavailable or uninstalled model."""
    pass


class ResearchInferenceService:
    """Production backend service for executing research-only machine learning inference."""

    def __init__(self, registry: ResearchModelRegistry | None = None) -> None:
        self.registry = registry or ResearchModelRegistry()

    def validate_recording_group(self, file_paths: list[str]) -> list[dict[str, Any]]:
        """Validate 1 to 4 WAV recordings belonging to one subject."""
        if not file_paths:
            raise AudioValidationError("At least one PCG recording must be provided for patient-level evaluation.")
        if len(file_paths) > 4:
            raise AudioValidationError(
                f"MurmurMIL supports up to 4 recordings per patient group (received {len(file_paths)}). "
                "Select up to 4 auscultation sites (e.g. AV, MV, PV, TV)."
            )

        validated: list[dict[str, Any]] = []
        for path_str in file_paths:
            path = Path(path_str)
            if not path.is_file():
                raise AudioValidationError(f"Audio file does not exist or is not a regular file: {path_str}")

            if path.stat().st_size < 100:
                raise AudioValidationError(f"Audio file is empty or corrupted: {path_str}")

            # Inspect WAV header
            try:
                with wave.open(str(path), "rb") as wf:
                    channels = wf.getnchannels()
                    framerate = wf.getframerate()
                    nframes = wf.getnframes()
                    sampwidth = wf.getsampwidth()
                    duration_sec = nframes / float(framerate) if framerate > 0 else 0.0

                    if duration_sec < 0.5:
                        raise AudioValidationError(
                            f"Recording {path.name} is too short ({duration_sec:.2f}s). "
                            "Minimum duration for acoustic STFT inference is 0.5s."
                        )

                    validated.append({
                        "file_path": str(path.resolve()),
                        "file_name": path.name,
                        "channels": channels,
                        "sample_rate_hz": framerate,
                        "duration_sec": round(duration_sec, 3),
                        "sample_width_bytes": sampwidth,
                    })
            except wave.Error as we:
                raise AudioValidationError(f"File {path.name} is not a valid RIFF/WAV format: {we}")

        return validated

    def _sync_predict_murmur_mil(self, artifact_dir: Path, valid_paths: list[str]) -> dict[str, Any]:
        """Synchronous inference worker executed inside threadpool."""
        # Import dynamically so service loads even if torch isn't immediately ready
        try:
            import sys
            ml_pkg_dir = self.registry.root_dir / "research" / "ml"
            if str(ml_pkg_dir) not in sys.path:
                sys.path.insert(0, str(ml_pkg_dir))
            from ausculta_ml.inference import predict_recordings
        except ImportError as e:
            raise ModelUnavailableError(f"ML dependencies missing: {e}")

        return predict_recordings(artifact_dir, valid_paths)

    async def run_patient_murmur_inference(
        self,
        file_paths: list[str],
        model_id: str = "af_murmur_mil_1.0",
        patient_identifier: str | None = None,
    ) -> dict[str, Any]:
        """Execute patient-level murmur prediction asynchronously without blocking the event loop."""
        reg = self.registry.get_model(model_id)
        if not reg:
            raise ModelUnavailableError(f"Model ID '{model_id}' is not recognized in the registry.")

        if reg.status != ModelStatus.AVAILABLE:
            raise ModelUnavailableError(
                f"Model '{model_id}' is not ready for inference (Status: {reg.status.value}). "
                "Ensure PyTorch is installed and model artifact is present."
            )

        if not reg.artifact_path or not Path(reg.artifact_path).exists():
            raise ModelUnavailableError(f"Artifact directory for model '{model_id}' not found.")

        # 1. Validate inputs
        validated_recordings = self.validate_recording_group(file_paths)
        resolved_paths = [r["file_path"] for r in validated_recordings]

        # 2. Run inference in worker thread
        artifact_dir = Path(reg.artifact_path)
        raw_result = await asyncio.to_thread(self._sync_predict_murmur_mil, artifact_dir, resolved_paths)

        # 3. Structure response with scientific disclaimers
        prob = raw_result.get("positive_probability", 0.0)
        threshold = raw_result.get("validation_selected_threshold", 0.52)
        predicted_label = raw_result.get("predicted_label", "research_pattern_absent")

        return {
            "research_only": True,
            "strictly_nonclinical": True,
            "model_id": model_id,
            "model_version": reg.version,
            "task": reg.task.value,
            "patient_identifier": patient_identifier or (Path(file_paths[0]).stem.split("_")[0] if file_paths else "Unknown"),
            "positive_probability": float(prob),
            "validation_selected_threshold": float(threshold),
            "predicted_label": predicted_label,
            "recordings_evaluated": validated_recordings,
            "recording_count": len(validated_recordings),
            "dataset_provenance": reg.dataset_provenance,
            "disclaimer": (
                "RESEARCH ONLY — NOT A CLINICAL DIAGNOSTIC DEVICE. "
                "Output represents an experimental acoustic pattern probability score. "
                "Not validated for patient diagnosis, arrhythmia detection, or physical hardware triage."
            ),
            "warning": raw_result.get("warning", "Domain-shifted hardware recordings require external validation."),
        }
