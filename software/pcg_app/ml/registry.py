"""AuscultaForge Research ML Model Registry.

Provides versioned, auditable registration for current and planned research models.
Guarantees graceful degradation when PyTorch or model artifacts are absent.
Strictly non-clinical research boundaries are declared and enforced.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ModelTaskType(str, Enum):
    MURMUR_DETECTION = "patient_level_murmur_present_vs_absent"
    QUALITY_ASSESSMENT = "recording_quality_assessment"
    ARTEFACT_CLASSIFICATION = "noise_and_artefact_classification"
    FILTER_RECOMMENDATION = "deterministic_filter_advisor"
    PCG_SEGMENTATION = "heart_sound_segmentation"
    DEEP_DENOISING = "acoustic_denoising"
    DOMAIN_ADAPTATION = "transducer_domain_adaptation"


class ModelStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    PLANNED_FUTURE = "PLANNED_FUTURE"
    RULE_BASED_FOUNDATION = "RULE_BASED_FOUNDATION"


@dataclass(frozen=True)
class ModelRegistration:
    model_id: str
    name: str
    version: str
    task: ModelTaskType
    status: ModelStatus
    is_research_only: bool
    description: str
    author: str
    dataset_provenance: str
    supported_inputs: str
    threshold: float | None
    metrics_summary: dict[str, Any] | None
    manifest: dict[str, Any] | None
    artifact_path: str | None
    nonclinical_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["task"] = self.task.value
        data["status"] = self.status.value
        return data


class ResearchModelRegistry:
    """Authoritative registry for AuscultaForge research models."""

    def __init__(self, root_dir: Path | None = None) -> None:
        if root_dir is None:
            # Default to repo root
            root_dir = Path(__file__).parent.parent.parent.parent
        self.root_dir = Path(root_dir)

    def _torch_available(self) -> bool:
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def _locate_artifact_dir(self, version: str) -> Path | None:
        """Find the local directory containing model weights."""
        candidates = [
            self.root_dir / "research" / "ml" / "artifacts" / "circor_mil_v1",
            self.root_dir / "research" / "ml" / "records" / version,
            self.root_dir / "models" / version,
        ]
        for c in candidates:
            if (c / "murmur_mil_cpu.pt").exists() or (c / "weights.pt").exists():
                return c
        # If weights are missing, check if records dir exists with metadata
        rec_dir = self.root_dir / "research" / "ml" / "records" / version
        if rec_dir.exists() and (rec_dir / "manifest.json").exists():
            return rec_dir
        return None

    def get_murmur_mil_registration(self) -> ModelRegistration:
        """Inspect and register af_murmur_mil_1.0."""
        version = "af_murmur_mil_1.0"
        artifact_dir = self._locate_artifact_dir(version)
        has_torch = self._torch_available()

        manifest_data: dict[str, Any] | None = None
        metrics_data: dict[str, Any] | None = None

        if artifact_dir and (artifact_dir / "manifest.json").exists():
            try:
                manifest_data = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
            except Exception:
                pass
        if artifact_dir and (artifact_dir / "metrics.json").exists():
            try:
                metrics_data = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
            except Exception:
                pass

        # Determine status
        weights_exist = False
        if artifact_dir:
            weights_exist = (artifact_dir / "murmur_mil_cpu.pt").exists() or (artifact_dir / "weights.pt").exists()

        if not has_torch:
            status = ModelStatus.DEPENDENCY_MISSING
        elif not weights_exist:
            status = ModelStatus.MISSING_ARTIFACT
        else:
            status = ModelStatus.AVAILABLE

        # Metrics summary
        metrics_summary = None
        if metrics_data and "internal_heldout_test" in metrics_data:
            test_m = metrics_data["internal_heldout_test"]
            metrics_summary = {
                "test_auroc": test_m.get("roc_auc"),
                "test_average_precision": test_m.get("average_precision"),
                "test_f1": test_m.get("f1"),
                "test_balanced_accuracy": test_m.get("balanced_accuracy"),
                "best_epoch": metrics_data.get("best_epoch", 6),
                "threshold": metrics_data.get("validation_threshold", 0.52),
                "dataset": metrics_data.get("dataset"),
            }

        return ModelRegistration(
            model_id="af_murmur_mil_1.0",
            name="MurmurMIL (Attention-Pooled Multi-Instance CNN)",
            version="1.0.0",
            task=ModelTaskType.MURMUR_DETECTION,
            status=status,
            is_research_only=True,
            description=(
                "Patient-level multi-instance acoustic pattern classifier trained on CirCor v1.0.3. "
                "Aggregates 1 to 4 auscultation recordings per subject with learned attention pooling."
            ),
            author="AuscultaForge ML Research Lab (Trained via Google Colab)",
            dataset_provenance="PhysioNet CirCor DigiScope v1.0.3 Public Training Subset (610 train / 132 val / 132 test patients)",
            supported_inputs="1 to 4 PCG WAV recordings from same patient (Aortic, Mitral, Pulmonic, Tricuspid)",
            threshold=0.52,
            metrics_summary=metrics_summary,
            manifest=manifest_data,
            artifact_path=str(artifact_dir) if artifact_dir else None,
            nonclinical_disclaimer=(
                "RESEARCH ONLY — NOT A CLINICAL DIAGNOSTIC DEVICE. "
                "Does not evaluate patient cardiovascular health or diagnose arrhythmia. "
                "Unvalidated on physical stethoscope hardware."
            ),
        )

    def list_models(self) -> list[ModelRegistration]:
        """Return all active and declared future models in the registry."""
        models: list[ModelRegistration] = [
            self.get_murmur_mil_registration(),
            ModelRegistration(
                model_id="af_filter_advisor_v1",
                name="Deterministic PCG Filter Advisor",
                version="1.0.0",
                task=ModelTaskType.FILTER_RECOMMENDATION,
                status=ModelStatus.RULE_BASED_FOUNDATION,
                is_research_only=True,
                description=(
                    "Deterministic, non-destructive DSP filter recommendation foundation. "
                    "Rule-based heuristics for passband and mains notch selection; NOT a trained neural network."
                ),
                author="AuscultaForge DSP Team",
                dataset_provenance="Deterministic spectral energy and SNR heuristics",
                supported_inputs="Single-channel raw PCG waveform",
                threshold=None,
                metrics_summary={"type": "Deterministic mathematical heuristics"},
                manifest={"engine": "scipy.signal", "mode": "rule_based"},
                artifact_path="research/ml/ausculta_ml/filter_advisor.py",
                nonclinical_disclaimer="Non-destructive filter parameter recommendations for scientific auditioning only.",
            ),
            ModelRegistration(
                model_id="af_quality_ai_v1",
                name="Deep Recording Quality & SNR Assessor",
                version="0.1.0-planned",
                task=ModelTaskType.QUALITY_ASSESSMENT,
                status=ModelStatus.PLANNED_FUTURE,
                is_research_only=True,
                description="Planned deep neural network for auscultation signal-to-noise ratio and acoustic clarity grading.",
                author="AuscultaForge ML Roadmap",
                dataset_provenance="Pending curated quality benchmark",
                supported_inputs="Single-channel PCG audio",
                threshold=None,
                metrics_summary=None,
                manifest=None,
                artifact_path=None,
                nonclinical_disclaimer="Research specification only. Not implemented in v1.0.",
            ),
            ModelRegistration(
                model_id="af_artefact_classifier_v1",
                name="Acoustic Artefact & Friction Noise Classifier",
                version="0.1.0-planned",
                task=ModelTaskType.ARTEFACT_CLASSIFICATION,
                status=ModelStatus.PLANNED_FUTURE,
                is_research_only=True,
                description="Planned multi-class detector for chest friction, cable rubs, vocalizations, and bowel sounds.",
                author="AuscultaForge ML Roadmap",
                dataset_provenance="Pending acoustic artefact corpus",
                supported_inputs="Single-channel PCG audio",
                threshold=None,
                metrics_summary=None,
                manifest=None,
                artifact_path=None,
                nonclinical_disclaimer="Research specification only. Not implemented in v1.0.",
            ),
            ModelRegistration(
                model_id="af_pcg_segmentation_v1",
                name="Deep S1/S2/Systole/Diastole Segmenter",
                version="0.1.0-planned",
                task=ModelTaskType.PCG_SEGMENTATION,
                status=ModelStatus.PLANNED_FUTURE,
                is_research_only=True,
                description="Planned deep neural sequence model for cardiac cycle phase segmentation.",
                author="AuscultaForge ML Roadmap",
                dataset_provenance="PhysioNet CinC 2016 / CirCor annotations",
                supported_inputs="Single-channel PCG audio",
                threshold=None,
                metrics_summary=None,
                manifest=None,
                artifact_path=None,
                nonclinical_disclaimer="Research specification only. Classical Springer HSMM is current baseline.",
            ),
            ModelRegistration(
                model_id="af_denoiser_v1",
                name="Deep PCG Waveform Denoising Network",
                version="0.1.0-planned",
                task=ModelTaskType.DEEP_DENOISING,
                status=ModelStatus.PLANNED_FUTURE,
                is_research_only=True,
                description="Planned waveform-to-waveform deep noise suppression without phase distortion.",
                author="AuscultaForge ML Roadmap",
                dataset_provenance="Pending synthetic + environmental noise pairing",
                supported_inputs="Single-channel raw PCG audio",
                threshold=None,
                metrics_summary=None,
                manifest=None,
                artifact_path=None,
                nonclinical_disclaimer="Research specification only. Not implemented in v1.0.",
            ),
            ModelRegistration(
                model_id="af_domain_adapt_v1",
                name="Cross-Microphone Sensor Domain Adapter",
                version="0.1.0-planned",
                task=ModelTaskType.DOMAIN_ADAPTATION,
                status=ModelStatus.PLANNED_FUTURE,
                is_research_only=True,
                description="Planned spectral feature mapping between clinical electronic stethoscopes and ESP32-S3 / INMP441 transducers.",
                author="AuscultaForge ML Roadmap",
                dataset_provenance="Pending paired acoustic phantom chamber corpus",
                supported_inputs="Raw 48 kHz MEMS acoustic stream",
                threshold=None,
                metrics_summary=None,
                manifest=None,
                artifact_path=None,
                nonclinical_disclaimer="Research specification only. Not implemented in v1.0.",
            ),
        ]
        return models

    def get_model(self, model_id: str) -> ModelRegistration | None:
        for m in self.list_models():
            if m.model_id == model_id:
                return m
        return None
