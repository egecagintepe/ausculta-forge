"""AuscultaForge — Unit Tests for Root-Cause Correlation Engine."""

from pathlib import Path
import pytest

from pcg_app.diagnostics.event_model import Severity, Subsystem
from pcg_app.diagnostics.flight_recorder import FlightRecorderJournal
from pcg_app.diagnostics.correlation_engine import RootCauseCorrelationEngine


def test_correlation_engine_nominal_case(tmp_path: Path):
    """Verify clean system with no faults produces CASE_NOMINAL_HEALTHY."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    engine = RootCauseCorrelationEngine(journal)

    rep = engine.evaluate_incidents(is_device_connected=True)
    assert rep.case_id == "CASE_NOMINAL_HEALTHY"
    assert rep.active_incident_count == 0
    assert len(rep.ranked_hypotheses) == 1
    assert rep.ranked_hypotheses[0].confidence == "HIGH"


def test_correlation_engine_case_a_usb_absent(tmp_path: Path):
    """Verify AF-USB-001 triggers Case A (USB cable or unpowered board)."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    journal.record(fault_code="AF-USB-001", subsystem=Subsystem.USB, severity=Severity.WARNING)

    engine = RootCauseCorrelationEngine(journal)
    rep = engine.evaluate_incidents(is_device_connected=False)

    assert rep.case_id == "CASE_A_USB_ABSENT"
    assert len(rep.ranked_hypotheses) >= 2
    assert "Charge-Only" in rep.ranked_hypotheses[0].title


def test_correlation_engine_case_b_port_locked(tmp_path: Path):
    """Verify AF-USB-002 triggers Case B (Access Denied / Busy by serial monitor)."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    journal.record(fault_code="AF-USB-002", subsystem=Subsystem.USB, severity=Severity.ERROR)

    engine = RootCauseCorrelationEngine(journal)
    rep = engine.evaluate_incidents(current_port="COM3")

    assert rep.case_id == "CASE_B_PORT_LOCKED"
    assert "Competing Terminal" in rep.ranked_hypotheses[0].title


def test_correlation_engine_case_d_crc_corrupt(tmp_path: Path):
    """Verify AF-PRT-002 triggers Case D (CRC Calculation / Stream Corrupt)."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    journal.record(fault_code="AF-PRT-002", subsystem=Subsystem.PROTOCOL, severity=Severity.ERROR)

    engine = RootCauseCorrelationEngine(journal)
    rep = engine.evaluate_incidents(is_streaming=True)

    assert rep.case_id == "CASE_D_CRC_STREAM_CORRUPT"
    assert rep.ranked_hypotheses[0].subsystem == Subsystem.PROTOCOL
    assert "0xCBF43926" in rep.ranked_hypotheses[0].recommended_checklist[0]


def test_correlation_engine_case_e_near_silence(tmp_path: Path):
    """Verify AF-SIG-001 triggers Case E (Acoustic sensor float, NOT USB framing)."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    journal.record(fault_code="AF-SIG-001", subsystem=Subsystem.SIGNAL, severity=Severity.WARNING)

    engine = RootCauseCorrelationEngine(journal)
    rep = engine.evaluate_incidents(is_streaming=True)

    assert rep.case_id == "CASE_E_SIGNAL_ACOUSTIC_ANOMALY"
    assert "Microphone Sensor" in rep.ranked_hypotheses[0].title
    assert "NOT a USB protocol fault" in rep.ranked_hypotheses[0].recommended_checklist[0]
