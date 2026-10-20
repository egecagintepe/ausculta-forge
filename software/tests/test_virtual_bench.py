"""Tests for AuscultaForge Deterministic Virtual Bench and Known-Answer Testing.

Validates all 8 required integration scenarios:
- 48 kHz mono 100 Hz sine wave fidelity & frequency resolution
- Exact ascending sample counter with known start/end accounting
- Silence, half-scale sine, and full-scale boundary conditions
- Clipped waveform and step/impulse sequences
- Explicitly injected sequence gaps and duplicate packets
- Timestamp regression and rollover handling
- Corrupt CRC and out-of-range packet rejection
- Clean STOP, sudden cable interruption and reconnection recovery

Also validates:
- Machine-readable JSON acceptance reporting with SOFTWARE_KNOWN_ANSWER tags
- Fast API /api/bench/scenarios and /api/bench/run endpoints
- CLI entrypoint execution and artifact generation
"""

import json
from pathlib import Path
import sys
import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from pcg_app.app import create_app
from pcg_app.virtual_bench import (
    VirtualBenchRunner,
    VirtualBenchReport,
    ScenarioResult,
    main as bench_main,
)


@pytest.fixture
def bench_dir(tmp_path: Path) -> Path:
    b_dir = tmp_path / "virtual_bench_test"
    b_dir.mkdir(parents=True, exist_ok=True)
    return b_dir


@pytest.fixture
def runner(bench_dir: Path) -> VirtualBenchRunner:
    return VirtualBenchRunner(output_dir=bench_dir, seed=42)


# ==============================================================================
# 1. Scenario Unit Tests
# ==============================================================================

def test_scenario_list(runner: VirtualBenchRunner):
    scenarios = runner.list_scenarios()
    assert len(scenarios) == 8
    scen_ids = [s["id"] for s in scenarios]
    assert "sine_100hz_48k" in scen_ids
    assert "ascending_sample_counter" in scen_ids
    assert "boundary_conditions" in scen_ids
    assert "clipped_and_impulse" in scen_ids
    assert "injected_gaps_duplicates" in scen_ids
    assert "timestamp_regression" in scen_ids
    assert "corrupt_inputs_rejection" in scen_ids
    assert "lifecycle_interruption_reconnect" in scen_ids


def test_scenario_sine_100hz(runner: VirtualBenchRunner, bench_dir: Path):
    result = runner.run_scenario("sine_100hz_48k")
    assert result.passed is True
    assert result.status_label == "SOFTWARE_KNOWN_ANSWER"
    assert result.duration_ms > 0

    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["sample_rate_hz"].observed == 48000
    assert metric_map["sample_count"].observed == 10240
    assert metric_map["dominant_frequency"].observed == 100.0
    assert metric_map["waveform_max_error"].observed < 1e-5
    assert abs(metric_map["rms_level"].observed - (0.75 / np.sqrt(2))) < 0.01

    # Verify generated WAV file matches oracle
    wav_path = Path(result.artifacts["raw_wav"])
    assert wav_path.exists()
    fs, data = wavfile.read(wav_path)
    assert fs == 48000
    assert len(data) == 10240

    # Verify session JSON sidecar exists
    json_path = Path(result.artifacts["session_json"])
    assert json_path.exists()
    sidecar = json.loads(json_path.read_text(encoding="utf-8"))
    assert sidecar["sample_rate_hz"] == 48000
    assert sidecar["total_samples"] == 10240
    assert sidecar["source"] == "Software Bench Sine 100Hz"


def test_scenario_ascending_counter(runner: VirtualBenchRunner):
    result = runner.run_scenario("ascending_sample_counter")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["sample_count"].observed == 4096
    assert metric_map["first_sample_int"].observed == 500.0
    assert metric_map["last_sample_int"].observed == 4595.0
    assert metric_map["monotonic_increment"].observed == 1.0
    assert metric_map["zero_dropped_blocks"].observed == 0


def test_scenario_boundary_conditions(runner: VirtualBenchRunner):
    result = runner.run_scenario("boundary_conditions")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["silence_peak"].observed == 0.0
    assert abs(metric_map["half_scale_peak"].observed - 0.5) < 1e-4
    assert metric_map["full_scale_negative"].observed == -1.0
    assert abs(metric_map["full_scale_positive"].observed - 1.0) < 1e-4
    assert metric_map["no_nan_or_inf"].observed is True


def test_scenario_clipped_and_impulse(runner: VirtualBenchRunner):
    result = runner.run_scenario("clipped_and_impulse")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["impulse_index"].observed == 32
    assert abs(metric_map["impulse_peak_val"].observed - 1.0) < 1e-4
    assert abs(metric_map["clipped_square_rms"].observed - 1.0) < 0.05
    assert metric_map["total_recorded_samples"].observed == 1024


def test_scenario_injected_gaps_duplicates(runner: VirtualBenchRunner):
    result = runner.run_scenario("injected_gaps_duplicates")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["packets_received"].observed == 5
    assert metric_map["sequence_gaps"].observed == 2
    assert metric_map["repeated_packets"].observed == 1
    assert metric_map["total_samples_recorded"].observed == 2560


def test_scenario_timestamp_regression(runner: VirtualBenchRunner):
    result = runner.run_scenario("timestamp_regression")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["timestamp_regressions"].observed == 1
    assert metric_map["packets_received"].observed == 4
    assert metric_map["session_samples_intact"].observed == 2048


def test_scenario_corrupt_inputs_rejection(runner: VirtualBenchRunner):
    result = runner.run_scenario("corrupt_inputs_rejection")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["crc_failures_counted"].observed == 1
    assert metric_map["bad_packet_excluded_from_samples"].observed == 1024
    assert metric_map["out_of_range_sample_rejected"].observed is True


def test_scenario_lifecycle_interruption_reconnect(runner: VirtualBenchRunner):
    result = runner.run_scenario("lifecycle_interruption_reconnect")
    assert result.passed is True
    metric_map = {m.name: m for m in result.metrics}
    assert metric_map["interrupted_state_reached"].observed is True
    assert metric_map["session_1_termination_reason"].observed == "device_disconnected"
    assert metric_map["session_1_samples_preserved"].observed == 1024
    assert metric_map["session_2_completed_cleanly"].observed == "completed"
    assert metric_map["session_2_samples"].observed == 1536


# ==============================================================================
# 2. Full Suite Run & Serialization Tests
# ==============================================================================

def test_virtual_bench_run_all(runner: VirtualBenchRunner):
    report: VirtualBenchReport = runner.run_all()
    assert report.total_scenarios == 8
    assert report.passed_scenarios == 8
    assert report.failed_scenarios == 0
    assert report.all_passed is True
    assert report.status_tag == "SOFTWARE_KNOWN_ANSWER"

    # Test JSON serialization & deserialization
    json_str = report.to_json()
    parsed = json.loads(json_str)
    assert parsed["status_tag"] == "SOFTWARE_KNOWN_ANSWER"
    assert parsed["all_passed"] is True
    assert len(parsed["scenarios"]) == 8


# ==============================================================================
# 3. FastAPI REST Endpoints Tests
# ==============================================================================

def test_api_bench_endpoints(tmp_path: Path):
    app = create_app(sessions_dir=tmp_path / "sessions")
    with TestClient(app) as client:
        # GET scenarios list
        resp = client.get("/api/bench/scenarios")
        assert resp.status_code == 200
        scenarios = resp.json()
        assert len(scenarios) == 8

        # Run specific scenario
        resp_scen = client.post("/api/bench/run", json={"scenario_id": "ascending_sample_counter"})
        assert resp_scen.status_code == 200
        scen_data = resp_scen.json()
        assert scen_data["scenario_id"] == "ascending_sample_counter"
        assert scen_data["passed"] is True
        assert scen_data["status_label"] == "SOFTWARE_KNOWN_ANSWER"

        # Run invalid scenario
        resp_bad = client.post("/api/bench/run", json={"scenario_id": "nonexistent_scenario"})
        assert resp_bad.status_code == 400


# ==============================================================================
# 4. CLI Execution Test
# ==============================================================================

def test_cli_execution(tmp_path: Path, monkeypatch):
    out_json = tmp_path / "cli_report.json"
    test_args = [
        "virtual_bench.py",
        "--all",
        "--output-dir",
        str(tmp_path / "cli_artifacts"),
        "--json-out",
        str(out_json),
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    exit_code = bench_main()
    assert exit_code == 0
    assert out_json.exists()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["all_passed"] is True
    assert data["total_scenarios"] == 8
    assert data["status_tag"] == "SOFTWARE_KNOWN_ANSWER"
