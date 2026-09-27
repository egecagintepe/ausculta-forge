"""Tests for validation benchmark REST API endpoints."""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from pcg_app.app import create_app
from pcg_app.analysis_service import AnalysisService


def test_validation_benchmarks_api(tmp_path):
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy benchmark report
    bm_id = "test_benchmark_123"
    bm_folder = benchmarks_dir / bm_id
    bm_folder.mkdir(parents=True, exist_ok=True)

    report_data = {
        "schema_version": "1.0.0",
        "benchmark_id": bm_id,
        "status": "COMPLETE_DATASET",
        "config": {
            "dataset_id": "CIRCOR_DIGISCOPE",
            "dataset_version": "1.0.3",
            "profile_id": "SPRINGER_PHYSIONET_REFERENCE_V1",
            "fold_count": 5,
            "random_seed": 2026,
            "tolerances_ms": [20, 40, 60, 80, 100],
            "primary_event_anchor": "ONSET",
        },
        "coverage": {
            "total_eligible_records": 10,
            "successful_segmentations": 10,
            "failed_segmentations": 0,
            "coverage_rate": 1.0,
            "failure_status_counts": {},
        },
        "provenance": {
            "timestamp_utc": "2026-09-27T12:00:00Z",
            "git_commit_sha": "abc1234",
        },
    }

    with open(bm_folder / "benchmark.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    service = AnalysisService(
        analysis_dir=tmp_path / "analysis",
        sessions_dir=tmp_path / "sessions",
        assets_dir=tmp_path / "assets",
        benchmarks_dir=benchmarks_dir,
    )
    app = create_app(
        sessions_dir=tmp_path / "sessions",
        analysis_service=service,
    )
    client = TestClient(app)

    # 1. List benchmarks
    resp = client.get("/api/scientific/validation/benchmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["benchmark_id"] == bm_id
    assert data[0]["status"] == "COMPLETE_DATASET"
    assert data[0]["dataset_id"] == "CIRCOR_DIGISCOPE"

    # 2. Get specific benchmark
    resp_bm = client.get(f"/api/scientific/validation/benchmarks/{bm_id}")
    assert resp_bm.status_code == 200
    assert resp_bm.json()["benchmark_id"] == bm_id

    # 3. 404 for non-existent benchmark
    resp_404 = client.get("/api/scientific/validation/benchmarks/non_existent_bm")
    assert resp_404.status_code == 404

    # 4. 400 for invalid identifier (special characters)
    resp_invalid = client.get("/api/scientific/validation/benchmarks/invalid!id")
    assert resp_invalid.status_code == 400
