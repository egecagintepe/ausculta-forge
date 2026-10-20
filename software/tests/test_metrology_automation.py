"""AuscultaForge — Tests for Metrology Automation & Laboratory Report Pipeline (Sprint 08).

Verifies the mathematical rigor, numerical validity, schema constraints, and report generation
for the six mandatory advisor measurements:
1. Phantom Frequency Response (20–500 Hz H1 & Coherence)
2. Active-to-Quiescent Level Ratio (SNR Convention)
3. Repeatability Study (>= 10 Independent Runs)
4. 50 Hz Mains Interference & Harmonics (Delta f <= 0.5 Hz)
5. End-to-End Latency & Synchronization Verification
6. Dropped-Sample Continuity Rate (30-Minute Gate Test)
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import tempfile
import numpy as np
import pytest
import scipy.signal
import scipy.io.wavfile as wavfile
from fastapi.testclient import TestClient

from pcg_core.metrology import (
    MeasurementStatus,
    SensorConfiguration,
    PhantomFrequencyResponseResult,
    SnrLevelRatioResult,
    RepeatabilityStudyResult,
    MainsInterferenceResult,
    LatencyMeasurementResult,
    PacketDropContinuityResult,
    AdvisorMetrologyReport,
    compute_phantom_frf,
    compute_active_quiescent_snr,
    compute_repeatability_study,
    compute_mains_interference,
    compute_latency_measurement,
    compute_continuity_drop_rate,
    export_report_to_json,
    export_summary_to_csv,
    format_human_readable_summary,
    MetrologyExperimentConfig,
    MetrologyRunner,
    Workflow1Config,
    Workflow2Config,
    Workflow3Config,
    Workflow4Config,
    Workflow5Config,
    Workflow6Config,
)
from pcg_app.app import create_app
from pcg_app.analysis_service import AnalysisService


# =============================================================================
# Workflow 1: Phantom Frequency Response Tests
# =============================================================================

class TestPhantomFrequencyResponse:
    def test_known_lowpass_phantom_recovery(self):
        fs = 4000.0
        n_samples = int(fs * 2.0)
        rng = np.random.default_rng(42)
        stim = rng.standard_normal(n_samples).astype(np.float32)

        # 4th-order Butterworth lowpass at 250 Hz (within 20–500 Hz target band)
        sos = scipy.signal.butter(4, 250.0, btype="lowpass", fs=fs, output="sos")
        resp = scipy.signal.sosfilt(sos, stim) + rng.standard_normal(n_samples).astype(np.float32) * 0.001

        res = compute_phantom_frf(
            input_stimulus=stim,
            output_response=resp,
            sample_rate_hz=fs,
            target_band_hz=(20.0, 500.0),
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.status == MeasurementStatus.BENCH_MEASURED.value
        assert len(res.frequencies_hz) > 0
        assert len(res.h1_magnitude_db) == len(res.frequencies_hz)
        assert len(res.coherence) == len(res.frequencies_hz)
        assert res.mean_coherence_target_band is not None
        assert res.mean_coherence_target_band > 0.80  # high coherence with low noise
        assert res.passband_ripple_db is not None
        assert res.excited_bins_count > 0

    def test_invalid_parameters_raise_value_error(self):
        stim = np.ones(100)
        resp = np.ones(100)
        with pytest.raises(ValueError, match="sample_rate_hz must be positive"):
            compute_phantom_frf(stim, resp, sample_rate_hz=0.0)

        with pytest.raises(ValueError, match="must be non-empty"):
            compute_phantom_frf(np.array([]), resp, sample_rate_hz=4000.0)


# =============================================================================
# Workflow 2: Active-to-Quiescent Level Ratio (SNR) Tests
# =============================================================================

class TestActiveQuiescentSnr:
    def test_synthetic_exact_snr_calculation(self):
        fs = 4000.0
        duration = 1.0
        t = np.linspace(0, duration, int(fs * duration), endpoint=False)

        # 100 Hz tone: RMS is amplitude / sqrt(2)
        amp = 0.2
        active_pure = amp * np.sin(2 * np.pi * 100.0 * t)
        quiescent_rms = 0.002
        rng = np.random.default_rng(123)
        quiescent_pure = rng.standard_normal(len(t)) * quiescent_rms

        # Active RMS ~ 0.2 / sqrt(2) ~ 0.14142
        # Expected SNR ~ 20 * log10(0.14142 / 0.002) ~ 37.0 dB
        res = compute_active_quiescent_snr(
            active_signal=active_pure,
            quiescent_signal=quiescent_pure,
            sample_rate_hz=fs,
            filter_band_hz=(20.0, 500.0),
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.status == MeasurementStatus.BENCH_MEASURED.value
        # Post-filter quiescent RMS is attenuated by the bandpass filter; ratio matches formula exactly
        expected_snr = 20.0 * math.log10(res.active_rms_fs / res.quiescent_rms_fs)
        assert math.isclose(res.active_to_quiescent_ratio_db, expected_snr, abs_tol=0.01)
        assert 40.0 < res.active_to_quiescent_ratio_db < 45.0
        assert res.active_rms_fs > res.quiescent_rms_fs
        assert res.sensor_config.sensor_model == "INMP441"

    def test_sensor_configuration_declaration(self):
        ecm_sensor = SensorConfiguration(
            sensor_model="ECM_CZN15E",
            interface_type="ANALOG_PREAMP",
            nominal_sensitivity_declared="-42 dBV/Pa",
            preamp_gain_db=26.0,
        )
        sig = np.random.randn(1000)
        res = compute_active_quiescent_snr(
            active_signal=sig * 2.0,
            quiescent_signal=sig * 0.1,
            sample_rate_hz=4000.0,
            sensor_config=ecm_sensor,
        )
        assert res.sensor_config.sensor_model == "ECM_CZN15E"
        assert res.sensor_config.preamp_gain_db == 26.0


# =============================================================================
# Workflow 3: Repeatability Study Tests
# =============================================================================

class TestRepeatabilityStudy:
    def test_ten_repeated_runs_statistics(self):
        runs = [24.1, 24.5, 23.9, 24.3, 24.0, 24.2, 24.4, 23.8, 24.6, 24.2]
        res = compute_repeatability_study(
            run_values=runs,
            metric_name="active_to_quiescent_ratio_db",
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.run_count == 10
        assert res.meets_minimum_runs_requirement is True
        assert math.isclose(res.mean, 24.2, abs_tol=0.05)
        assert res.std_dev > 0.0
        assert res.variance == round(res.std_dev ** 2, 6)
        assert res.coefficient_of_variation_pct == round((res.std_dev / res.mean) * 100.0, 2)
        assert res.confidence_interval_95[0] < res.mean < res.confidence_interval_95[1]
        assert res.range_value == round(res.max_value - res.min_value, 4)

    def test_outlier_retention_and_logging(self):
        runs = [25.0] * 9 + [12.0]  # run 10 was an accidental apparatus knock
        outlier_log = [{"run_index": 10, "value_db": 12.0, "cause": "Cable knocked by bench technician"}]

        res = compute_repeatability_study(
            run_values=runs,
            outliers_documented=outlier_log,
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.run_count == 10
        assert len(res.run_values) == 10  # Outlier was NOT discarded!
        assert len(res.outliers_documented) == 1
        assert res.outliers_documented[0]["cause"] == "Cable knocked by bench technician"


# =============================================================================
# Workflow 4: 50 Hz Mains Interference Tests
# =============================================================================

class TestMainsInterference:
    def test_high_resolution_psd_mains_pickup(self):
        fs = 4000.0
        duration = 4.0
        t = np.linspace(0, duration, int(fs * duration), endpoint=False)
        rng = np.random.default_rng(999)

        # Baseline noise + 50 Hz tone + 150 Hz 3rd harmonic
        sig = rng.standard_normal(len(t)) * 0.001
        sig += 0.01 * np.sin(2 * np.pi * 50.0 * t)   # 50 Hz
        sig += 0.005 * np.sin(2 * np.pi * 150.0 * t) # 150 Hz

        res = compute_mains_interference(
            quiescent_signal=sig,
            sample_rate_hz=fs,
            harmonics_hz=(50.0, 100.0, 150.0, 200.0, 250.0),
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.status == MeasurementStatus.BENCH_MEASURED.value
        assert res.frequency_resolution_hz <= 0.5  # Crucial advisor resolution requirement
        # 50 Hz and 150 Hz powers should be significantly higher than 100 Hz (no tone injected at 100)
        p_50 = res.harmonic_powers_dbfs[0]
        p_100 = res.harmonic_powers_dbfs[1]
        p_150 = res.harmonic_powers_dbfs[2]

        assert p_50 > p_100 + 10.0
        assert p_150 > p_100 + 5.0
        assert res.mains_to_total_power_ratio_pct > 0.0


# =============================================================================
# Workflow 5: End-to-End Latency Tests
# =============================================================================

class TestLatencyMeasurement:
    def test_valid_hardware_trigger_timestamps(self):
        tx = [0.100, 0.500, 0.900, 1.300]
        rx = [0.125, 0.526, 0.924, 1.325]  # ~25 ms transit latency

        res = compute_latency_measurement(
            stimulus_trigger_timestamps_s=tx,
            received_timestamps_s=rx,
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.status == MeasurementStatus.BENCH_MEASURED.value
        assert res.has_valid_hardware_sync is True
        assert res.synchronization_method == "HARDWARE_TRIGGER_TIMESTAMPS"
        assert math.isclose(res.end_to_end_latency_ms, 25.0, abs_tol=0.5)
        assert res.jitter_ms is not None
        assert res.jitter_ms < 2.0

    def test_unsynchronized_fallback_warns_researcher(self):
        res = compute_latency_measurement(
            acoustic_cross_corr_lag_ms=3.2,
            playback_buffer_delay_ms=25.0,
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.has_valid_hardware_sync is False
        assert res.synchronization_method == "UNSYNCHRONIZED_ACOUSTIC_LAG_ONLY"
        assert res.end_to_end_latency_ms is None
        assert "SYNCHRONIZATION EVIDENCE MISSING" in res.notes


# =============================================================================
# Workflow 6: Dropped-Sample Continuity Rate Tests
# =============================================================================

class TestPacketDropContinuity:
    def test_stream_with_injected_drop_events(self):
        # Continuous packets 1..100, drop 101..105, continuous 106..200
        seqs = list(range(1, 101)) + list(range(106, 201))
        res = compute_continuity_drop_rate(
            sequence_numbers=seqs,
            samples_per_packet=128,
            sample_rate_hz=48000,
            total_elapsed_seconds=10.0,
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.status == MeasurementStatus.BENCH_MEASURED.value
        assert res.gap_events_count == 1
        assert res.dropped_samples_count == 5 * 128  # 5 missed packets * 128 samples
        assert res.expected_samples_count == 200 * 128
        assert res.ingested_samples_count == 195 * 128
        assert res.drop_rate_pct == round((640 / (200 * 128)) * 100.0, 6)
        assert res.is_30_minute_gate_met is False  # 10s is far below 1800s

    def test_thirty_minute_gate_satisfied(self):
        # 14,063 consecutive packets without drops for 1800s
        seqs = list(range(1, 14064))
        res = compute_continuity_drop_rate(
            sequence_numbers=seqs,
            samples_per_packet=128,
            sample_rate_hz=1000,
            total_elapsed_seconds=1800.5,
            status=MeasurementStatus.BENCH_MEASURED,
        )

        assert res.dropped_samples_count == 0
        assert res.gap_events_count == 0
        assert res.is_30_minute_gate_met is True


# =============================================================================
# Multi-Format Report Exporter Tests
# =============================================================================

class TestReportExporters:
    def test_json_csv_markdown_export_cycle(self, tmp_path: Path):
        cfg = MetrologyExperimentConfig(
            experiment_id="exp_test_cycle",
            title="Metrology Test Cycle",
            author="Test Runner",
            apparatus_id="TEST_BENCH_01",
            run_synthetic_verification=True,
        )
        runner = MetrologyRunner(cfg)
        report = runner.run(output_dir=tmp_path)

        assert report.report_id == "exp_test_cycle"
        assert report.overall_hardware_status == "SYNTHETIC_VERIFIED"

        # Verify JSON
        json_path = tmp_path / "metrology_report.json"
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["report_id"] == "exp_test_cycle"
        assert "workflow_1_frequency_response" in data

        # Verify CSV
        csv_path = tmp_path / "metrology_summary.csv"
        assert csv_path.exists()
        csv_text = csv_path.read_text(encoding="utf-8")
        assert "Workflow_ID,Measurement_Name,Status" in csv_text
        assert "W1,Phantom Frequency Response" in csv_text
        assert "W6,Dropped-Sample Rate" in csv_text

        # Verify Markdown
        md_path = tmp_path / "metrology_report.md"
        assert md_path.exists()
        md_text = md_path.read_text(encoding="utf-8")
        assert "# AUSCULTAFORGE — ADVISOR METROLOGY REPORT" in md_text
        assert "Executive Summary: The Six Mandatory Measurements" in md_text
        assert "Uncalibrated Sensor Output" in md_text


# =============================================================================
# Default Not Yet Measured State Tests
# =============================================================================

class TestDefaultUnmeasuredState:
    def test_default_config_leaves_all_unmeasured(self):
        cfg = MetrologyExperimentConfig(run_synthetic_verification=False)
        runner = MetrologyRunner(cfg)
        report = runner.run()

        assert report.overall_hardware_status == "NOT_YET_MEASURED"
        assert report.workflow_1_frequency_response.status == MeasurementStatus.NOT_YET_MEASURED.value
        assert report.workflow_2_snr_level_ratio.status == MeasurementStatus.NOT_YET_MEASURED.value
        assert report.workflow_3_repeatability.status == MeasurementStatus.NOT_YET_MEASURED.value
        assert report.workflow_4_mains_interference.status == MeasurementStatus.NOT_YET_MEASURED.value
        assert report.workflow_5_latency.status == MeasurementStatus.NOT_YET_MEASURED.value
        assert report.workflow_6_dropped_samples.status == MeasurementStatus.NOT_YET_MEASURED.value


# =============================================================================
# Bench WAV Execution and Failure Handling Tests
# =============================================================================

class TestBenchWavExecutionAndFailureIsolation:
    def test_corrupted_wav_file_isolates_failure_without_aborting_suite(self, tmp_path: Path):
        # Create a valid active WAV and a corrupted quiescent file
        fs = 4000
        active_wav = tmp_path / "active.wav"
        corrupt_wav = tmp_path / "corrupt.wav"

        t = np.linspace(0, 1.0, fs, endpoint=False)
        wavfile.write(active_wav, fs, (0.5 * np.sin(2 * np.pi * 100 * t) * 32767).astype(np.int16))
        corrupt_wav.write_text("NOT A REAL WAV FILE DATA")

        cfg = MetrologyExperimentConfig(
            workflow_2=Workflow2Config(
                active_wav_path=str(active_wav),
                quiescent_wav_path=str(corrupt_wav),
            ),
            run_synthetic_verification=False,
        )
        runner = MetrologyRunner(cfg)
        report = runner.run()

        # Workflow 2 should report FAILED, others remain NOT_YET_MEASURED
        assert report.workflow_2_snr_level_ratio.status == MeasurementStatus.FAILED.value
        assert report.overall_hardware_status == "CONTAINS_FAILURES"
        assert any("Workflow 2 physical execution failed" in lim for lim in report.limitations_and_uncertainties)
        assert report.workflow_1_frequency_response.status == MeasurementStatus.NOT_YET_MEASURED.value


# =============================================================================
# Application Service and REST API Integration Tests
# =============================================================================

class TestMetrologyApiIntegration:
    @pytest.fixture
    def test_app_and_service(self, tmp_path: Path):
        sessions_dir = tmp_path / "sessions"
        analysis_dir = tmp_path / "analysis"
        assets_dir = tmp_path / "assets"
        metrology_dir = tmp_path / "metrology"

        service = AnalysisService(
            assets_dir=assets_dir,
            analysis_dir=analysis_dir,
            sessions_dir=sessions_dir,
            metrology_dir=metrology_dir,
        )
        app = create_app(
            sessions_dir=sessions_dir,
            assets_dir=assets_dir,
            analysis_dir=analysis_dir,
            analysis_service=service,
        )
        client = TestClient(app)
        return client, service

    def test_template_and_synthetic_run_api(self, test_app_and_service):
        client, service = test_app_and_service

        # 1. GET template
        resp_tpl = client.get("/api/scientific/metrology/template")
        assert resp_tpl.status_code == 200
        template_cfg = resp_tpl.json()
        assert "workflow_1" in template_cfg
        assert "sensor_declarations" in template_cfg

        # 2. POST run with synthetic mode
        template_cfg["experiment_id"] = "api_exp_test"
        template_cfg["run_synthetic_verification"] = True

        resp_run = client.post("/api/scientific/metrology/run", json={"config": template_cfg})
        assert resp_run.status_code == 200
        run_data = resp_run.json()
        assert run_data["report_id"] == "api_exp_test"
        assert run_data["overall_hardware_status"] == "SYNTHETIC_VERIFIED"

        # 3. GET list reports
        resp_list = client.get("/api/scientific/metrology/reports")
        assert resp_list.status_code == 200
        reports_list = resp_list.json()
        assert len(reports_list) >= 1
        assert reports_list[0]["report_id"] == "api_exp_test"

        # 4. GET report by ID
        resp_get = client.get("/api/scientific/metrology/reports/api_exp_test")
        assert resp_get.status_code == 200
        assert resp_get.json()["report_id"] == "api_exp_test"

        # 5. GET CSV summary
        resp_csv = client.get("/api/scientific/metrology/reports/api_exp_test/csv")
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv.headers["content-type"]
        assert "Workflow_ID" in resp_csv.text

        # 6. GET Markdown summary
        resp_md = client.get("/api/scientific/metrology/reports/api_exp_test/markdown")
        assert resp_md.status_code == 200
        assert "text/markdown" in resp_md.headers["content-type"]
        assert "# AUSCULTAFORGE — ADVISOR METROLOGY REPORT" in resp_md.text
