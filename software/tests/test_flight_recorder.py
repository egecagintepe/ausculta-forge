"""AuscultaForge — Unit Tests for Persistent Flight Recorder Journal."""

import json
from pathlib import Path
import time
import pytest

from pcg_app.diagnostics.event_model import DiagnosticEvent, Severity, Subsystem, EvidenceOrigin
from pcg_app.diagnostics.flight_recorder import (
    FlightRecorderJournal,
    redact_sensitive_data,
    redact_dict,
)


def test_redact_sensitive_data():
    """Verify secrets and authentication tokens are properly redacted."""
    raw = "Failed auth: token=4f9b8c2d1e0a9f8b7c6d5e4a3b2c1d0e and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    clean = redact_sensitive_data(raw)
    assert "[REDACTED" in clean
    assert "4f9b8c2d1e0a9f8b7c6d5e4a3b2c1d0e" not in clean

    d = {"user": "tester", "auth_token": "secret123", "nested": {"password": "pwd", "normal": "val"}}
    clean_d = redact_dict(d)
    assert clean_d["auth_token"] == "[REDACTED]"
    assert clean_d["nested"]["password"] == "[REDACTED]"
    assert clean_d["nested"]["normal"] == "val"


def test_flight_recorder_in_memory_and_dedup(tmp_path: Path):
    """Verify non-blocking submission and duplicate event aggregation."""
    journal = FlightRecorderJournal(log_dir=tmp_path, dedup_window_seconds=1.0)
    try:
        # Emit first event
        e1 = journal.record(
            fault_code="AF-USB-001",
            message="No device found on COM bus",
            subsystem=Subsystem.USB,
            severity=Severity.WARNING,
        )
        assert e1.occurrence_count == 1

        # Emit identical event immediately -> should aggregate
        e2 = journal.record(
            fault_code="AF-USB-001",
            message="No device found on COM bus",
            subsystem=Subsystem.USB,
            severity=Severity.WARNING,
        )
        assert e2.occurrence_count == 2
        assert len(journal.get_recent_events()) == 1

        # Emit different event
        e3 = journal.record(
            fault_code="AF-PRT-001",
            message="Sync magic missing",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
        )
        assert e3.occurrence_count == 1
        assert len(journal.get_recent_events()) == 2

        # Filter by subsystem
        usb_events = journal.get_recent_events(subsystem=Subsystem.USB)
        assert len(usb_events) == 1
        assert usb_events[0].fault_code == "AF-USB-001"

    finally:
        journal.shutdown()


def test_flight_recorder_disk_persistence_and_recovery(tmp_path: Path):
    """Verify asynchronous JSONL disk writing and restart persistence."""
    journal1 = FlightRecorderJournal(log_dir=tmp_path, max_file_size_bytes=100000)
    try:
        journal1.record(
            fault_code="AF-USB-002",
            message="Port access denied",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            connection_attempt_id="conn-101",
        )
        journal1.record(
            fault_code="AF-PRT-002",
            message="CRC check failed",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            session_id="sess-202",
        )
        # Allow worker thread to flush
        time.sleep(0.4)
    finally:
        journal1.shutdown()

    # Verify JSONL file exists on disk
    jsonl_file = tmp_path / "flight_recorder.jsonl"
    assert jsonl_file.exists()
    lines = jsonl_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    # Instantiate second journal instance simulating application restart
    journal2 = FlightRecorderJournal(log_dir=tmp_path)
    try:
        recent = journal2.get_recent_events()
        assert len(recent) == 2
        assert recent[0].fault_code == "AF-USB-002"
        assert recent[1].fault_code == "AF-PRT-002"
        assert recent[0].connection_attempt_id == "conn-101"
        assert recent[1].session_id == "sess-202"
    finally:
        journal2.shutdown()


def test_flight_recorder_rotation(tmp_path: Path):
    """Verify size-based log rotation when file exceeds threshold."""
    # Set tiny max_file_size_bytes to trigger rotation
    journal = FlightRecorderJournal(log_dir=tmp_path, max_file_size_bytes=500, max_backup_files=3)
    try:
        for i in range(15):
            journal.record(
                fault_code="AF-STR-001",
                message=f"Sequence gap {i} occurred on frame {i * 10}",
                subsystem=Subsystem.STREAMING,
                severity=Severity.WARNING,
                frame_sequence=i * 10,
            )
            time.sleep(0.05)

        time.sleep(0.5)
        # Check that backup rotated files exist
        backup1 = tmp_path / "flight_recorder.1.jsonl"
        assert backup1.exists(), "Rotation backup file flight_recorder.1.jsonl was not created"
    finally:
        journal.shutdown()
