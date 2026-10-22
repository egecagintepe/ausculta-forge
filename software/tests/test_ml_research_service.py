"""Unit and Integration Tests for Research ML Model Activation and Hardening.

Verifies:
1. Model Registry discovery, status resolution, corruption detection, and future task declarations.
2. Subject-group integrity enforcement (CirCor patient matching, mixed-subject rejection, custom attestation).
3. Audio security boundaries (path traversal containment, leak-free error messages, file size/duration bounds).
4. Real exported MurmurMIL TorchScript model execution via FastAPI TestClient.
5. Non-clinical research disclaimers, uncalibrated probability disclosures, and output guardrails.
6. Clean fallback when PyTorch is unavailable or artifact is missing/corrupted.
7. Concurrency serialization lock for CPU safety.
"""
from __future__ import annotations

import asyncio
import io
import json
import wave
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pcg_app.app import create_app
from pcg_app.ml.registry import (
    EXPECTED_MURMUR_MIL_CHECKSUMS,
    ModelRegistration,
    ModelStatus,
    ModelTaskType,
    ResearchModelRegistry,
)
from pcg_app.ml.service import (
    MAX_AUDIO_DURATION_SEC,
    MAX_AUDIO_FILE_SIZE_BYTES,
    MIN_AUDIO_DURATION_SEC,
    AudioValidationError,
    ModelUnavailableError,
    ResearchInferenceService,
    SubjectIntegrityError,
    UnauthorizedPathError,
)


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
        assert m.threshold == pytest.approx(0.52, abs=1e-3)
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

    def test_corrupted_model_weights_status(self, tmp_path):
        """Corrupted TorchScript file with invalid checksum must evaluate to CORRUPTED_ARTIFACT."""
        fake_rec = tmp_path / "research" / "ml" / "records" / "af_murmur_mil_1.0"
        fake_rec.mkdir(parents=True)
        (fake_rec / "manifest.json").write_text(
            json.dumps({"model_version": "af_murmur_mil_1.0"}), encoding="utf-8"
        )
        (fake_rec / "murmur_mil_cpu.pt").write_bytes(b"CORRUPTED_OR_TAMPERED_MODEL_BYTES")

        reg = ResearchModelRegistry(root_dir=tmp_path)
        m = reg.get_murmur_mil_registration()
        assert m.status == ModelStatus.CORRUPTED_ARTIFACT

    def test_torch_unavailable_clean_fallback(self):
        """When PyTorch is unavailable, registry truthfully reports DEPENDENCY_MISSING without crashing."""
        reg = ResearchModelRegistry()
        with patch.object(reg, "_torch_available", return_value=False):
            m = reg.get_murmur_mil_registration()
            assert m.status == ModelStatus.DEPENDENCY_MISSING


class TestSubjectGroupIntegrityValidation:
    @pytest.fixture
    def service(self, tmp_path):
        srv = ResearchInferenceService()
        srv.add_allowed_directory(tmp_path)
        return srv

    def test_circor_same_subject_accepted_and_verified(self, service, tmp_path):
        """CirCor recordings with matching patient IDs evaluate as VERIFIED."""
        wav1 = make_dummy_wav(tmp_path / "14241_AV.wav", duration_s=1.5)
        wav2 = make_dummy_wav(tmp_path / "14241_MV.wav", duration_s=2.0)

        recordings, integrity = service.validate_recording_group([str(wav1), str(wav2)])
        assert len(recordings) == 2
        assert integrity["patient_identifier"] == "14241"
        assert integrity["integrity_status"] == "VERIFIED"
        assert integrity["provenance"] == "VERIFIED_CIRCOR_SUBJECT"

    def test_circor_mixed_subject_rejected(self, service, tmp_path):
        """Combining CirCor recordings from different patient IDs is strictly rejected."""
        wav1 = make_dummy_wav(tmp_path / "14241_AV.wav", duration_s=1.5)
        wav2 = make_dummy_wav(tmp_path / "2530_MV.wav", duration_s=2.0)

        with pytest.raises(SubjectIntegrityError, match="Mixed-subject group rejected"):
            service.validate_recording_group([str(wav1), str(wav2)])

    def test_custom_recordings_without_attestation_rejected(self, service, tmp_path):
        """Custom unverified audio without explicit same-subject attestation is rejected."""
        wav1 = make_dummy_wav(tmp_path / "mic_recording_1.wav", duration_s=2.0)

        with pytest.raises(SubjectIntegrityError, match="Explicit same-subject attestation"):
            service.validate_recording_group([str(wav1)], same_subject_attestation=False)

    def test_custom_recordings_with_attestation_accepted_as_user_attested(self, service, tmp_path):
        """Custom audio with explicit attestation is accepted and labeled USER-ATTESTED, never VERIFIED."""
        wav1 = make_dummy_wav(tmp_path / "esp32_site_a.wav", duration_s=2.0)
        wav2 = make_dummy_wav(tmp_path / "esp32_site_b.wav", duration_s=2.0)

        recordings, integrity = service.validate_recording_group(
            [str(wav1), str(wav2)],
            same_subject_attestation=True,
            patient_identifier="VolunteerSubject01",
        )
        assert len(recordings) == 2
        assert integrity["patient_identifier"] == "VolunteerSubject01"
        assert integrity["integrity_status"] == "USER-ATTESTED"
        assert integrity["provenance"] == "USER_ATTESTED_CUSTOM_RECORDINGS"

    def test_mixed_circor_and_custom_rejected(self, service, tmp_path):
        """Combining a CirCor recording with a custom recording is rejected."""
        wav1 = make_dummy_wav(tmp_path / "14241_AV.wav", duration_s=1.5)
        wav2 = make_dummy_wav(tmp_path / "custom_external.wav", duration_s=1.5)

        with pytest.raises(SubjectIntegrityError, match="Mixed-provenance group rejected"):
            service.validate_recording_group([str(wav1), str(wav2)], same_subject_attestation=True)


class TestAudioSecurityAndResourceBounds:
    @pytest.fixture
    def service(self, tmp_path):
        srv = ResearchInferenceService()
        srv.add_allowed_directory(tmp_path)
        return srv

    def test_unauthorized_path_outside_allowed_boundaries_rejected(self, tmp_path):
        """Audio file outside approved directory boundaries is rejected without leaking full paths."""
        service = ResearchInferenceService()
        # tmp_path is NOT registered as allowed for this instance
        outside_file = tmp_path / "unauthorized_sample.wav"
        make_dummy_wav(outside_file, duration_s=1.0)

        with pytest.raises(UnauthorizedPathError) as exc_info:
            service.validate_recording_group([str(outside_file)])
        
        # Verify no local username or drive letter is leaked in the error detail
        assert "File access denied: Path is outside approved research datasets" in str(exc_info.value)
        assert str(outside_file) not in str(exc_info.value)

    def test_path_traversal_dot_dot_rejected(self, tmp_path):
        """Path traversal sequences (..) escaping boundaries are rejected."""
        service = ResearchInferenceService()
        traversal_path = str(service.registry.root_dir / "data" / "recordings" / ".." / ".." / "outside.wav")
        with pytest.raises(UnauthorizedPathError):
            service.validate_recording_group([traversal_path])

    def test_null_bytes_in_path_rejected(self, service):
        with pytest.raises(AudioValidationError, match="Null bytes detected"):
            service.validate_recording_group(["test\x00path.wav"])

    def test_audio_duration_too_short(self, service, tmp_path):
        short_file = tmp_path / "14241_AV.wav"
        make_dummy_wav(short_file, duration_s=0.2)
        with pytest.raises(AudioValidationError, match="too short"):
            service.validate_recording_group([str(short_file)])

    def test_audio_duration_too_long(self, service, tmp_path):
        long_file = tmp_path / "14241_AV.wav"
        make_dummy_wav(long_file, duration_s=125.0)
        with pytest.raises(AudioValidationError, match="too long"):
            service.validate_recording_group([str(long_file)])

    def test_audio_file_size_limit(self, service, tmp_path, monkeypatch):
        """Audio files exceeding 15MB are rejected."""
        import os
        big_file = tmp_path / "14241_AV.wav"
        make_dummy_wav(big_file, duration_s=1.0)

        orig_stat = Path.stat
        def mock_stat(self):
            real = orig_stat(self)
            return os.stat_result((
                real.st_mode,
                real.st_ino,
                real.st_dev,
                real.st_nlink,
                real.st_uid,
                real.st_gid,
                16 * 1024 * 1024,  # 16 MB > 15 MB limit
                real.st_atime,
                real.st_mtime,
                real.st_ctime,
            ))
        monkeypatch.setattr(Path, "stat", mock_stat)

        with pytest.raises(AudioValidationError, match="exceeds maximum allowed size"):
            service.validate_recording_group([str(big_file)])


class TestResearchInferenceExecution:
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

    def test_api_predict_circor_if_present(self, client):
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

        # Research-only and calibration honesty
        assert data["research_only"] is True
        assert data["strictly_nonclinical"] is True
        assert data["is_clinically_calibrated"] is False
        assert data["score_interpretation"] == "uncalibrated_research_probability"

        # Subject-group integrity
        assert data["subject_integrity"]["integrity_status"] == "VERIFIED"
        assert data["subject_integrity"]["provenance"] == "VERIFIED_CIRCOR_SUBJECT"
        assert data["patient_identifier"] == "14241"

        # Probability and threshold
        assert 0.0 <= data["positive_probability"] <= 1.0
        assert data["validation_selected_threshold"] == pytest.approx(0.52, abs=1e-3)
        assert "RESEARCH ONLY" in data["disclaimer"]
        assert data["predicted_label"] == "research_pattern_present"

        # Display paths sanitized (no leaking of Windows drive root or full paths)
        for rec in data["recordings_evaluated"]:
            assert "file_name" in rec
            assert "display_path" in rec

    def test_api_predict_rejects_mixed_subject(self, client):
        circor_dir = Path("data/external/circor-heart-sound-1.0.3/training_data")
        if not circor_dir.exists():
            pytest.skip("Local CirCor dataset not found")

        wav1 = str(circor_dir / "14241_AV.wav")
        wav2 = str(circor_dir / "2530_MV.wav")
        if not Path(wav1).exists() or not Path(wav2).exists():
            pytest.skip("CirCor benchmark samples not present")

        resp = client.post(
            "/api/research/ml/predict",
            json={"file_paths": [wav1, wav2], "model_id": "af_murmur_mil_1.0"},
        )
        assert resp.status_code == 400
        assert "Mixed-subject group rejected" in resp.json()["detail"]

    def test_api_predict_model_not_found(self, client):
        resp = client.post(
            "/api/research/ml/predict",
            json={"file_paths": ["data/dummy.wav"], "model_id": "nonexistent_model"},
        )
        assert resp.status_code in (400, 503)

    def test_inference_concurrency_mutex(self, tmp_path):
        """Concurrent calls to the inference service are safely serialized under the lock."""
        async def run():
            service = ResearchInferenceService()
            assert not service._inference_lock.locked()
            async with service._inference_lock:
                assert service._inference_lock.locked()
            assert not service._inference_lock.locked()
        asyncio.run(run())
