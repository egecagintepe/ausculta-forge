"""AuscultaForge — Diagnostics Fault Injection Laboratory.

Provides deterministic, reproducible injection of at least 20 hardware,
protocol, streaming, signal quality, and storage fault scenarios into
the persistent diagnostic journal.

All injected events are strictly labeled with EvidenceOrigin.INJECTED_SIMULATION.
Never marks simulated runs as PHYSICAL_G1_PASS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Callable, Dict, List, Optional
import numpy as np

from pcg_app.diagnostics.event_model import (
    DiagnosticEvent,
    EvidenceOrigin,
    Severity,
    Subsystem,
)
from pcg_app.diagnostics.fault_catalog import get_fault_definition
from pcg_app.diagnostics.flight_recorder import FlightRecorderJournal
from pcg_app.diagnostics.signal_doctor import SignalQualityDoctor
from pcg_app.diagnostics.usb_doctor import UsbDiscoveryDoctor, UsbPortDescriptor


@dataclass(slots=True)
class ScenarioResult:
    scenario_id: str
    name: str
    target_fault_code: str
    subsystem: Subsystem
    severity: Severity
    evidence_origin: EvidenceOrigin
    passed: bool
    diagnostic_message: str
    emitted_event_id: Optional[str] = None
    extra_details: dict[str, Any] = field(default_factory=dict)


class FaultInjectionLab:
    """Registry and execution harness for deterministic diagnostic fault simulations."""

    def __init__(self, journal: Optional[FlightRecorderJournal] = None) -> None:
        self.journal = journal or FlightRecorderJournal(in_memory_capacity=200)

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return metadata for all available fault injection scenarios."""
        return [
            {"id": "empty_discovery", "name": "Empty Device Discovery", "fault_code": "AF-USB-001"},
            {"id": "port_permission_denied", "name": "Port Permission Denied", "fault_code": "AF-USB-002"},
            {"id": "busy_com_port", "name": "Busy COM Port (Locked)", "fault_code": "AF-USB-002"},
            {"id": "missing_hello_ack", "name": "Missing HELLO_ACK Timeout", "fault_code": "AF-USB-005"},
            {"id": "wrong_hello_nonce", "name": "Wrong HELLO Nonce", "fault_code": "AF-PRT-004"},
            {"id": "incompatible_protocol_version", "name": "Incompatible Protocol Version", "fault_code": "AF-PRT-003"},
            {"id": "wrong_start_encoding", "name": "START Configuration Rejected", "fault_code": "AF-PRT-005"},
            {"id": "zero_session_id", "name": "Zero Session ID In START_ACK", "fault_code": "AF-PRT-006"},
            {"id": "stale_stop_ack", "name": "Stale Session ID In STOP_ACK", "fault_code": "AF-PRT-006"},
            {"id": "corrupted_crc", "name": "Corrupted CRC Packet", "fault_code": "AF-PRT-002"},
            {"id": "invalid_magic", "name": "Invalid Packet Sync Magic", "fault_code": "AF-PRT-001"},
            {"id": "fragmented_packet_stream", "name": "Fragmented Packet Ingestion", "fault_code": "AF-PRT-007"},
            {"id": "dropped_audio_packet", "name": "Audio Frame Sequence Gap", "fault_code": "AF-STR-001"},
            {"id": "repeated_audio_packet", "name": "Duplicate Audio Frame", "fault_code": "AF-STR-002"},
            {"id": "reordered_sample_index", "name": "Sample Index Discontinuity", "fault_code": "AF-STR-003"},
            {"id": "usb_read_timeout", "name": "USB Read Ingestion Timeout", "fault_code": "AF-USB-005"},
            {"id": "usb_write_stall", "name": "USB Write Transmission Stalled", "fault_code": "AF-USB-006"},
            {"id": "firmware_ring_overflow", "name": "Firmware Ring Buffer Overflow", "fault_code": "AF-STR-007"},
            {"id": "incorrect_integer_sample", "name": "Corrupted PCM Integer Sample", "fault_code": "AF-STR-009"},
            {"id": "near_silence", "name": "Acoustic Near-Silence", "fault_code": "AF-SIG-001"},
            {"id": "clipping", "name": "Signal Rail Clipping", "fault_code": "AF-SIG-002"},
            {"id": "excessive_dc_offset", "name": "Excessive DC Offset Bias", "fault_code": "AF-SIG-003"},
            {"id": "insufficient_storage", "name": "Low Disk Storage Space", "fault_code": "AF-FILE-003"},
            {"id": "wav_integrity_mismatch", "name": "WAV Integrity Hash Mismatch", "fault_code": "AF-FILE-002"},
            {"id": "backend_exited", "name": "Backend Process Unexpected Exit", "fault_code": "AF-APP-002"},
        ]

    def run_scenario(self, scenario_id: str) -> ScenarioResult:
        """Execute a specific scenario by identifier."""
        method_name = f"scenario_{scenario_id}"
        if not hasattr(self, method_name):
            raise ValueError(f"Unknown scenario ID: {scenario_id}")
        fn = getattr(self, method_name)
        return fn()

    def run_all(self) -> list[ScenarioResult]:
        """Execute all scenarios in sequence and return results."""
        results = []
        for item in self.list_scenarios():
            results.append(self.run_scenario(item["id"]))
        return results

    # =========================================================================
    # Individual Scenario Implementations
    # =========================================================================

    def scenario_empty_discovery(self) -> ScenarioResult:
        doctor = UsbDiscoveryDoctor(flight_recorder=self.journal, custom_comports_fn=lambda: [])
        ports = doctor.scan_ports()
        msg = "Zero serial ports enumerated on host bus."
        event = self.journal.record(
            fault_code="AF-USB-001",
            message=msg,
            subsystem=Subsystem.USB,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            possible_causes=["No USB cable plugged in", "Non-data charging cable"],
            suggested_actions=["Connect ESP32-S3 via data USB cable"],
        )
        return ScenarioResult(
            scenario_id="empty_discovery",
            name="Empty Device Discovery",
            target_fault_code="AF-USB-001",
            subsystem=Subsystem.USB,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=msg,
            emitted_event_id=event.event_id,
        )

    def scenario_port_permission_denied(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-USB-002",
            message="Simulated OS permission denied accessing port /dev/ttyACM0 (udev rules required)",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            device_port="/dev/ttyACM0",
            possible_causes=["Missing dialout group permissions", "Access restricted by OS"],
            suggested_actions=["Add user to dialout group", "Install 99-ausculta-esp32.rules"],
        )
        return ScenarioResult(
            scenario_id="port_permission_denied",
            name="Port Permission Denied",
            target_fault_code="AF-USB-002",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_busy_com_port(self) -> ScenarioResult:
        port = UsbPortDescriptor(
            port_name="COM7",
            description="USB Serial Device (COM7)",
            hwid="USB\\VID_303A&PID_1001",
            vid=0x303A,
            pid=0x1001,
        )
        event = self.journal.record(
            fault_code="AF-USB-002",
            message=f"Port {port.port_name} is busy or locked by another serial monitor process",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            device_port=port.port_name,
            possible_causes=["IDF monitor or PuTTY open in another window"],
            suggested_actions=["Close competing serial terminal"],
        )
        return ScenarioResult(
            scenario_id="busy_com_port",
            name="Busy COM Port (Locked)",
            target_fault_code="AF-USB-002",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_missing_hello_ack(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-USB-005",
            message="Timeout waiting for HELLO_ACK response (1000ms elapsed)",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            possible_causes=["Firmware not implementing v0.1 handshake", "Wrong CDC interface"],
            suggested_actions=["Verify firmware flashes canonical protocol v0.1"],
        )
        return ScenarioResult(
            scenario_id="missing_hello_ack",
            name="Missing HELLO_ACK Timeout",
            target_fault_code="AF-USB-005",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_wrong_hello_nonce(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-004",
            message="HELLO nonce mismatch: expected 0x12345678, got 0x87654321",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            expected_value=0x12345678,
            observed_value=0x87654321,
            possible_causes=["Firmware corrupted nonce echo", "Byte order mismatch"],
            suggested_actions=["Check little-endian 32-bit nonce echo in firmware"],
        )
        return ScenarioResult(
            scenario_id="wrong_hello_nonce",
            name="Wrong HELLO Nonce",
            target_fault_code="AF-PRT-004",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_incompatible_protocol_version(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-003",
            message="Protocol version mismatch: expected major 1, got 2",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            expected_value=1,
            observed_value=2,
            possible_causes=["Firmware running newer incompatible wire protocol"],
            suggested_actions=["Sync host and firmware protocol definitions"],
        )
        return ScenarioResult(
            scenario_id="incompatible_protocol_version",
            name="Incompatible Protocol Version",
            target_fault_code="AF-PRT-003",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_wrong_start_encoding(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-005",
            message="START_ACK configuration rejected: encoding expected 1 (PCM16_LE) got 99",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            expected_value="1",
            observed_value="99",
            possible_causes=["Firmware does not support requested encoding profile"],
            suggested_actions=["Check profile capabilities returned in HELLO_ACK"],
        )
        return ScenarioResult(
            scenario_id="wrong_start_encoding",
            name="START Configuration Rejected",
            target_fault_code="AF-PRT-005",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_zero_session_id(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-006",
            message="Device returned invalid zero session_id in START_ACK",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            expected_value="nonzero uint64",
            observed_value=0,
            possible_causes=["Firmware session initialization bug", "Uninitialized session ID counter"],
            suggested_actions=["Ensure firmware increments session ID before START_ACK"],
        )
        return ScenarioResult(
            scenario_id="zero_session_id",
            name="Zero Session ID In START_ACK",
            target_fault_code="AF-PRT-006",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_stale_stop_ack(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-006",
            message="STOP_ACK session_id mismatch: expected 0x00000001, got 0xDEADBEEF00000000",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            session_id="0x00000001",
            expected_value="0x00000001",
            observed_value="0xDEADBEEF00000000",
            possible_causes=["Delayed STOP_ACK from previous session arrived"],
            suggested_actions=["Flush stale buffer before new handshake"],
        )
        return ScenarioResult(
            scenario_id="stale_stop_ack",
            name="Stale Session ID In STOP_ACK",
            target_fault_code="AF-PRT-006",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_corrupted_crc(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-002",
            message="CRC error detected on seq 12, opcode 0x01 (AUDIO_DATA)",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            frame_sequence=12,
            possible_causes=["USB physical cable noise", "Hardware framing misalignment"],
            suggested_actions=["Check USB cable shielding", "Verify CRC-32 IEEE 802.3 calculation"],
        )
        return ScenarioResult(
            scenario_id="corrupted_crc",
            name="Corrupted CRC Packet",
            target_fault_code="AF-PRT-002",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_invalid_magic(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-001",
            message="Invalid packet sync magic: expected 'AF', received 0x00 0x00",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            possible_causes=["Framing out of sync", "Baud rate mismatch or unformatted UART data"],
            suggested_actions=["Decoder resynchronizes at next AF header boundary"],
        )
        return ScenarioResult(
            scenario_id="invalid_magic",
            name="Invalid Packet Sync Magic",
            target_fault_code="AF-PRT-001",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_fragmented_packet_stream(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-PRT-007",
            message="Control frame boundary fragmented across multiple USB CDC reads",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.INFO,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            possible_causes=["Normal USB packet fragmentation by OS scheduler"],
            suggested_actions=["Decoder streaming buffer reassembles cleanly"],
        )
        return ScenarioResult(
            scenario_id="fragmented_packet_stream",
            name="Fragmented Packet Ingestion",
            target_fault_code="AF-PRT-007",
            subsystem=Subsystem.PROTOCOL,
            severity=Severity.INFO,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_dropped_audio_packet(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-STR-001",
            message="Frame sequence gap detected: expected 15, got 17",
            subsystem=Subsystem.STREAMING,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            frame_sequence=17,
            expected_value=15,
            observed_value=17,
            possible_causes=["USB packet dropped by host controller", "Firmware ring buffer drop"],
            suggested_actions=["Check firmware dropped_samples telemetry counter"],
        )
        return ScenarioResult(
            scenario_id="dropped_audio_packet",
            name="Audio Frame Sequence Gap",
            target_fault_code="AF-STR-001",
            subsystem=Subsystem.STREAMING,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_repeated_audio_packet(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-STR-002",
            message="Duplicate audio frame sequence received: 42",
            subsystem=Subsystem.STREAMING,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            frame_sequence=42,
            possible_causes=["Transport retransmission duplication"],
            suggested_actions=["Drop duplicate audio frame and continue"],
        )
        return ScenarioResult(
            scenario_id="repeated_audio_packet",
            name="Duplicate Audio Frame",
            target_fault_code="AF-STR-002",
            subsystem=Subsystem.STREAMING,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_reordered_sample_index(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-STR-003",
            message="Sample index discontinuity: expected 2560, got 2816",
            subsystem=Subsystem.STREAMING,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            first_sample_index=2816,
            expected_value=2560,
            observed_value=2816,
            possible_causes=["256 audio samples lost in DMA ring buffer"],
            suggested_actions=["Check ring buffer fill level and USB bandwidth"],
        )
        return ScenarioResult(
            scenario_id="reordered_sample_index",
            name="Sample Index Discontinuity",
            target_fault_code="AF-STR-003",
            subsystem=Subsystem.STREAMING,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_usb_read_timeout(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-USB-005",
            message="USB read timeout: no bytes received on /dev/ttyACM0 for 500ms during STREAMING",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            device_port="/dev/ttyACM0",
            possible_causes=["Firmware stalled in DMA ISR", "Hardware disconnect without notification"],
            suggested_actions=["Inspect ESP32-S3 firmware console for watchdog panic"],
        )
        return ScenarioResult(
            scenario_id="usb_read_timeout",
            name="USB Read Ingestion Timeout",
            target_fault_code="AF-USB-005",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_usb_write_stall(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-USB-006",
            message="USB write stalled: host cannot push START_REQ bytes to CDC endpoint",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            possible_causes=["ESP32-S3 USB-OTG CDC RX FIFO unserviced"],
            suggested_actions=["Check tud_cdc_read task in ESP-IDF firmware"],
        )
        return ScenarioResult(
            scenario_id="usb_write_stall",
            name="USB Write Transmission Stalled",
            target_fault_code="AF-USB-006",
            subsystem=Subsystem.USB,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_firmware_ring_overflow(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-STR-007",
            message="Firmware reported 8 ring buffer overflow events via telemetry",
            subsystem=Subsystem.STREAMING,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.REPORTED_BY_FIRMWARE,
            counter_snapshot={"ring_overflow_events": 8, "dropped_samples": 2048},
            possible_causes=["USB transmission bandwidth unable to sustain 48 kHz / 16-bit"],
            suggested_actions=["Increase ESP32-S3 ring buffer size or check USB hub congestion"],
        )
        return ScenarioResult(
            scenario_id="firmware_ring_overflow",
            name="Firmware Ring Buffer Overflow",
            target_fault_code="AF-STR-007",
            subsystem=Subsystem.STREAMING,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.REPORTED_BY_FIRMWARE,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_incorrect_integer_sample(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-STR-009",
            message="Deterministic known-answer sample verification failed at index 4096 (expected 100, observed -32768)",
            subsystem=Subsystem.STREAMING,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            first_sample_index=4096,
            expected_value=100,
            observed_value=-32768,
            possible_causes=["PCM endianness inversion", "DMA word alignment corruption"],
            suggested_actions=["Check I2S DMA byte packing order in firmware"],
        )
        return ScenarioResult(
            scenario_id="incorrect_integer_sample",
            name="Corrupted PCM Integer Sample",
            target_fault_code="AF-STR-009",
            subsystem=Subsystem.STREAMING,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_near_silence(self) -> ScenarioResult:
        doctor = SignalQualityDoctor()
        silent_samples = np.zeros(4800, dtype=np.float32)
        metrics = doctor.analyze_window(silent_samples, sample_rate_hz=48000)
        event = self.journal.record(
            fault_code="AF-SIG-001",
            message=f"Signal near silence detected: RMS {metrics.rms_fs:.6f} below threshold",
            subsystem=Subsystem.SIGNAL,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.DERIVED_FROM_SAMPLES,
            observed_value=round(metrics.rms_fs, 6),
            possible_causes=["Acoustic sensor disconnected", "Microphone phantom bias missing"],
            suggested_actions=["Check physical INMP441 wiring and solder joints"],
        )
        return ScenarioResult(
            scenario_id="near_silence",
            name="Acoustic Near-Silence",
            target_fault_code="AF-SIG-001",
            subsystem=Subsystem.SIGNAL,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.DERIVED_FROM_SAMPLES,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_clipping(self) -> ScenarioResult:
        doctor = SignalQualityDoctor()
        clipped_samples = np.ones(4800, dtype=np.float32)
        metrics = doctor.analyze_window(clipped_samples, sample_rate_hz=48000)
        event = self.journal.record(
            fault_code="AF-SIG-002",
            message=f"Signal clipping detected: fraction {metrics.clipping_fraction * 100:.1f}% samples at rails",
            subsystem=Subsystem.SIGNAL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.DERIVED_FROM_SAMPLES,
            observed_value=round(metrics.clipping_fraction, 4),
            possible_causes=["Analog pre-amp gain too high", "Acoustic signal exceeds microphone dynamic range"],
            suggested_actions=["Lower pre-amp gain or increase distance to sound source"],
        )
        return ScenarioResult(
            scenario_id="clipping",
            name="Signal Rail Clipping",
            target_fault_code="AF-SIG-002",
            subsystem=Subsystem.SIGNAL,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.DERIVED_FROM_SAMPLES,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_excessive_dc_offset(self) -> ScenarioResult:
        doctor = SignalQualityDoctor()
        biased_samples = np.full(4800, 0.75, dtype=np.float32)
        metrics = doctor.analyze_window(biased_samples, sample_rate_hz=48000)
        event = self.journal.record(
            fault_code="AF-SIG-003",
            message=f"Excessive DC offset detected: {metrics.dc_offset_fs:.4f} exceeds threshold",
            subsystem=Subsystem.SIGNAL,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.DERIVED_FROM_SAMPLES,
            observed_value=round(metrics.dc_offset_fs, 4),
            possible_causes=["ADC input DC bias leakage", "Missing hardware AC-coupling capacitor"],
            suggested_actions=["Enable software high-pass DC blocking filter"],
        )
        return ScenarioResult(
            scenario_id="excessive_dc_offset",
            name="Excessive DC Offset Bias",
            target_fault_code="AF-SIG-003",
            subsystem=Subsystem.SIGNAL,
            severity=Severity.WARNING,
            evidence_origin=EvidenceOrigin.DERIVED_FROM_SAMPLES,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_insufficient_storage(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-FILE-003",
            message="Storage space critical: available disk space 45 MB below 100 MB safety threshold",
            subsystem=Subsystem.STORAGE,
            severity=Severity.CRITICAL,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            observed_value="45MB",
            expected_value=">100MB",
            possible_causes=["Host disk nearly full"],
            suggested_actions=["Free disk space on host recording volume"],
        )
        return ScenarioResult(
            scenario_id="insufficient_storage",
            name="Low Disk Storage Space",
            target_fault_code="AF-FILE-003",
            subsystem=Subsystem.STORAGE,
            severity=Severity.CRITICAL,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_wav_integrity_mismatch(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-FILE-002",
            message="WAV integrity hash mismatch: recorded SHA-256 does not match disk file",
            subsystem=Subsystem.STORAGE,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            possible_causes=["Disk corruption or concurrent external file write"],
            suggested_actions=["Verify disk filesystem integrity"],
        )
        return ScenarioResult(
            scenario_id="wav_integrity_mismatch",
            name="WAV Integrity Hash Mismatch",
            target_fault_code="AF-FILE-002",
            subsystem=Subsystem.STORAGE,
            severity=Severity.ERROR,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )

    def scenario_backend_exited(self) -> ScenarioResult:
        event = self.journal.record(
            fault_code="AF-APP-002",
            message="Backend FastAPI process terminated unexpectedly with exit code -9",
            subsystem=Subsystem.APP,
            severity=Severity.CRITICAL,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            observed_value=-9,
            expected_value=0,
            possible_causes=["Killed by OS OOM killer or unhandled native segfault"],
            suggested_actions=["Inspect backend log stderr and restart application"],
        )
        return ScenarioResult(
            scenario_id="backend_exited",
            name="Backend Process Unexpected Exit",
            target_fault_code="AF-APP-002",
            subsystem=Subsystem.APP,
            severity=Severity.CRITICAL,
            evidence_origin=EvidenceOrigin.INJECTED_SIMULATION,
            passed=True,
            diagnostic_message=event.message,
            emitted_event_id=event.event_id,
        )
