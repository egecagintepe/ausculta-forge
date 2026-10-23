from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pcg_app.app import create_app
from pcg_app.state import StreamManager


def test_parameterless_filter_reapply_preserves_preset_pipeline_and_band(tmp_path: Path):
    manager = StreamManager(sessions_dir=tmp_path / "sessions")
    original_pipeline = manager.pipeline

    state = manager.set_filter()

    assert state["filter_preset"] == "recommended"
    assert state["filter_low_hz"] == 20.0
    assert state["filter_high_hz"] == 200.0
    assert manager.pipeline is original_pipeline


def test_custom_filter_contract_and_invalid_inputs(tmp_path: Path):
    manager = StreamManager(sessions_dir=tmp_path / "sessions")

    custom = manager.set_filter(low_hz=35, high_hz=420)
    assert custom["filter_preset"] == "custom"
    assert custom["filter_low_hz"] == 35.0
    assert custom["filter_high_hz"] == 420.0

    # A no-argument refresh must preserve the custom selection as well.
    refreshed = manager.set_filter()
    assert refreshed["filter_preset"] == "custom"
    assert refreshed["filter_low_hz"] == 35.0
    assert refreshed["filter_high_hz"] == 420.0

    with pytest.raises(ValueError, match="0 < low_hz < high_hz"):
        manager.set_filter(low_hz=500, high_hz=200)
    with pytest.raises(ValueError, match="Unknown filter preset"):
        manager.set_filter(preset="unsupported")


def test_filter_http_contract_accepts_custom_and_returns_bad_input(tmp_path: Path):
    app = create_app(
        sessions_dir=tmp_path / "sessions",
        assets_dir=tmp_path / "assets",
        analysis_dir=tmp_path / "analysis",
    )
    with TestClient(app) as client:
        response = client.post("/api/stream/filter", json={"preset": "custom", "low_hz": 40, "high_hz": 800})
        assert response.status_code == 200
        assert response.json()["filter_preset"] == "custom"
        assert response.json()["filter_low_hz"] == 40.0
        assert response.json()["filter_high_hz"] == 800.0

        invalid = client.post("/api/stream/filter", json={"preset": "not-a-preset"})
        assert invalid.status_code == 400
