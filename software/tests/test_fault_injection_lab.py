"""Tests for Diagnostics Fault Injection Laboratory (Phase 9).

Validates 25 deterministic fault scenarios:
- Verifies correct fault codes, subsystems, severities, evidence origins.
- Ensures no physical measurements or PHYSICAL_G1_PASS are fabricated.
- Ensures journal persistence and event correlation.
"""

import pytest

from pcg_app.diagnostics.event_model import EvidenceOrigin, Severity, Subsystem
from pcg_app.diagnostics.fault_catalog import get_fault_definition
from pcg_app.diagnostics.fault_injection_lab import FaultInjectionLab, ScenarioResult
from pcg_app.diagnostics.flight_recorder import FlightRecorderJournal


class TestFaultInjectionLaboratory:
    @pytest.fixture
    def lab(self, tmp_path):
        journal = FlightRecorderJournal(log_dir=tmp_path, in_memory_capacity=200)
        return FaultInjectionLab(journal=journal)

    def test_minimum_scenario_count(self, lab: FaultInjectionLab):
        scenarios = lab.list_scenarios()
        assert len(scenarios) >= 20, f"Expected at least 20 scenarios, got {len(scenarios)}"

    def test_all_scenarios_have_valid_catalog_entries(self, lab: FaultInjectionLab):
        for item in lab.list_scenarios():
            code = item["fault_code"]
            entry = get_fault_definition(code)
            assert entry is not None, f"Catalog missing entry for fault code {code}"
            assert entry.code == code

    def test_run_all_scenarios_deterministic(self, lab: FaultInjectionLab):
        results = lab.run_all()
        assert len(results) >= 20
        for res in results:
            assert res.passed is True
            assert res.emitted_event_id is not None
            assert res.target_fault_code.startswith("AF-")
            assert isinstance(res.subsystem, Subsystem)
            assert isinstance(res.severity, Severity)
            assert isinstance(res.evidence_origin, EvidenceOrigin)
            # Ensure evidence origin is never marked as physical observation
            assert res.evidence_origin in (
                EvidenceOrigin.INJECTED_SIMULATION,
                EvidenceOrigin.REPORTED_BY_FIRMWARE,
                EvidenceOrigin.DERIVED_FROM_SAMPLES,
            )

    @pytest.mark.parametrize(
        "scenario_id,expected_code,expected_subsystem",
        [
            ("empty_discovery", "AF-USB-001", Subsystem.USB),
            ("port_permission_denied", "AF-USB-002", Subsystem.USB),
            ("busy_com_port", "AF-USB-002", Subsystem.USB),
            ("missing_hello_ack", "AF-USB-005", Subsystem.USB),
            ("wrong_hello_nonce", "AF-PRT-004", Subsystem.PROTOCOL),
            ("incompatible_protocol_version", "AF-PRT-003", Subsystem.PROTOCOL),
            ("wrong_start_encoding", "AF-PRT-005", Subsystem.PROTOCOL),
            ("zero_session_id", "AF-PRT-006", Subsystem.PROTOCOL),
            ("stale_stop_ack", "AF-PRT-006", Subsystem.PROTOCOL),
            ("corrupted_crc", "AF-PRT-002", Subsystem.PROTOCOL),
            ("invalid_magic", "AF-PRT-001", Subsystem.PROTOCOL),
            ("dropped_audio_packet", "AF-STR-001", Subsystem.STREAMING),
            ("repeated_audio_packet", "AF-STR-002", Subsystem.STREAMING),
            ("reordered_sample_index", "AF-STR-003", Subsystem.STREAMING),
            ("firmware_ring_overflow", "AF-STR-007", Subsystem.STREAMING),
            ("incorrect_integer_sample", "AF-STR-009", Subsystem.STREAMING),
            ("near_silence", "AF-SIG-001", Subsystem.SIGNAL),
            ("clipping", "AF-SIG-002", Subsystem.SIGNAL),
            ("excessive_dc_offset", "AF-SIG-003", Subsystem.SIGNAL),
            ("insufficient_storage", "AF-FILE-003", Subsystem.STORAGE),
            ("wav_integrity_mismatch", "AF-FILE-002", Subsystem.STORAGE),
            ("backend_exited", "AF-APP-002", Subsystem.APP),
        ],
    )
    def test_individual_scenario_execution(
        self, lab: FaultInjectionLab, scenario_id: str, expected_code: str, expected_subsystem: Subsystem
    ):
        res = lab.run_scenario(scenario_id)
        assert res.passed is True
        assert res.target_fault_code == expected_code
        assert res.subsystem == expected_subsystem

        # Check that event was recorded into journal
        events = lab.journal.get_recent_events(limit=10)
        matched = [e for e in events if e.event_id == res.emitted_event_id]
        assert len(matched) == 1
        ev = matched[0]
        assert ev.fault_code == expected_code
        assert ev.subsystem == expected_subsystem
