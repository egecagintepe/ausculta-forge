"""AuscultaForge — Unit Tests for Real USB Discovery Doctor."""

from dataclasses import dataclass
from pathlib import Path
import pytest

from pcg_app.diagnostics.flight_recorder import FlightRecorderJournal
from pcg_app.diagnostics.usb_doctor import (
    UsbDiscoveryDoctor,
    UsbPortDescriptor,
    DiscoveryDiagnosticState,
    ESPRESSIF_VID,
    ESP32_S3_CDC_ACM_PID,
)


@dataclass
class MockPortInfo:
    device: str
    description: str
    hwid: str
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    product: str | None = None
    interface: str | None = None


def test_usb_doctor_empty_bus(tmp_path: Path):
    """Verify empty serial bus is diagnosed truthfully without hallucinating hardware."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    doctor = UsbDiscoveryDoctor(flight_recorder=journal, custom_comports_fn=lambda: [])

    ports = doctor.scan_ports()
    assert len(ports) == 0

    state, info = doctor.diagnose_environment()
    assert state == DiscoveryDiagnosticState.NO_SERIAL_PORTS_ENUMERATED
    assert "No serial ports detected" in info["message"]

    # Verify event recorded
    events = journal.get_recent_events()
    assert len(events) == 1
    assert events[0].fault_code == "AF-USB-001"


def test_usb_doctor_detects_espressif_candidate(tmp_path: Path):
    """Verify detection of genuine Espressif ESP32-S3 CDC-ACM hardware descriptors."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)

    mock_ports = [
        MockPortInfo(
            device="COM4",
            description="USB Serial Device (COM4)",
            hwid=f"USB VID:PID={ESPRESSIF_VID:04X}:{ESP32_S3_CDC_ACM_PID:04X}",
            vid=ESPRESSIF_VID,
            pid=ESP32_S3_CDC_ACM_PID,
            manufacturer="Espressif",
            product="AuscultaForge Probe",
        )
    ]

    doctor = UsbDiscoveryDoctor(flight_recorder=journal, custom_comports_fn=lambda: mock_ports)
    ports = doctor.scan_ports()

    assert len(ports) == 1
    p = ports[0]
    assert p.port_name == "COM4"
    assert p.is_espressif_candidate is True
    assert "0x303A:0x1001" in p.candidate_reason


def test_usb_doctor_reenumeration_event(tmp_path: Path):
    """Verify that a device disappearing and reappearing triggers AF-USB-007 re-enumeration event."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)

    p1 = MockPortInfo(device="COM3", description="Generic COM", hwid="USB-01")
    p2 = MockPortInfo(device="COM7", description="ESP32-S3", hwid="USB-02", vid=ESPRESSIF_VID, pid=ESP32_S3_CDC_ACM_PID)

    # Scan 1: Only COM3
    doctor = UsbDiscoveryDoctor(flight_recorder=journal, custom_comports_fn=lambda: [p1])
    doctor.scan_ports()

    # Scan 2: COM3 + COM7
    doctor._custom_comports_fn = lambda: [p1, p2]
    ports = doctor.scan_ports()
    assert len(ports) == 2

    events = journal.get_recent_events(fault_code="AF-USB-007")
    assert len(events) == 1
    assert "COM7" in events[0].message
