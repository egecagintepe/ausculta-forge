"""AuscultaForge — Deterministic Root-Cause Correlation Engine.

Implements rule-based multi-event correlation across the entire lifecycle:
CASE A: USB Enumeration Absent -> Hardware bus power/cable/PHY issue. No HELLO attempted.
CASE B: USB Enumerated -> Port open fails -> OS port permission or competing process lock.
CASE C: Port Open Succeeds -> HELLO timeout -> Firmware protocol version or wrong USB port mode.
CASE D: HELLO & START Succeed -> CRC Failures -> Wire encoding or packet framing boundary fault.
CASE E: CRC Valid -> Stream Correct -> Signal Near Silence -> Electroacoustic sensor/coupling fault.
CASE F: Signal Data Healthy -> Recording Write Fails -> Host file system or disk capacity fault.

STRICT PRINCIPLE:
Never confidently assign root cause when evidence is ambiguous. Reports UNKNOWN / INCONCLUSIVE
with ranked hypotheses and explicit uncertainty markers.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .fault_catalog import Subsystem, Severity, EvidenceOrigin
from .event_model import DiagnosticEvent
from .flight_recorder import FlightRecorderJournal


@dataclass(slots=True)
class DiagnosticHypothesis:
    """Ranked troubleshooting hypothesis with uncertainty bounds."""
    rank: int
    title: str
    subsystem: Subsystem
    confidence: str  # "HIGH" | "MEDIUM" | "LOW" | "INCONCLUSIVE"
    evidence_summary: str
    confirmed_observations: list[str] = field(default_factory=list)
    unconfirmed_hypotheses: list[str] = field(default_factory=list)
    recommended_checklist: list[str] = field(default_factory=list)
    primary_owner: str = "Joint (Module B/C)"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["subsystem"] = self.subsystem.value
        return d


@dataclass(slots=True)
class CorrelationReport:
    """Deterministic root-cause correlation analysis report."""
    case_id: str
    summary: str
    active_incident_count: int
    ranked_hypotheses: list[DiagnosticHypothesis]
    evidence_demarcation: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "summary": self.summary,
            "active_incident_count": self.active_incident_count,
            "ranked_hypotheses": [h.to_dict() for h in self.ranked_hypotheses],
            "evidence_demarcation": self.evidence_demarcation,
        }


class RootCauseCorrelationEngine:
    """Lightweight rule-based correlation engine evaluating incident patterns."""

    def __init__(self, flight_recorder: FlightRecorderJournal) -> None:
        self.flight_recorder = flight_recorder

    def evaluate_incidents(
        self,
        current_port: Optional[str] = None,
        is_device_connected: bool = False,
        is_streaming: bool = False,
        is_recording: bool = False,
    ) -> CorrelationReport:
        """Analyze recent flight recorder events and correlate into root-cause report."""
        events = self.flight_recorder.get_recent_events(limit=50)
        fault_codes = {e.fault_code for e in events if e.event_status == "active"}

        evidence_demarcation = {
            "physical_device_connected": "YES" if is_device_connected else "NO",
            "active_streaming": "YES" if is_streaming else "NO",
            "active_recording": "YES" if is_recording else "NO",
            "active_fault_count": str(len(fault_codes)),
        }

        # ----------------------------------------------------------------------
        # CASE A: USB Enumeration Absent
        # ----------------------------------------------------------------------
        if "AF-USB-001" in fault_codes and not is_device_connected:
            return CorrelationReport(
                case_id="CASE_A_USB_ABSENT",
                summary="No AuscultaForge ESP32-S3 hardware detected on host USB bus.",
                active_incident_count=len(fault_codes),
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="USB Cable Lacks D+/D- Data Lines (Charge-Only Cable)",
                        subsystem=Subsystem.USB,
                        confidence="HIGH",
                        evidence_summary="Serial port list is empty or lacks Espressif CDC-ACM descriptor.",
                        confirmed_observations=["Zero compatible COM/serial ports enumerated on host OS bus."],
                        unconfirmed_hypotheses=[
                            "USB cable may be charge-only without data conductors.",
                            "Board may be unpowered or connected to auxiliary UART.",
                        ],
                        recommended_checklist=[
                            "1. Test USB cable with another known peripheral to verify data capability.",
                            "2. Ensure cable is connected to ESP32-S3 Native USB port (GPIO19/20) rather than UART.",
                            "3. Verify power LED is lit on the microcontroller PCB.",
                            "4. Inspect Windows Device Manager (Ports COM & LPT) or run lsusb on Linux.",
                        ],
                        primary_owner="Ege (Module C)",
                    ),
                    DiagnosticHypothesis(
                        rank=2,
                        title="Microcontroller in Reset or Unflashed Bootloader State",
                        subsystem=Subsystem.USB,
                        confidence="MEDIUM",
                        evidence_summary="Board is connected but fails to present CDC-ACM USB descriptors.",
                        confirmed_observations=["No CDC-ACM device descriptor matched."],
                        unconfirmed_hypotheses=["ESP32-S3 held in bootloader / download mode."],
                        recommended_checklist=[
                            "1. Press EN/RST button on ESP32-S3 board to restart firmware.",
                            "2. Verify ESP-IDF firmware binary was flashed successfully.",
                        ],
                        primary_owner="Ozan (Module B)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE B: USB Enumerated -> Port Open Fails (Access Denied / Busy)
        # ----------------------------------------------------------------------
        if "AF-USB-002" in fault_codes:
            return CorrelationReport(
                case_id="CASE_B_PORT_LOCKED",
                summary="USB port detected but exclusive access was denied by the operating system.",
                active_incident_count=len(fault_codes),
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="Serial Port Exclusively Locked by Competing Terminal",
                        subsystem=Subsystem.USB,
                        confidence="HIGH",
                        evidence_summary=f"OS returned PermissionError (Access Denied) when opening port {current_port or 'target'}.",
                        confirmed_observations=[f"Port {current_port or 'device'} open failed with access denied."],
                        unconfirmed_hypotheses=[
                            "PuTTY, Arduino IDE Serial Monitor, minicom, or idf.py monitor is running.",
                            "Previous instance of AuscultaForge backend process is still running.",
                        ],
                        recommended_checklist=[
                            "1. Close all open serial monitors, terminal emulators, or IDE debug consoles.",
                            "2. Open Task Manager and terminate any lingering 'python.exe' or 'uvicorn' processes.",
                            "3. On Linux, ensure user is a member of the 'dialout' group.",
                            "4. Re-poll device in AuscultaForge Device Center.",
                        ],
                        primary_owner="Ege (Module C)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE C: Port Open Succeeds -> HELLO Timeout / Nonce Mismatch
        # ----------------------------------------------------------------------
        if ("AF-PRT-004" in fault_codes or "AF-USB-005" in fault_codes or "AF-PRT-001" in fault_codes) and not is_streaming:
            return CorrelationReport(
                case_id="CASE_C_HELLO_HANDSHAKE_FAULT",
                summary="Serial port opened successfully but canonical B/C HELLO handshake failed.",
                active_incident_count=len(fault_codes),
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="Firmware Missing Canonical v0.1 Control Protocol Responder",
                        subsystem=Subsystem.PROTOCOL,
                        confidence="HIGH",
                        evidence_summary="Host sent 40-byte HELLO (0x01) but device timed out or sent unformatted data.",
                        confirmed_observations=["Port open succeeded; HELLO frame generated zero valid HELLO_ACK."],
                        unconfirmed_hypotheses=[
                            "Firmware is running legacy UART text loop instead of binary packet framing.",
                            "CDC-ACM RX interrupt callback is not polling incoming control packets.",
                        ],
                        recommended_checklist=[
                            "1. Verify firmware builds against canonical B/C v0.1 packet_framing.h.",
                            "2. Confirm firmware handles MSG_TYPE_HELLO_REQ (0x01) and returns 24-byte HELLO_ACK.",
                            "3. Check ESP32-S3 serial debug log for incoming byte receive confirmation.",
                        ],
                        primary_owner="Ozan (Module B)",
                    ),
                    DiagnosticHypothesis(
                        rank=2,
                        title="Cable Connected to Hardware UART Bridge Instead of Native USB",
                        subsystem=Subsystem.USB,
                        confidence="MEDIUM",
                        evidence_summary="Port opened at 115200 baud but device transmits bootloader text instead of binary frames.",
                        confirmed_observations=["Sync magic 0xAF53 not located in initial byte stream."],
                        unconfirmed_hypotheses=["USB plugged into CH340 / CP2102 UART chip instead of ESP32-S3 Native USB connector."],
                        recommended_checklist=[
                            "1. Switch USB cable to the board's second USB-C connector (Native USB-OTG).",
                        ],
                        primary_owner="Joint (Module B/C)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE D: HELLO & START Succeed -> CRC Failures / Sequence Gaps
        # ----------------------------------------------------------------------
        if "AF-PRT-002" in fault_codes or "AF-STR-001" in fault_codes or "AF-STR-009" in fault_codes:
            return CorrelationReport(
                case_id="CASE_D_CRC_STREAM_CORRUPT",
                summary="Stream is active but packet CRC integrity verification or sample continuity failed.",
                active_incident_count=len(fault_codes),
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="CRC-32 Calculation Range or Polynomial Inconsistency",
                        subsystem=Subsystem.PROTOCOL,
                        confidence="HIGH",
                        evidence_summary="IEEE 802.3 CRC-32 trailer does not match computed value over header bytes 0..35 + payload.",
                        confirmed_observations=["Packet magic 0xAF53 matched but CRC-32 check rejected frame."],
                        unconfirmed_hypotheses=[
                            "Firmware CRC-32 includes trailer bytes 36..39 or omits header fields.",
                            "Firmware uses non-standard initial seed or final XOR.",
                        ],
                        recommended_checklist=[
                            "1. Run firmware CRC-32 test vector: '123456789' must equal 0xCBF43926.",
                            "2. Ensure CRC buffer range is: compute_crc32(packet_bytes, 36 + payload_len).",
                            "3. Verify Little-Endian integer encoding of 4-byte CRC trailer.",
                        ],
                        primary_owner="Joint (Module B/C)",
                    ),
                    DiagnosticHypothesis(
                        rank=2,
                        title="Microcontroller FreeRTOS Buffer Starvation or DMA Overflow",
                        subsystem=Subsystem.STREAMING,
                        confidence="MEDIUM",
                        evidence_summary="Sequence IDs exhibit skips (AF-STR-001) or G1 deterministic values mismatch.",
                        confirmed_observations=["Sequence gap or sample index discontinuity detected."],
                        unconfirmed_hypotheses=["USB CDC transmission loop blocked waiting for endpoint availability."],
                        recommended_checklist=[
                            "1. Inspect STOP_ACK telemetry for dropped_samples and dma_overflow_events.",
                            "2. Increase intermediate ring buffer size in ESP32-S3 PSRAM.",
                        ],
                        primary_owner="Ozan (Module B)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE E: CRC Valid -> Stream Correct -> Signal Near Silence / Artifact
        # ----------------------------------------------------------------------
        if "AF-SIG-001" in fault_codes or "AF-SIG-007" in fault_codes or "AF-SIG-002" in fault_codes:
            return CorrelationReport(
                case_id="CASE_E_SIGNAL_ACOUSTIC_ANOMALY",
                summary="USB framing and CRC integrity are valid, but acoustic signal exhibits near-silence or clipping.",
                active_incident_count=len(fault_codes),
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="I2S Microphone Sensor Hardware Disconnection or Float",
                        subsystem=Subsystem.SIGNAL,
                        confidence="MEDIUM",
                        evidence_summary="Decoded stream is receiving continuous zeros or near-zero RMS (< -60 dBFS).",
                        confirmed_observations=["USB framing, sequence numbers, and CRC are 100% valid; audio samples are silent."],
                        unconfirmed_hypotheses=[
                            "MEMS microphone (INMP441) jumper wires disconnected (SD, BCLK, WS, VDD, GND).",
                            "I2S microphone channel selection (L/R pin) floating.",
                        ],
                        recommended_checklist=[
                            "1. Note: A silent digital signal is NOT a USB protocol fault; transport is working normally.",
                            "2. Check jumper wires from microphone breakout to ESP32-S3 GPIOs with a multimeter.",
                            "3. Verify sensor VDD is 3.3V and L/R pin is tied to GND (Left channel).",
                            "4. If using acoustic phantom, verify audio amplifier and exciter are powered on.",
                        ],
                        primary_owner="Joint (Module B/C)",
                    ),
                    DiagnosticHypothesis(
                        rank=2,
                        title="I2S Container Format Bit-Alignment Discrepancy",
                        subsystem=Subsystem.SIGNAL,
                        confidence="LOW",
                        evidence_summary="Sample values exhibit extreme rail-to-rail alternating signs (AF-SIG-007).",
                        confirmed_observations=["High zero-crossing density with large amplitude."],
                        unconfirmed_hypotheses=["I2S WS delay mismatch (Philips standard vs Left-Justified)."],
                        recommended_checklist=[
                            "1. Verify I2S slot configuration in ESP-IDF matches 24-bit in 32-bit container.",
                        ],
                        primary_owner="Ozan (Module B)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE F: Signal Healthy -> Recording Write Fails (Storage Fault)
        # ----------------------------------------------------------------------
        if "AF-FILE-001" in fault_codes or "AF-FILE-002" in fault_codes or "AF-FILE-003" in fault_codes:
            return CorrelationReport(
                case_id="CASE_F_STORAGE_FAULT",
                summary="Acoustic stream is healthy but session recording to disk failed.",
                active_incident_count=len(fault_codes),
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="Host Storage Partition Full or Write Permission Denied",
                        subsystem=Subsystem.STORAGE,
                        confidence="HIGH",
                        evidence_summary="SessionRecorder raised I/O error or SHA-256 hash mismatch.",
                        confirmed_observations=["File system operation failed on user-data directory."],
                        unconfirmed_hypotheses=["Disk full, disk quota exceeded, or read-only volume."],
                        recommended_checklist=[
                            "1. Free disk space on host storage drive.",
                            "2. Verify write permissions on AuscultaForge user-data directory.",
                        ],
                        primary_owner="Ege (Module C)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE NOMINAL: No Active Faults
        # ----------------------------------------------------------------------
        if not fault_codes:
            return CorrelationReport(
                case_id="CASE_NOMINAL_HEALTHY",
                summary="Workstation diagnostic systems nominal; zero active engineering faults.",
                active_incident_count=0,
                evidence_demarcation=evidence_demarcation,
                ranked_hypotheses=[
                    DiagnosticHypothesis(
                        rank=1,
                        title="System Operating Within Nominal Specifications",
                        subsystem=Subsystem.APP,
                        confidence="HIGH",
                        evidence_summary="No active faults recorded across USB, protocol, streaming, signal, or storage.",
                        confirmed_observations=["All diagnostic monitors healthy."],
                        unconfirmed_hypotheses=[],
                        recommended_checklist=["Proceed with standard acquisition, characterization, or G1 testing."],
                        primary_owner="Joint (Module B/C)",
                    ),
                ],
            )

        # ----------------------------------------------------------------------
        # CASE INCONCLUSIVE: Faults present but don't match specific signature
        # ----------------------------------------------------------------------
        return CorrelationReport(
            case_id="CASE_INCONCLUSIVE",
            summary=f"Active faults detected ({', '.join(sorted(fault_codes))}) with ambiguous correlation signature.",
            active_incident_count=len(fault_codes),
            evidence_demarcation=evidence_demarcation,
            ranked_hypotheses=[
                DiagnosticHypothesis(
                    rank=1,
                    title="Multiple Fault Indicators Require Manual Engineering Inspection",
                    subsystem=Subsystem.APP,
                    confidence="INCONCLUSIVE",
                    evidence_summary=f"Active fault codes: {', '.join(sorted(fault_codes))}",
                    confirmed_observations=[f"Fault codes {', '.join(sorted(fault_codes))} are active."],
                    unconfirmed_hypotheses=["Evidence insufficient to uniquely isolate single physical root cause."],
                    recommended_checklist=[
                        "1. Export Diagnostics Support Bundle for detailed offline timeline inspection.",
                        "2. Inspect Flight Recorder JSONL event journal.",
                        "3. Verify individual subsystem telemetry counters in Diagnostics Drawer.",
                    ],
                    primary_owner="Joint (Module B/C)",
                ),
            ],
        )
