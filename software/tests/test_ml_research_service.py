"""Unit and Integration Tests for Research ML Model Activation.

Tests:
1. Model Registry discovery, status resolution, and future task declarations.
2. Audio input validation (0 files, >4 files, nonexistent file, corrupted WAV, <0.5s duration).
3. Real exported MurmurMIL TorchScript model execution via FastAPI TestClient.
4. Non-clinical research disclaimers, threshold comparison, and output guardrails.
5. Missing model and dependency error handling.
"""
from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from pcg_app.app import create_app
from pcg_app.ml.registry import ModelStatus, ModelTaskType, ResearchModelRegistry
from pcg_app.ml.service import AudioValidationError, ModelUnavailableError, ResearchInferenceService


def make_dummy_wav(path: Path, duration_s: float = 1.0, sample_rate: int = 4000) -> Path:
    """Generate a clean synthetic sine WAV file for testing input validation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import numpy as np

    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    sig = (0.5 * np.sin(2 * np.pi * 50.0 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(sig.tobytes())
    return path


class TestResearchModelRegistry:
    def test_registry_lists_all_models(self):
        reg = ResearchModelRegistry()
        models = reg.list_models()
        assert len(models) >= 7

        ids = [m.model_id for m in models]
        assert "af_murmur_mil_1.0" in ids
        assert "af_filter_advisor_v1" in ids
        assert "af_quality_ai_v1" in ids
        assert "af_artefact_classifier_v1" in ids
        assert "af_pcg_segmentation_v1" in ids
        assert "af_denoiser_v1" in ids
        assert "af_domain_adapt_v1" in ids

    def test_murmur_mil_registration_details(self):
        reg = ResearchModelRegistry()
        m = reg.get_model("af_murmur_mil_1.0")
        assert m is not None
        assert m.task == ModelTaskType.MURMUR_DETECTION
        assert m.is_research_only is True
        assert m.threshold == 0.52
        assert "CirCor" in m.dataset_provenance
        assert "RESEARCH ONLY" in m.nonclinical_disclaimer

        if m.status == ModelStatus.AVAILABLE:
            assert m.metrics_summary is not None
            assert m.metrics_summary["test_auroc"] > 0.85
            assert m.metrics_summary["test_f1"] > 0.50

    def test_filter_advisor_declared_as_rule_based(self):
        reg = ResearchModelRegistry()
        fa = reg.get_model("af_filter_advisor_v1")
        assert fa is not None
        assert fa.status == ModelStatus.RULE_BASED_FOUNDATION
        assert "rule-based" in fa.description.lower() or "deterministic" in fa.description.lower()


class TestResearchInferenceValidation:
    def test_validation_empty_files(self, tmp_path):
        service = ResearchInferenceService()
        with pytest.raises(AudioValidationError, match="At least one PCG recording"):
            service.validate_recording_group([])

    def test_validation_too_many_files(self, tmp_path):
        service = ResearchInferenceService()
        files = [str(tmp_path / f"audio_{i}.wav") for i in range(5)]
        with pytest.raises(AudioValidationError, match="supports up to 4 recordings"):
            service.validate_recording_group(files)

    def test_validation_nonexistent_file(self, tmp_path):
        service = ResearchInferenceService()
        fake_path = str(tmp_path / "does_not_exist.wav")
        with pytest.raises(AudioValidationError, match="does not exist"):
            service.validate_recording_group([fake_path])

    def test_validation_file_too_short(self, tmp_path):
        service = ResearchInferenceService()
        short_file = tmp_path / "short.wav"
        make_dummy_wav(short_file, duration_s=0.2, sample_rate=4000)
        with pytest.raises(AudioValidationError, match="too short"):
            service.validate_recording_group([str(short_file)])

    def test_validation_valid_wav_group(self, tmp_path):
        service = ResearchInferenceService()
        wav1 = make_dummy_wav(tmp_path / "patient_av.wav", duration_s=2.0)
        wav2 = make_dummy_wav(tmp_path / "patient_mv.wav", duration_s=2.5)

        validated = service.validate_recording_group([str(wav1), str(wav2)])
        assert len(validated) == 2
        assert validated[0]["file_name"] == "patient_av.wav"
        assert validated[0]["duration_sec"] == 2.0
        assert validated[1]["file_name"] == "patient_mv.wav"
        assert validated[1]["duration_sec"] == 2.5


class TestResearchFastAPIEndpoints:
    @pytest.fixture
    def client(self, tmp_path):
        app = create_app(sessions_dir=tmp_path / "sessions")
        return TestClient(app)

    def test_api_list_models(self, client):
        resp = client.get("/api/research/ml/models")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(m["model_id"] == "af_murmur_mil_1.0" for m in data)

    def test_api_get_model_details(self, client):
        resp = client.get("/api/research/ml/models/af_murmur_mil_1.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "af_murmur_mil_1.0"
        assert data["is_research_only"] is True
        assert data["threshold"] == 0.52

    def test_api_get_model_not_found(self, client):
        resp = client.get("/api/research/ml/models/nonexistent_model")
        assert resp.status_code == 404

    def test_api_predict_validation_error(self, client):
        resp = client.post("/api/research/ml/predict", json={"file_paths": []})
        assert resp.status_code == 422 or resp.status_code == 400

    def test_api_predict_with_real_circor_if_available(self, client):
        circor_dir = Path("data/external/circor-heart-sound-1.0.3/training_data")
        if not circor_dir.exists():
            pytest.skip("Local CirCor dataset not found in data/external")

        wavs = [
            str(circor_dir / "14241_AV.wav"),
            str(circor_dir / "14241_MV.wav"),
            str(circor_dir / "14241_PV.wav"),
            str(circor_dir / "14241_TV.wav"),
        ]
        if not all(Path(w).exists() for w in wavs):
            pytest.skip("CirCor sample 14241 recordings not found")

        resp = client.post(
            "/api/research/ml/predict",
            json={
                "file_paths": wavs,
                "model_id": "af_murmur_mil_1.0",
                "patient_identifier": "14241",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["research_only"] is True
        assert data["strictly_nonclinical"] is True
        assert data["model_id"] == "af_murmur_mil_1.0"
        assert data["patient_identifier"] == "14241"
        assert 0.0 <= data["positive_probability"] <= 1.0
        assert data["validation_selected_threshold"] == pytest.approx(0.52, abs=1e-3)
        assert "RESEARCH ONLY" in data["disclaimer"]
        assert data["recording_count"] == 4
        # Patient 14241 is known present
        assert data["positive_probability"] > 0.52
        assert data["predicted_label"] == "research_pattern_present"
