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
    CORRUPTED_ARTIFACT = "CORRUPTED_ARTIFACT"
    PLANNED_FUTURE = "PLANNED_FUTURE"
    RULE_BASED_FOUNDATION = "RULE_BASED_FOUNDATION"


EXPECTED_MURMUR_MIL_CHECKSUMS: dict[str, str] = {
    "murmur_mil_cpu.pt": "60ee906eb204c5c5bc94d0285e0f6b25f7d2c9532b6394939d902813a86a49e0",
    "weights.pt": "63728ddc49dc24399fc4c523ced67d3cf7aeb8046bca8a742a68f64609256280",
    "manifest.json": "efb961e529cba6df4825860d8e375ac3d0c49569cdc699e1f246c4aee602e1ea",
    "metrics.json": "7c788a5fef982eead586e3de44c16c2216481b45eb94100becccfadf8c245a30",
    "training_config.yaml": "a764ed5583c240c92cdf0c4e23d1bbe03c66f9ae438312ba5c462189373fb78d",
}


def compute_file_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
            # Check environment variable first
            import os
            env_root = os.environ.get("AUSCULTAFORGE_REPO_ROOT") or os.environ.get("AUSCULTAFORGE_RESEARCH_DIR")
            if env_root and Path(env_root).exists():
                root_dir = Path(env_root)
            else:
                # Default to repo root relative to this file
                root_dir = Path(__file__).parent.parent.parent.parent
        self.root_dir = Path(root_dir)
        self._verification_cache: dict[str, tuple[float, ModelStatus]] = {}

    def _torch_available(self) -> bool:
        try:
            import torch  # noqa: F401
            return True
        except (ImportError, Exception):
            return False

    def _locate_artifact_dir(self, version: str) -> Path | None:
        """Find the local directory containing model weights with packaged desktop heuristics."""
        import os
        import sys

        candidates: list[Path] = []

        # 1. Explicit environment override
        env_model_dir = os.environ.get("AUSCULTAFORGE_MODEL_DIR")
        if env_model_dir:
            candidates.append(Path(env_model_dir))
            candidates.append(Path(env_model_dir) / version)

        # 2. PyInstaller bundle extraction dir (_MEIPASS)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "research" / "ml" / "artifacts" / "circor_mil_v1")
            candidates.append(Path(meipass) / "research" / "ml" / "records" / version)
            candidates.append(Path(meipass) / "models" / version)

        # 3. Standard repository paths
        candidates.extend([
            self.root_dir / "research" / "ml" / "artifacts" / "circor_mil_v1",
            self.root_dir / "research" / "ml" / "records" / version,
            self.root_dir / "models" / version,
        ])

        # 4. Executable parent directory (when packaged)
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "models" / version)
        candidates.append(exe_dir / "research" / "ml" / "records" / version)

        for c in candidates:
            if c.exists() and ((c / "murmur_mil_cpu.pt").exists() or (c / "weights.pt").exists()):
                return c

        # If weights are missing, check if records dir exists with metadata
        for c in candidates:
            if c.exists() and (c / "manifest.json").exists():
                return c

        return None

    def _verify_artifact_integrity(self, artifact_dir: Path) -> ModelStatus:
        """Verify presence of required files, manifest version, and SHA-256 hashes."""
        # Required files for full operation
        ts_path = artifact_dir / "murmur_mil_cpu.pt"
        manifest_path = artifact_dir / "manifest.json"

        if not ts_path.exists() or not manifest_path.exists():
            return ModelStatus.MISSING_ARTIFACT

        # Cache check using mtime
        cache_key = str(artifact_dir)
        mtime = ts_path.stat().st_mtime
        if cache_key in self._verification_cache:
            cached_mtime, cached_status = self._verification_cache[cache_key]
            if cached_mtime == mtime:
                return cached_status

        # 1. Verify manifest version
        try:
            m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if m_data.get("model_version") != "af_murmur_mil_1.0":
                self._verification_cache[cache_key] = (mtime, ModelStatus.CORRUPTED_ARTIFACT)
                return ModelStatus.CORRUPTED_ARTIFACT
        except Exception:
            self._verification_cache[cache_key] = (mtime, ModelStatus.CORRUPTED_ARTIFACT)
            return ModelStatus.CORRUPTED_ARTIFACT

        # 2. Verify TorchScript file hash
        ts_hash = compute_file_sha256(ts_path)
        if ts_hash != EXPECTED_MURMUR_MIL_CHECKSUMS["murmur_mil_cpu.pt"]:
            self._verification_cache[cache_key] = (mtime, ModelStatus.CORRUPTED_ARTIFACT)
            return ModelStatus.CORRUPTED_ARTIFACT

        # 3. Verify manifest hash
        manifest_hash = compute_file_sha256(manifest_path)
        if manifest_hash != EXPECTED_MURMUR_MIL_CHECKSUMS["manifest.json"]:
            self._verification_cache[cache_key] = (mtime, ModelStatus.CORRUPTED_ARTIFACT)
            return ModelStatus.CORRUPTED_ARTIFACT

        # 4. If weights.pt is present, verify its hash
        weights_path = artifact_dir / "weights.pt"
        if weights_path.exists():
            weights_hash = compute_file_sha256(weights_path)
            if weights_hash != EXPECTED_MURMUR_MIL_CHECKSUMS["weights.pt"]:
                self._verification_cache[cache_key] = (mtime, ModelStatus.CORRUPTED_ARTIFACT)
                return ModelStatus.CORRUPTED_ARTIFACT

        self._verification_cache[cache_key] = (mtime, ModelStatus.AVAILABLE)
        return ModelStatus.AVAILABLE

    def get_murmur_mil_registration(self) -> ModelRegistration:
        """Inspect and register af_murmur_mil_1.0 with strict fail-closed verification."""
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

        # Determine status with fail-closed integrity checks
        if not has_torch:
            status = ModelStatus.DEPENDENCY_MISSING
        elif not artifact_dir:
            status = ModelStatus.MISSING_ARTIFACT
        else:
            status = self._verify_artifact_integrity(artifact_dir)

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
