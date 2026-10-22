"""AuscultaForge — Versioned Engineering Fault Catalog & Taxonomy.

Defines project-wide, stable, version-controlled fault definitions across:
- AF-USB-xxx: Hardware Discovery & USB CDC-ACM Transport
- AF-PRT-xxx: Canonical B/C Protocol v0.1 Handshake & Wire Contract
- AF-STR-xxx: Streaming Integrity & Firmware Telemetry Reconciliation
- AF-SIG-xxx: Signal Quality & Electroacoustic Diagnostics
- AF-DSP-xxx: Digital Signal Processing & Filtering
- AF-FILE-xxx: Session Storage & Recording Integrity
- AF-APP-xxx: Application, Host Process & WebSocket Transport

CRITICAL PRINCIPLES:
1. Hypotheses vs Confirmed Causes: Possible causes are strictly documented as hypotheses,
   never stated as proven physical hardware facts without verified evidence.
2. Severity vs Certainty: Severity indicates operational impact, not certainty of diagnosis.
3. Separation of Responsibilities: Clearly identifies primary debugging owner (Ozan: Module B,
   Ege: Module C, or Joint).
4. Physical Acceptance Demarcation: Declares whether fault affects G1 physical acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Diagnostic event and fault severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Subsystem(str, Enum):
    """Subsystems generating diagnostic events."""
    USB = "USB"
    PROTOCOL = "PROTOCOL"
    STREAMING = "STREAMING"
    SIGNAL = "SIGNAL"
    DSP = "DSP"
    STORAGE = "STORAGE"
    APP = "APP"


class EvidenceOrigin(str, Enum):
    """Strict ground-truth provenance of diagnostic evidence."""
    OBSERVED_HOST = "OBSERVED_HOST"                    # Host OS or transport API measurement
    REPORTED_BY_FIRMWARE = "REPORTED_BY_FIRMWARE"      # Telemetry or error frame sent by MCU
    DERIVED_FROM_SAMPLES = "DERIVED_FROM_SAMPLES"      # Mathematical calculation on raw samples
    INFERRED_HYPOTHESIS = "INFERRED_HYPOTHESIS"        # Diagnostic correlation hypothesis (unproven)
    INJECTED_SIMULATION = "INJECTED_SIMULATION"        # Simulated / synthetic bench test injection
    NOT_MEASURED = "NOT_MEASURED"                      # Quantity unobserved or sensor uncalibrated


@dataclass(slots=True, frozen=True)
class FaultDefinition:
    """Immutable specification of an engineering fault code."""
    code: str
    name: str
    subsystem: Subsystem
    severity: Severity
    detection_condition: str
    evidence_needed: str
    description_en: str
    description_tr: str
    possible_causes: tuple[str, ...]
    suggested_actions: tuple[str, ...]
    auto_recovery_permitted: bool
    affects_g1_acceptance: bool
    observable_without_hardware: bool
    emitting_component: str
    primary_owner: str  # "Ozan (Module B)", "Ege (Module C)", "Joint (Module B/C)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "subsystem": self.subsystem.value,
            "severity": self.severity.value,
            "detection_condition": self.detection_condition,
            "evidence_needed": self.evidence_needed,
            "description_en": self.description_en,
            "description_tr": self.description_tr,
            "possible_causes": list(self.possible_causes),
            "suggested_actions": list(self.suggested_actions),
            "auto_recovery_permitted": self.auto_recovery_permitted,
            "affects_g1_acceptance": self.affects_g1_acceptance,
            "observable_without_hardware": self.observable_without_hardware,
            "emitting_component": self.emitting_component,
            "primary_owner": self.primary_owner,
        }


# ==============================================================================
# CANONICAL FAULT CATALOG REPOSITORY
# ==============================================================================

_CATALOG_LIST: list[FaultDefinition] = [
    # --------------------------------------------------------------------------
    # Subsystem: USB Discovery & CDC-ACM Transport (AF-USB-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-USB-001",
        name="NO_COMPATIBLE_DEVICE_DETECTED",
        subsystem=Subsystem.USB,
        severity=Severity.WARNING,
        detection_condition="Host USB enumeration completed but no ports match AuscultaForge ESP32-S3 VID/PID or CDC descriptors.",
        evidence_needed="System enumerated serial port list with VID, PID, manufacturer, and product strings.",
        description_en="No AuscultaForge ESP32-S3 stethoscope probe was detected on host USB serial buses.",
        description_tr="Ana bilgisayar USB veriyolunda AuscultaForge ESP32-S3 stetoskop probu tespit edilemedi.",
        possible_causes=(
            "Hypothesis: USB cable is charge-only lacking D+/D- data conductors.",
            "Hypothesis: Cable plugged into UART/CH340 port instead of ESP32-S3 Native USB-OTG port.",
            "Hypothesis: ESP32-S3 unpowered or held in reset / bootloader state.",
            "Hypothesis: CDC-ACM driver missing or uninstalled on host OS.",
        ),
        suggested_actions=(
            "Verify USB cable supports high-speed data transfer (test with a known peripheral).",
            "Ensure the USB cable is connected to the Native USB port (GPIO19/20) rather than auxiliary UART.",
            "Check Windows Device Manager (Ports COM & LPT) or run lsusb / dmesg on Linux.",
            "Verify power LED is illuminated on the ESP32-S3 N16R8 board.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbDiscoveryDoctor",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-USB-002",
        name="PORT_ACCESS_DENIED_OR_BUSY",
        subsystem=Subsystem.USB,
        severity=Severity.ERROR,
        detection_condition="Attempt to open the enumerated serial port failed with PermissionError or Access Denied (error code 5 or 13).",
        evidence_needed="Target COM port name and OS system error message / errno.",
        description_en="The target serial port exists but access was denied because another process has opened it exclusively.",
        description_tr="Hedef seri port mevcut fakat başka bir işlem portu kilitlediği için erişim reddedildi.",
        possible_causes=(
            "Hypothesis: Serial terminal monitor (PuTTY, Arduino IDE, minicom, ESP-IDF monitor) is holding port open.",
            "Hypothesis: Insufficient user privileges (e.g. dialout group membership missing on Linux).",
            "Hypothesis: Previous instance of AuscultaForge backend did not release COM port before terminating.",
        ),
        suggested_actions=(
            "Close any open serial monitors, IDEs, or terminal debuggers accessing the device port.",
            "On Linux, ensure user is a member of the 'dialout' or 'uucp' group.",
            "Restart AuscultaForge desktop backend to release orphaned port handles.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbCdcAcmAdapter",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-USB-003",
        name="PORT_OPEN_FAILED",
        subsystem=Subsystem.USB,
        severity=Severity.ERROR,
        detection_condition="Serial port open operation failed due to hardware or driver initialization error.",
        evidence_needed="Port name, configured baud rate, and exception traceback.",
        description_en="Failed to open connection to the selected serial port.",
        description_tr="Seçilen seri porta bağlantı açılamadı.",
        possible_causes=(
            "Hypothesis: Device disconnected precisely during the port open system call.",
            "Hypothesis: Corrupted USB CDC-ACM driver state in operating system kernel.",
            "Hypothesis: Physical signal integrity fault causing USB PHY reset.",
        ),
        suggested_actions=(
            "Unplug and reconnect the USB probe.",
            "Verify port name has not shifted to a different COM index.",
            "Inspect system dmesg or Windows Event Viewer for USB bus reset events.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbCdcAcmAdapter",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-USB-004",
        name="UNEXPECTED_DISCONNECT",
        subsystem=Subsystem.USB,
        severity=Severity.ERROR,
        detection_condition="Transport read or write raised SerialException or port vanished during active connection.",
        evidence_needed="Session ID, last successful packet sequence, and transport error message.",
        description_en="The physical USB probe disconnected unexpectedly during active operation.",
        description_tr="Fiziksel USB probu aktif çalışma sırasında beklenmedik şekilde koptu.",
        possible_causes=(
            "Hypothesis: Mechanical cable tug or intermittent USB-C connector contact.",
            "Hypothesis: ESP32-S3 brownout reset triggered by current spike or unstable 5V USB rail.",
            "Hypothesis: ESP-IDF firmware panic or watchdog timer expiration causing MCU reboot.",
        ),
        suggested_actions=(
            "Inspect physical cable mechanical strain relief and USB-C port tightness.",
            "Check ESP32-S3 serial console log for Brownout detector or Guru Meditation Error.",
            "Safely stop active session and trigger re-enumeration scan.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbCdcAcmAdapter",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-USB-005",
        name="USB_READ_TIMEOUT",
        subsystem=Subsystem.USB,
        severity=Severity.WARNING,
        detection_condition="Transport read returned 0 bytes continuously for duration exceeding configured read timeout during streaming.",
        evidence_needed="Elapsed silence duration, active state, and last packet arrival timestamp.",
        description_en="Transport read timed out with zero bytes received during active streaming.",
        description_tr="Aktif akış sırasında transport okuması zaman aşımına uğradı, veri gelmedi.",
        possible_causes=(
            "Hypothesis: Firmware audio acquisition task stalled or halted.",
            "Hypothesis: USB CDC-ACM endpoint FIFO stalled or blocked waiting for host token.",
            "Hypothesis: Host USB hub controller entered selective suspend power-saving state.",
        ),
        suggested_actions=(
            "Verify firmware acquisition loop is actively scheduling and filling USB endpoints.",
            "Disable USB selective suspend in Windows Power Options.",
            "Check whether STOP request was missed or firmware entered halt state.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbCdcAcmAdapter",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-USB-006",
        name="USB_WRITE_STALLED",
        subsystem=Subsystem.USB,
        severity=Severity.ERROR,
        detection_condition="Attempt to transmit control frame (HELLO, START, STOP) blocked or timed out on write.",
        evidence_needed="Control message opcode, payload byte length, and timeout duration.",
        description_en="Host transmission of control command to device timed out or stalled.",
        description_tr="Cihaza kontrol komutu gönderimi zaman aşımına uğradı veya kilitlendi.",
        possible_causes=(
            "Hypothesis: ESP32-S3 CDC-ACM RX FIFO buffer full without task reading incoming data.",
            "Hypothesis: Hardware flow control (DTR/RTS) mismatch or unasserted.",
            "Hypothesis: USB host endpoint controller driver pipe stalled.",
        ),
        suggested_actions=(
            "Ensure firmware CDC-ACM read callback is actively flushing incoming commands.",
            "Verify DTR and RTS lines are asserted by host serial adapter.",
            "Close and re-open serial transport.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbCdcAcmAdapter",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-USB-007",
        name="USB_PORT_REENUMERATED",
        subsystem=Subsystem.USB,
        severity=Severity.INFO,
        detection_condition="A serial port previously disconnected or absent reappeared on the host bus with valid descriptors.",
        evidence_needed="Previous port identifier, new port identifier, and descriptor match.",
        description_en="USB hardware probe was re-detected and re-enumerated on the host system.",
        description_tr="USB donanım probu ana sistemde yeniden tespit edildi ve numaralandırıldı.",
        possible_causes=(
            "Hypothesis: User plugged device back into USB port.",
            "Hypothesis: MCU completed software reboot or watchdog restart.",
        ),
        suggested_actions=(
            "Perform automatic or manual HELLO handshake to verify operational readiness.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="UsbDiscoveryDoctor",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-USB-008",
        name="SERIAL_DEPENDENCY_UNAVAILABLE",
        subsystem=Subsystem.USB,
        severity=Severity.ERROR,
        detection_condition="Python 'serial' (pyserial) module failed to import when opening CDC-ACM port.",
        evidence_needed="Python interpreter path and ImportError message.",
        description_en="Required serial communication library 'pyserial' is not installed in current Python environment.",
        description_tr="Gerekli seri iletişim kütüphanesi 'pyserial' mevcut Python ortamında kurulu değil.",
        possible_causes=(
            "Hypothesis: Backend running in virtualenv where pyserial was not installed.",
        ),
        suggested_actions=(
            "Run 'pip install pyserial' in active Python virtual environment.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="UsbCdcAcmAdapter",
        primary_owner="Ege (Module C)",
    ),

    # --------------------------------------------------------------------------
    # Subsystem: Canonical B/C Protocol v0.1 (AF-PRT-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-PRT-001",
        name="SYNC_NOT_FOUND",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="Decoder scanned buffer without locating 2-byte sync magic (0xAF 0x53).",
        evidence_needed="Byte count scanned, leading candidate bytes, and decoder discard count.",
        description_en="Frame synchronization prefix 0xAF53 not found in received byte stream.",
        description_tr="Alınan bayt akışında çerçeve senkronizasyon öneki 0xAF53 bulunamadı.",
        possible_causes=(
            "Hypothesis: Firmware transmitting unformatted raw text, boot messages, or printf output over CDC port.",
            "Hypothesis: Baud rate mismatch on UART bridge or bit slippage.",
            "Hypothesis: Host stream offset desynchronized following lost bytes.",
        ),
        suggested_actions=(
            "Ensure ESP32-S3 firmware disables UART debug logging on the CDC-ACM endpoint.",
            "Verify all packets begin with canonical 2-byte magic prefix 0xAF53.",
            "Allow decoder sliding window to discard unaligned noise bytes.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-PRT-002",
        name="CRC_MISMATCH",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="Computed IEEE 802.3 CRC-32 on 36-byte header and payload does not equal received 4-byte CRC-32 trailer.",
        evidence_needed="Received packet sequence, expected CRC, computed CRC, and payload length.",
        description_en="Packet CRC-32 integrity verification failed; data corrupted or improperly calculated.",
        description_tr="Paket CRC-32 bütünlük doğrulaması başarısız; veri bozuk veya yanlış hesaplanmış.",
        possible_causes=(
            "Hypothesis: Firmware CRC calculation uses different polynomial or seed (canonical requires polynomial 0xEDB88320, init 0xFFFFFFFF, final XOR 0xFFFFFFFF).",
            "Hypothesis: Payload bytes modified or truncated in transit.",
            "Hypothesis: Firmware CRC covers incorrect byte range (must cover bytes 0..35 of header + payload).",
        ),
        suggested_actions=(
            "Verify firmware CRC-32 implementation matches canonical test vector: '123456789' -> 0xCBF43926.",
            "Verify CRC header range covers bytes 0..35 and excludes the CRC field itself (bytes 36..39).",
            "Inspect physical USB cable and PCB routing for signal noise.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-PRT-003",
        name="PROTOCOL_VERSION_MISMATCH",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.CRITICAL,
        detection_condition="Device reported protocol major/minor version incompatible with host canonical v0.1.",
        evidence_needed="Host protocol version, device reported protocol version, and device firmware version.",
        description_en="Device protocol version is incompatible with host canonical B/C v0.1 specification.",
        description_tr="Cihaz protokol sürümü, ana bilgisayar kanonik B/C v0.1 spesifikasyonu ile uyumsuz.",
        possible_causes=(
            "Hypothesis: Stale or experimental firmware branch flashed to ESP32-S3.",
            "Hypothesis: Host software updated without corresponding firmware build.",
        ),
        suggested_actions=(
            "Flash firmware with canonical v0.1 protocol implementation.",
            "Confirm protocol_major==0 and protocol_minor==1 in HELLO_ACK response.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-PRT-004",
        name="HELLO_NONCE_MISMATCH",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="HELLO_ACK payload returned a nonce different from the random 32-bit nonce sent in HELLO request.",
        evidence_needed="Sent host nonce (uint32) and received device nonce (uint32).",
        description_en="HELLO handshake nonce mismatch; device echoed incorrect or stale transaction token.",
        description_tr="HELLO el sıkışması nonce uyuşmazlığı; cihaz yanlış veya eski işlem anahtarı döndürdü.",
        possible_causes=(
            "Hypothesis: Firmware echoed a hardcoded nonce constant instead of copying request nonce.",
            "Hypothesis: Delayed response from an earlier abandoned handshake attempt.",
        ),
        suggested_actions=(
            "Ensure firmware copies incoming hello_req.nonce directly into hello_ack.nonce.",
            "Flush input buffer before transmitting HELLO request.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-PRT-005",
        name="START_CONFIGURATION_REJECTED",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.CRITICAL,
        detection_condition="Device rejected START command with non-zero start_status in START_ACK payload.",
        evidence_needed="Sent configuration (sample rate, profile, block size) and received start_status code.",
        description_en="Device firmware rejected requested stream acquisition configuration.",
        description_tr="Cihaz yazılımı talep edilen akış konfigürasyonunu reddetti.",
        possible_causes=(
            "Hypothesis: Requested sample rate (e.g. 48000 Hz) not supported by firmware I2S clock tree.",
            "Hypothesis: DMA buffer allocation failed on microcontroller due to internal heap exhaustion.",
            "Hypothesis: Microcontroller already in active STREAMING state.",
        ),
        suggested_actions=(
            "Inspect start_status code in START_ACK payload (1=Rate, 2=Channels, 3=Format, 4=Memory, 5=State).",
            "Send STOP command to force idle state before retrying START.",
            "Verify ESP32-S3 I2S APLL clock configuration for 48 kHz operation.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-PRT-006",
        name="SESSION_ID_MISMATCH",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="Received AUDIO frame header contains a session_id differing from the active session.",
        evidence_needed="Expected session ID, received packet session ID, and packet sequence ID.",
        description_en="Packet session ID does not match active host session; data may belong to a prior session.",
        description_tr="Paket oturum kimliği aktif oturum ile uyuşmuyor; veri eski bir oturuma ait olabilir.",
        possible_causes=(
            "Hypothesis: Stale audio frames buffered in USB hardware FIFO from previous un-flushed session.",
            "Hypothesis: Firmware did not update its internal session_id variable upon START.",
        ),
        suggested_actions=(
            "Ensure firmware updates its session_id register upon parsing START command.",
            "Host discards stale frames until session_id aligns.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-PRT-007",
        name="CONTROL_FRAME_MALFORMED",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="Control frame payload length does not match exact canonical specification for opcode.",
        evidence_needed="Message type opcode, expected length, and actual decoded payload length.",
        description_en="Control response frame received with incorrect wire payload length.",
        description_tr="Kontrol yanıt çerçevesi geçersiz yük uzunluğu ile alındı.",
        possible_causes=(
            "Hypothesis: Struct packing alignment or padding discrepancy between GCC (ESP-IDF) and Python.",
            "Hypothesis: Firmware omitted fields (e.g. START_ACK must be 32 bytes, HELLO_ACK 24 bytes, STATUS 72 bytes).",
        ),
        suggested_actions=(
            "Verify all protocol structures use __attribute__((packed)) in C firmware.",
            "Consult docs/engineering/protocol/B_C_CANONICAL_PROTOCOL_V0_1.md for exact wire byte offsets.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-PRT-008",
        name="STOP_ACK_MISSING",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.WARNING,
        detection_condition="Host sent STOP command but device did not return STOP_ACK within configured timeout.",
        evidence_needed="Session ID, STOP command timestamp, and timeout duration.",
        description_en="Device did not return STOP_ACK confirmation frame following STOP command.",
        description_tr="Cihaz STOP komutunun ardından STOP_ACK onay çerçevesi döndürmedi.",
        possible_causes=(
            "Hypothesis: Firmware crashed or hung during acquisition teardown.",
            "Hypothesis: STOP command lost in unread USB buffer.",
            "Hypothesis: Device disconnected immediately when STOP was issued.",
        ),
        suggested_actions=(
            "Inspect ESP32-S3 serial monitor for crash during i2s_channel_disable() or usb teardown.",
            "Host forces session closure with reconciliation marked as UNCONFIRMED.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-PRT-009",
        name="FIRMWARE_ERROR_REPORTED",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="Device transmitted an ERROR notification frame (0x08) with numeric error code.",
        evidence_needed="Raw firmware error_code (uint32) and error_context (uint32).",
        description_en="Firmware emitted an explicit hardware or software error notification frame.",
        description_tr="Aygıt yazılımı açık bir donanım veya yazılım hata bildirim çerçevesi iletti.",
        possible_causes=(
            "Hypothesis: I2S peripheral error, DMA allocation failure, or sensor communication fault on MCU.",
        ),
        suggested_actions=(
            "Map numeric error code against Module B firmware error documentation.",
            "Check ESP-IDF log output for detailed kernel diagnostic message.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-PRT-010",
        name="CAPABILITY_NEGOTIATION_FAILED",
        subsystem=Subsystem.PROTOCOL,
        severity=Severity.ERROR,
        detection_condition="Device reported capabilities do not satisfy minimum host acquisition requirements.",
        evidence_needed="Required sample rates, channel count, and reported capability bitmask.",
        description_en="Device capabilities do not satisfy minimum host workstation acquisition requirements.",
        description_tr="Cihaz yetenekleri ana bilgisayar asgari kayıt gereksinimlerini karşılamıyor.",
        possible_causes=(
            "Hypothesis: Firmware does not report support for 48 kHz mono 24-bit PCM.",
        ),
        suggested_actions=(
            "Update firmware capabilities bitmask in HELLO_ACK response.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Joint (Module B/C)",
    ),

    # --------------------------------------------------------------------------
    # Subsystem: Streaming Integrity & Firmware Telemetry (AF-STR-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-STR-001",
        name="FRAME_SEQUENCE_GAP",
        subsystem=Subsystem.STREAMING,
        severity=Severity.WARNING,
        detection_condition="Audio frame sequence_id skipped one or more expected monotonic increments (seq > expected_seq).",
        evidence_needed="Expected sequence ID, observed sequence ID, and calculated skipped frame count.",
        description_en="Audio frame sequence gap detected; one or more USB packets were dropped in transit.",
        description_tr="Ses çerçevesi sıra atlaması tespit edildi; bir veya daha fazla USB paketi kayboldu.",
        possible_causes=(
            "Hypothesis: Microcontroller dropped packet due to USB CDC-ACM write timeout or buffer overflow.",
            "Hypothesis: Host USB hub controller dropped packets due to bus congestion.",
            "Hypothesis: Host process descheduled by OS for excessive duration.",
        ),
        suggested_actions=(
            "Reconcile against STOP_ACK dropped_samples telemetry to identify if loss occurred on MCU or host bus.",
            "Increase microcontroller ring buffer capacity or streamline CDC write loop.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-STR-002",
        name="DUPLICATE_AUDIO_FRAME",
        subsystem=Subsystem.STREAMING,
        severity=Severity.WARNING,
        detection_condition="Audio frame received with sequence_id identical to previously processed frame.",
        evidence_needed="Repeated sequence ID and timestamp comparison.",
        description_en="Duplicate audio frame received with an already-processed sequence number.",
        description_tr="Daha önce işlenmiş sıra numarasına sahip yinelenen ses çerçevesi alındı.",
        possible_causes=(
            "Hypothesis: Firmware retransmitted unacknowledged packet inappropriately.",
            "Hypothesis: Sequence ID counter rollover or loopback test buffer duplication.",
        ),
        suggested_actions=(
            "Ensure firmware monotonically increments sequence_id for every emitted packet without retransmission.",
            "Host decoder drops duplicate packet to prevent audio timeline distortion.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-STR-003",
        name="SAMPLE_INDEX_DISCONTINUITY",
        subsystem=Subsystem.STREAMING,
        severity=Severity.WARNING,
        detection_condition="Packet sample_index_start does not equal previous (sample_index_start + sample_count).",
        evidence_needed="Expected sample index start, observed index start, and gap size in samples.",
        description_en="Sample index counter discontinuity detected across packet boundaries.",
        description_tr="Paket sınırları arasında örnek dizin sayacı süreksizliği tespit edildi.",
        possible_causes=(
            "Hypothesis: Firmware I2S DMA ISR dropped samples before framing into USB packets.",
            "Hypothesis: Packet loss on USB transport occurred.",
        ),
        suggested_actions=(
            "Verify sample index calculation in firmware: next_index = prev_index + sample_count.",
            "Check for DMA FIFO underflow / overflow events in microcontroller telemetry.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-STR-004",
        name="TIMESTAMP_REGRESSION",
        subsystem=Subsystem.STREAMING,
        severity=Severity.WARNING,
        detection_condition="Packet timestamp_us is less than the timestamp_us of the preceding packet.",
        evidence_needed="Previous timestamp_us, current timestamp_us, and delta.",
        description_en="Microcontroller hardware timestamp regression detected (non-monotonic timebase).",
        description_tr="Mikrodenetleyici donanım zaman damgasında gerileme tespit edildi (monoton olmayan zaman).",
        possible_causes=(
            "Hypothesis: Microcontroller esp_timer or 32-bit microsecond counter rolled over.",
            "Hypothesis: Packets reordered in multi-threaded host queue.",
        ),
        suggested_actions=(
            "Use 64-bit microsecond integer arithmetic for hardware timestamping on ESP32-S3.",
            "Verify single-producer single-consumer FIFO ordering.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="StreamingProtocolDecoder",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-STR-005",
        name="MCU_SAMPLE_DROP_REPORTED",
        subsystem=Subsystem.STREAMING,
        severity=Severity.ERROR,
        detection_condition="Microcontroller reported dropped_samples > 0 in STATUS or STOP_ACK telemetry.",
        evidence_needed="Telemetry dropped_samples count, generated_samples, and fully_queued_samples.",
        description_en="Microcontroller firmware explicitly reported dropped audio samples due to internal buffer saturation.",
        description_tr="Mikrodenetleyici yazılımı dahili tampon dolması nedeniyle düşürülen örnekler bildirdi.",
        possible_causes=(
            "Hypothesis: USB CDC-ACM link throughput lower than audio generation rate (48k * 4B = 192 kB/s).",
            "Hypothesis: FreeRTOS task starvation or excessive interrupt latency on MCU.",
        ),
        suggested_actions=(
            "Confirm USB bulk endpoint packet size is 512 bytes (High-Speed CDC-ACM).",
            "Increase FreeRTOS stream task priority or enlarge ring buffer in SRAM.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-STR-006",
        name="DMA_OVERFLOW_REPORTED",
        subsystem=Subsystem.STREAMING,
        severity=Severity.ERROR,
        detection_condition="Microcontroller reported dma_overflow_events > 0 in telemetry.",
        evidence_needed="Telemetry dma_overflow_events count.",
        description_en="ESP32-S3 I2S DMA descriptor ring buffer overflowed; samples lost at hardware ADC interface.",
        description_tr="ESP32-S3 I2S DMA tanımlayıcı tamponu taştı; donanım ADC arayüzünde örnek kaybı oluştu.",
        possible_causes=(
            "Hypothesis: DMA descriptors too small or too few (e.g. fewer than 4 descriptors).",
            "Hypothesis: Interrupt handler execution delayed by higher-priority interrupts.",
        ),
        suggested_actions=(
            "Increase I2S DMA descriptor count to at least 8 with 512-byte buffer length in ESP-IDF.",
            "Verify I2S ISR is placed in IRAM.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-STR-007",
        name="RING_BUFFER_OVERFLOW_REPORTED",
        subsystem=Subsystem.STREAMING,
        severity=Severity.ERROR,
        detection_condition="Microcontroller reported ring_overflow_events > 0 in telemetry.",
        evidence_needed="Telemetry ring_overflow_events count.",
        description_en="Firmware inter-task ring buffer overflowed before USB packetization.",
        description_tr="Yazılım görevler arası halka tamponu USB paketleme öncesinde taştı.",
        possible_causes=(
            "Hypothesis: Intermediate ring buffer size insufficient to absorb USB transmission bursts.",
        ),
        suggested_actions=(
            "Allocate larger ring buffer in ESP32-S3 external PSRAM (8 MB available on N16R8).",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Ozan (Module B)",
    ),
    FaultDefinition(
        code="AF-STR-008",
        name="SUSTAINED_USB_BACKPRESSURE",
        subsystem=Subsystem.STREAMING,
        severity=Severity.WARNING,
        detection_condition="Microcontroller reported usb_partial_write_events > 50 or host dropped display frames continuously.",
        evidence_needed="Partial write count, dropped display frames, and host queue depth.",
        description_en="Sustained USB transport backpressure detected between microcontroller and host.",
        description_tr="Mikrodenetleyici ile ana bilgisayar arasında sürekli USB geri basıncı tespit edildi.",
        possible_causes=(
            "Hypothesis: Host USB driver scheduling delay or USB controller bandwidth saturation.",
        ),
        suggested_actions=(
            "Verify host ingestion worker runs on high-priority asynchronous executor.",
            "Ensure host display decimation drops UI display frames rather than stream audio frames.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-STR-009",
        name="G1_SAMPLE_MISMATCH",
        subsystem=Subsystem.STREAMING,
        severity=Severity.CRITICAL,
        detection_condition="Decoded sample value does not match deterministic G1 generator x[n] = (n * 37) & 0xFFFFFF.",
        evidence_needed="Sample index n, expected value, observed value, and mismatch count.",
        description_en="Physical G1 acceptance test failed: decoded sample value differs from deterministic reference.",
        description_tr="Fiziksel G1 kabul testi başarısız: çözümlenen örnek değeri referanstan farklı.",
        possible_causes=(
            "Hypothesis: Endianness mismatch in 24-bit PCM payload unpacking.",
            "Hypothesis: Bit-shifting or container sign-extension error in firmware or host decoder.",
            "Hypothesis: Firmware generator formula discrepancy.",
        ),
        suggested_actions=(
            "Confirm firmware generator uses exact formula: x[n] = (n * 37) & 0x00FFFFFF.",
            "Verify 24-bit Little-Endian packing: byte0 = x & 0xFF, byte1 = (x >> 8) & 0xFF, byte2 = (x >> 16) & 0xFF.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="VerifyG1Bringup",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-STR-010",
        name="FINAL_TELEMETRY_MISMATCH",
        subsystem=Subsystem.STREAMING,
        severity=Severity.ERROR,
        detection_condition="Reconciliation between host-received samples and MCU-reported generated_samples shows discrepancy > 0.",
        evidence_needed="Host received sample count, MCU generated sample count, and discrepancy delta.",
        description_en="End-of-session telemetry reconciliation failed: host sample count does not match MCU total.",
        description_tr="Oturum sonu telemetri mutabakatı başarısız: ana bilgisayar örnek sayısı MCU toplamı ile eşleşmiyor.",
        possible_causes=(
            "Hypothesis: Trailing packets remained in USB pipe when STOP_ACK was transmitted.",
            "Hypothesis: Firmware telemetry counter incremented before hardware transmit confirmation.",
        ),
        suggested_actions=(
            "Ensure firmware flushes all queued audio packets before transmitting STOP_ACK.",
            "Inspect STOP_ACK generated_samples vs audio_bytes_queued.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="CanonicalProtocolSession",
        primary_owner="Joint (Module B/C)",
    ),

    # --------------------------------------------------------------------------
    # Subsystem: Signal Quality & Acoustic Diagnostics (AF-SIG-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-SIG-001",
        name="NEAR_SILENCE_DETECTED",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.WARNING,
        detection_condition="Signal RMS is below -60 dBFS (< 0.001 FS) for duration exceeding observation window (>= 2.0 s).",
        evidence_needed="Calculated RMS value, threshold (-60 dBFS), and silence duration in seconds.",
        description_en="Signal is near absolute silence; acoustic energy is below expected baseline noise floor.",
        description_tr="Sinyal neredeyse tamamen sessiz; akustik enerji beklenen taban gürültüsünün altında.",
        possible_causes=(
            "Hypothesis: Acoustic microphone sensor (INMP441 / PUI) unpowered or I2S SD pin disconnected.",
            "Hypothesis: I2S clock (BCLK/WS) lines disconnected or floating.",
            "Hypothesis: Synthetic test generator paused or generating zeros.",
            "Note: Does NOT prove physical microphone hardware fault without hardware inspection.",
        ),
        suggested_actions=(
            "Inspect physical jumper wires connecting microphone to ESP32-S3 (BCLK, WS, SD, VDD, GND).",
            "Verify sensor VDD is 3.3V and GND is shared with microcontroller.",
            "If using acoustic phantom, verify exciter amplifier power is on.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="SignalQualityDoctor",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-SIG-002",
        name="CLIPPING_DETECTED",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.WARNING,
        detection_condition="Sample amplitude reaches or exceeds 0.999 digital full-scale for more than 0.1% of window.",
        evidence_needed="Saturation hit count, window sample count, and fraction of saturated samples.",
        description_en="Digital rail clipping detected; samples are reaching normalized full-scale ceiling (+/- 1.0).",
        description_tr="Dijital sınır kırpılması tespit edildi; örnekler tam ölçek tavanına (+/- 1.0) ulaşıyor.",
        possible_causes=(
            "Hypothesis: Acoustic chestpiece coupled to excessively loud source causing sensor overload.",
            "Hypothesis: Mechanical handling noise, friction, or tapping directly against microphone diaphragm.",
            "Hypothesis: Digital bit-shift error in firmware multiplying samples by excessive factor.",
        ),
        suggested_actions=(
            "Ensure chestpiece is held steady against auscultation surface without rubbing.",
            "Verify firmware bit-shift logic (24-bit sensor data in 32-bit slot: sign-extend 24-bit signed integer).",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="SignalQualityDoctor",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-SIG-003",
        name="EXCESSIVE_DC_COMPONENT",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.WARNING,
        detection_condition="Mean sample value (DC offset) exceeds 10% of normalized digital full-scale (|mean| > 0.10).",
        evidence_needed="Calculated mean DC value and normalized ratio.",
        description_en="Excessive DC bias offset detected in raw acoustic waveform.",
        description_tr="Ham akustik dalga biçiminde aşırı doğru akım (DC) kayması tespit edildi.",
        possible_causes=(
            "Hypothesis: MEMS microphone DC offset drift or ADC reference voltage imbalance.",
            "Hypothesis: Unsigned integer erroneously converted to signed PCM without subtracting midpoint.",
        ),
        suggested_actions=(
            "Inspect raw integer sample bit representation for signed two's-complement formatting.",
            "Apply digital high-pass filter (Butterworth 20 Hz) to eliminate DC baseline wander.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="SignalQualityDoctor",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-SIG-004",
        name="SUSPECTED_MAINS_INTERFERENCE",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.INFO,
        detection_condition="Welch PSD peak in 49–51 Hz (or 99–101 Hz) band exceeds local background noise floor by > 18 dB.",
        evidence_needed="PSD peak frequency, peak power in dB, and broadband median power.",
        description_en="Prominent tonal component detected near 50 Hz power-mains fundamental.",
        description_tr="50 Hz şebeke frekansı civarında belirgin tek tonlu bileşen tespit edildi.",
        possible_causes=(
            "Hypothesis: Electromagnetic coupling from mains AC power adapter or nearby unshielded cabling.",
            "Hypothesis: Genuine physiological signal component (heart sound S1/S2 fundamental overlaps 40-60 Hz).",
            "Note: A 50 Hz peak alone does NOT prove mains interference without comparative shielding check.",
        ),
        suggested_actions=(
            "Test operation on battery power / disconnected laptop charger to determine if peak vanishes.",
            "Ensure sensor ground shielding is properly bonded to sensor chassis.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="SignalQualityDoctor",
        primary_owner="Joint (Module B/C)",
    ),
    FaultDefinition(
        code="AF-SIG-005",
        name="LOW_RELATIVE_SIGNAL_LEVEL",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.INFO,
        detection_condition="Signal RMS is between -60 dBFS and -40 dBFS, below recommended operational headroom (0.01 to 0.50 FS).",
        evidence_needed="Calculated RMS and peak utilization fraction.",
        description_en="Signal level is low relative to digital full-scale headroom.",
        description_tr="Sinyal seviyesi dijital tam ölçeğe göre düşük seviyede.",
        possible_causes=(
            "Hypothesis: Light contact pressure on auscultation surface.",
            "Hypothesis: Thick acoustic attenuation layer (heavy clothing) between sensor and subject.",
        ),
        suggested_actions=(
            "Ensure firm, uniform acoustic contact between stethoscope diaphragm and surface.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="SignalQualityDoctor",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-SIG-006",
        name="REFERENCE_COMPARISON_FAILED",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.WARNING,
        detection_condition="System ID or Phantom coherence gamma_xy^2 in excited band drops below 0.60.",
        evidence_needed="Excited frequency range, mean coherence, and stimulus SNR.",
        description_en="Stimulus-response coherence is below validation threshold during acoustic characterization.",
        description_tr="Akustik karakterizasyon sırasında uyaran-yanıt tutarlılığı doğrulama eşiğinin altında.",
        possible_causes=(
            "Hypothesis: Extraneous ambient acoustic noise contaminating calibration sweep.",
            "Hypothesis: Non-linear distortion in acoustic transducer or mechanical loose fit.",
        ),
        suggested_actions=(
            "Repeat phantom characterization sweep in a quiet acoustic environment.",
            "Check physical coupling between acoustic exciter and stethoscope chestpiece.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="SystemIdDoctor",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-SIG-007",
        name="POSSIBLE_PCM_ALIGNMENT_MISMATCH",
        subsystem=Subsystem.SIGNAL,
        severity=Severity.WARNING,
        detection_condition="Sample values exhibit periodic alternating sign flips (+/- 2^23) characteristic of container bit offset.",
        evidence_needed="Alternating sample values, sample bit analysis, and zero-crossing density.",
        description_en="Sample value distribution suggests I2S bit alignment or byte-endianness container mismatch.",
        description_tr="Örnek değer dağılımı I2S bit hizalama veya bayt sırası konteyner uyuşmazlığına işaret ediyor.",
        possible_causes=(
            "Hypothesis: I2S WS delay mismatch (e.g. Philips I2S 1-bit delay vs Left-Justified 0-bit delay).",
            "Hypothesis: 24-bit data shifted by 8 bits in 32-bit slot.",
        ),
        suggested_actions=(
            "Verify I2S format standard in ESP-IDF: I2S_COMM_FORMAT_STAND_I2S vs I2S_COMM_FORMAT_STAND_MSB.",
            "Check whether sensor MSB aligns with slot bit 31 or bit 23.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="SignalQualityDoctor",
        primary_owner="Ozan (Module B)",
    ),

    # --------------------------------------------------------------------------
    # Subsystem: DSP, Processing & Metrology (AF-DSP-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-DSP-001",
        name="INVALID_SAMPLE_RATE",
        subsystem=Subsystem.DSP,
        severity=Severity.ERROR,
        detection_condition="DSP processing requested with unsupported or non-positive sample rate (fs <= 0 or fs > 192000).",
        evidence_needed="Requested sample rate value.",
        description_en="DSP processing requested with invalid or unsupported sample rate.",
        description_tr="DSP filtreleme geçersiz veya desteklenmeyen örnekleme hızı ile talep edildi.",
        possible_causes=(
            "Hypothesis: Stream metadata corrupted or uninitialized prior to DSP pipeline execution.",
        ),
        suggested_actions=(
            "Ensure stream metadata provides valid positive sample rate (e.g. 4000 or 48000 Hz).",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="LiveStreamingPipeline",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-DSP-002",
        name="FILTER_CONFIGURATION_INVALID",
        subsystem=Subsystem.DSP,
        severity=Severity.ERROR,
        detection_condition="Bandpass filter cutoff frequencies violate Nyquist bound (high_hz >= fs / 2 or low_hz <= 0).",
        evidence_needed="Cutoff low_hz, high_hz, and Nyquist limit (fs / 2).",
        description_en="Digital filter cutoff frequencies violate mathematical stability or Nyquist bounds.",
        description_tr="Dijital filtre kesim frekansları matematiksel kararlılık veya Nyquist sınırını ihlal ediyor.",
        possible_causes=(
            "Hypothesis: User selected high-frequency preset while operating on downsampled stream.",
        ),
        suggested_actions=(
            "Clamp high cutoff to min(requested_high, 0.45 * fs) before SOS coefficient design.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="LiveStreamingPipeline",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-DSP-003",
        name="ANALYSIS_PROCESSING_FAILED",
        subsystem=Subsystem.DSP,
        severity=Severity.ERROR,
        detection_condition="Scientific analysis pipeline (Welch, Hilbert, System ID) raised unhandled computation exception.",
        evidence_needed="Analysis profile ID, session ID, and Python exception traceback.",
        description_en="Scientific acoustic analysis pipeline computation failed.",
        description_tr="Bilimsel akustik analiz hattı hesaplaması başarısız oldu.",
        possible_causes=(
            "Hypothesis: Audio session duration too short for requested Welch nperseg segment length.",
            "Hypothesis: Numerical NaN/Inf encountered during floating-point matrix inversion.",
        ),
        suggested_actions=(
            "Ensure recorded session contains at least 2 * nperseg samples before Welch PSD.",
            "Check raw signal for NaN or infinite values.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="AnalysisService",
        primary_owner="Ege (Module C)",
    ),

    # --------------------------------------------------------------------------
    # Subsystem: Storage & Recording Integrity (AF-FILE-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-FILE-001",
        name="RECORDING_WRITE_FAILED",
        subsystem=Subsystem.STORAGE,
        severity=Severity.CRITICAL,
        detection_condition="SessionRecorder failed to append audio samples to disk WAV file.",
        evidence_needed="Target session directory, file path, and OS disk I/O error message.",
        description_en="Disk write failed while saving raw acoustic recording session.",
        description_tr="Ham akustik kayıt oturumu diske yazılırken yazma hatası oluştu.",
        possible_causes=(
            "Hypothesis: Disk storage full or quota exceeded.",
            "Hypothesis: File system permission denied on user data directory.",
            "Hypothesis: External storage drive disconnected mid-session.",
        ),
        suggested_actions=(
            "Check available free space on storage partition.",
            "Verify write permissions on AuscultaForge user-data directory.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="SessionRecorder",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-FILE-002",
        name="WAV_INTEGRITY_HASH_MISMATCH",
        subsystem=Subsystem.STORAGE,
        severity=Severity.CRITICAL,
        detection_condition="Recomputed SHA-256 hash of recorded raw.wav does not match session manifest record.",
        evidence_needed="Session ID, recorded manifest SHA-256, and recomputed SHA-256 hash.",
        description_en="Recorded WAV file cryptographic integrity verification failed; file modified or corrupted.",
        description_tr="Kayıtlı WAV dosyasının kriptografik bütünlük doğrulaması başarısız; dosya değiştirilmiş veya bozulmuş.",
        possible_causes=(
            "Hypothesis: File modified by external application after session completion.",
            "Hypothesis: Incomplete disk flush during unexpected backend termination.",
        ),
        suggested_actions=(
            "Inspect file modification timestamp and session manifest file.",
            "Avoid editing recorded audio files outside AuscultaForge workstation.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="SessionVerifier",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-FILE-003",
        name="INSUFFICIENT_STORAGE",
        subsystem=Subsystem.STORAGE,
        severity=Severity.CRITICAL,
        detection_condition="Storage partition hosting user data has less than minimum required free space (< 200 MB).",
        evidence_needed="Free bytes available and minimum required threshold.",
        description_en="Insufficient free disk space available to guarantee safe session recording.",
        description_tr="Güvenli oturum kaydını garanti etmek için yeterli boş disk alanı yok.",
        possible_causes=(
            "Hypothesis: Host hard drive or SSD is nearly full.",
        ),
        suggested_actions=(
            "Free disk space on host machine or archive older AuscultaForge sessions.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="SessionRecorder",
        primary_owner="Ege (Module C)",
    ),

    # --------------------------------------------------------------------------
    # Subsystem: Application, Host Process & Transport (AF-APP-xxx)
    # --------------------------------------------------------------------------
    FaultDefinition(
        code="AF-APP-001",
        name="BACKEND_STARTUP_FAILED",
        subsystem=Subsystem.APP,
        severity=Severity.CRITICAL,
        detection_condition="FastAPI desktop server failed to bind port or initialize runtime within startup timeout.",
        evidence_needed="Host, port, and exception traceback.",
        description_en="AuscultaForge desktop backend server failed to start.",
        description_tr="AuscultaForge masaüstü arka uç sunucusu başlatılamadı.",
        possible_causes=(
            "Hypothesis: Port conflict, missing dependencies, or invalid configuration.",
        ),
        suggested_actions=(
            "Inspect desktop backend log file (%APPDATA%/AuscultaForge/logs/backend.log).",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="DesktopServer",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-APP-002",
        name="BACKEND_PROCESS_EXITED",
        subsystem=Subsystem.APP,
        severity=Severity.CRITICAL,
        detection_condition="Desktop frontend detected backend child process terminated unexpectedly.",
        evidence_needed="Process PID, exit code, and parent watchdog status.",
        description_en="Backend server process exited unexpectedly during workstation operation.",
        description_tr="Arka uç sunucu işlemi çalışma sırasında beklenmedik şekilde sonlandı.",
        possible_causes=(
            "Hypothesis: Unhandled exception in native C extension, memory crash, or parent watchdog trigger.",
        ),
        suggested_actions=(
            "Inspect backend log file and Windows Application Event logs for crash report.",
        ),
        auto_recovery_permitted=False,
        affects_g1_acceptance=True,
        observable_without_hardware=True,
        emitting_component="TauriWatchdog",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-APP-003",
        name="FRONTEND_BACKEND_COMMUNICATION_FAILED",
        subsystem=Subsystem.APP,
        severity=Severity.ERROR,
        detection_condition="WebSocket connection to local backend closed abnormally or reconnect attempts exhausted.",
        evidence_needed="WebSocket URL, reconnect attempt count, and last close code.",
        description_en="Communication link between React Desktop UI and local Python backend failed.",
        description_tr="React masaüstü arayüzü ile yerel Python arka ucu arasındaki iletişim bağlantısı koptu.",
        possible_causes=(
            "Hypothesis: Backend crashed or blocked in synchronous call.",
            "Hypothesis: Authentication token expired or mismatched.",
        ),
        suggested_actions=(
            "Check backend process status and verify handshake token match.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="BridgeClient",
        primary_owner="Ege (Module C)",
    ),
    FaultDefinition(
        code="AF-APP-004",
        name="RESOURCE_LIMIT_EXCEEDED",
        subsystem=Subsystem.APP,
        severity=Severity.WARNING,
        detection_condition="Host memory consumption or background queue depth exceeded configured safety ceiling.",
        evidence_needed="Memory bytes used, queue size, and configured limits.",
        description_en="Workstation resource utilization exceeded safe engineering thresholds.",
        description_tr="İş istasyonu kaynak kullanımı güvenli mühendislik eşiklerini aştı.",
        possible_causes=(
            "Hypothesis: Unbounded audio frame retention or slow display rendering consuming RAM.",
        ),
        suggested_actions=(
            "Verify display frame drop-oldest policy is actively discarding throttled UI frames.",
        ),
        auto_recovery_permitted=True,
        affects_g1_acceptance=False,
        observable_without_hardware=True,
        emitting_component="StreamManager",
        primary_owner="Ege (Module C)",
    ),
]

FAULT_CATALOG: dict[str, FaultDefinition] = {f.code: f for f in _CATALOG_LIST}


def get_fault_definition(code: str) -> Optional[FaultDefinition]:
    """Retrieve fault definition by stable code (e.g. 'AF-USB-001')."""
    return FAULT_CATALOG.get(code)


def list_fault_definitions(subsystem: Optional[Subsystem] = None) -> list[FaultDefinition]:
    """List all registered fault definitions, optionally filtered by subsystem."""
    if subsystem is None:
        return list(_CATALOG_LIST)
    return [f for f in _CATALOG_LIST if f.subsystem == subsystem]


list_all_faults = list_fault_definitions
