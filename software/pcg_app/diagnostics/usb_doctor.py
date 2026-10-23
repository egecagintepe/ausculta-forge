"""AuscultaForge — Platform-Aware USB Discovery Doctor & Hardware Inspector.

Diagnoses host USB serial enumeration, CDC-ACM hardware readiness, and connection states:
1. No serial ports enumerated on host.
2. Serial ports enumerated, but no verified AuscultaForge candidate.
3. Selected port is unavailable / vanished.
4. Selected port is in use / access denied (busy by competing terminal).
5. Port opens, but HELLO handshake times out.
6. Port opens, but HELLO responds with invalid magic/version.
7. Port opens and HELLO validates verified device capabilities.
8. Device disconnects during active session.
9. Device reappears after reconnection.

Hardware Physical Context:
- Native OTG uses GPIO19 D- / GPIO20 D+ and shares the internal PHY with USB
  Serial/JTAG. Connector count and PCB routing require physical inspection.
- Espressif 0x303A:0x1001 is a Serial/JTAG candidate, not proof of TinyUSB firmware.
- TinyUSB application descriptors vary; external UART bridges are distinct.
- Enumeration/access alone never establishes canonical HELLO identity.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from .fault_catalog import Subsystem, Severity, EvidenceOrigin, get_fault_definition
from .event_model import DiagnosticEvent
from .flight_recorder import FlightRecorderJournal, get_flight_recorder

# Known Espressif USB vendor and product IDs
ESPRESSIF_VID = 0x303A
ESP32_S3_CDC_ACM_PID = 0x1001
ESP32_S3_JTAG_SERIAL_PID = 0x1002


class DiscoveryDiagnosticState(str, Enum):
    """Authoritative physical USB discovery diagnostics state."""
    NO_SERIAL_PORTS_ENUMERATED = "NO_SERIAL_PORTS_ENUMERATED"
    PORTS_ENUMERATED_NO_VERIFIED_DEVICE = "PORTS_ENUMERATED_NO_VERIFIED_DEVICE"
    PORT_UNAVAILABLE = "PORT_UNAVAILABLE"
    PORT_BUSY_ACCESS_DENIED = "PORT_BUSY_ACCESS_DENIED"
    PORT_OPEN_HELLO_TIMEOUT = "PORT_OPEN_HELLO_TIMEOUT"
    PORT_OPEN_HELLO_WRONG_MAGIC = "PORT_OPEN_HELLO_WRONG_MAGIC"
    DEVICE_VERIFIED_READY = "DEVICE_VERIFIED_READY"
    DEVICE_DISCONNECTED_ACTIVE_SESSION = "DEVICE_DISCONNECTED_ACTIVE_SESSION"
    DEVICE_RECONNECTED = "DEVICE_RECONNECTED"


@dataclass(slots=True)
class UsbPortDescriptor:
    """Detailed host serial port hardware descriptor."""
    port_name: str
    description: str
    hwid: str
    vid: Optional[int] = None
    pid: Optional[int] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    interface: Optional[str] = None
    is_espressif_candidate: bool = False
    candidate_reason: str = "Standard COM port"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.vid is not None:
            d["vid_hex"] = f"0x{self.vid:04X}"
        if self.pid is not None:
            d["pid_hex"] = f"0x{self.pid:04X}"
        return d


class UsbDiscoveryDoctor:
    """Platform-aware serial bus scanner and hardware diagnostic engine."""

    def __init__(
        self,
        flight_recorder: Optional[FlightRecorderJournal] = None,
        custom_comports_fn: Optional[Any] = None,
    ) -> None:
        self.flight_recorder = flight_recorder or get_flight_recorder()
        self._custom_comports_fn = custom_comports_fn
        self._last_detected_ports: set[str] = set()

    def scan_ports(self) -> list[UsbPortDescriptor]:
        """Scan real host operating system serial ports and extract descriptors."""
        raw_ports = self._list_system_ports()
        descriptors: list[UsbPortDescriptor] = []

        for p in raw_ports:
            desc = self._parse_port(p)
            descriptors.append(desc)

        current_port_names = {d.port_name for d in descriptors}

        # Check for re-enumeration events
        reappeared = current_port_names - self._last_detected_ports
        if reappeared and self._last_detected_ports:
            for port in reappeared:
                self.flight_recorder.record(
                    fault_code="AF-USB-007",
                    message=f"Serial port {port} re-enumerated on host bus.",
                    subsystem=Subsystem.USB,
                    severity=Severity.INFO,
                    device_port=port,
                    evidence_origin=EvidenceOrigin.OBSERVED_HOST,
                )

        self._last_detected_ports = current_port_names

        # If no ports or no candidates, record diagnostic warning
        has_candidates = any(d.is_espressif_candidate for d in descriptors)
        if not descriptors:
            self.flight_recorder.record(
                fault_code="AF-USB-001",
                message="Zero serial ports enumerated on host bus.",
                subsystem=Subsystem.USB,
                severity=Severity.WARNING,
                evidence_origin=EvidenceOrigin.OBSERVED_HOST,
                counter_snapshot={"enumerated_ports": 0},
            )
        elif not has_candidates:
            self.flight_recorder.record(
                fault_code="AF-USB-001",
                message=f"Enumerated {len(descriptors)} serial port(s), but none match AuscultaForge ESP32-S3 descriptors.",
                subsystem=Subsystem.USB,
                severity=Severity.WARNING,
                evidence_origin=EvidenceOrigin.OBSERVED_HOST,
                counter_snapshot={"enumerated_ports": len(descriptors)},
            )

        return descriptors

    def check_port_accessibility(self, port_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Non-intrusively verify whether port can be opened by host process.

        Returns: (is_accessible, fault_code, error_message)
        """
        try:
            import serial
        except ImportError:
            return False, "AF-USB-008", "Python package 'pyserial' is not installed."

        try:
            s = serial.Serial(
                port=port_name,
                baudrate=115200,
                timeout=0.1,
                write_timeout=0.1,
            )
            s.close()
            return True, None, None
        except PermissionError as e:
            return False, "AF-USB-002", f"Access Denied (Port locked by another process): {e}"
        except Exception as e:
            err_str = str(e)
            if "PermissionError" in err_str or "Access is denied" in err_str or "Device or resource busy" in err_str:
                return False, "AF-USB-002", f"Port busy or locked by another process: {err_str}"
            return False, "AF-USB-003", f"Failed to open port '{port_name}': {err_str}"

    def diagnose_environment(
        self,
        target_port: Optional[str] = None,
        is_active_session: bool = False,
        last_disconnect: bool = False,
        probe_access: bool = False,
    ) -> Tuple[DiscoveryDiagnosticState, dict[str, Any]]:
        """Diagnose overall USB hardware connectivity and produce actionable status."""
        ports = self.scan_ports()

        if last_disconnect:
            return DiscoveryDiagnosticState.DEVICE_DISCONNECTED_ACTIVE_SESSION, {
                "message": "Device disconnected during active streaming session.",
                "action": "Inspect USB cable connection and restart acquisition.",
            }

        if not ports:
            return DiscoveryDiagnosticState.NO_SERIAL_PORTS_ENUMERATED, {
                "message": "No serial ports detected on host system.",
                "action": "Ensure USB-C cable has data lines (D+/D-) and is connected to ESP32-S3 Native USB port.",
                "ports": [],
            }

        # Check candidate ports
        candidates = [p for p in ports if p.is_espressif_candidate]
        selected_port = target_port or (candidates[0].port_name if candidates else None)

        if not selected_port:
            return DiscoveryDiagnosticState.PORTS_ENUMERATED_NO_VERIFIED_DEVICE, {
                "message": f"{len(ports)} serial port(s) detected, but none confirmed as ESP32-S3 Native USB.",
                "action": "Select port manually from Ports list or verify ESP32-S3 firmware CDC-ACM descriptor.",
                "available_ports": [p.to_dict() for p in ports],
            }

        if not probe_access:
            return DiscoveryDiagnosticState.PORTS_ENUMERATED_NO_VERIFIED_DEVICE, {
                "port": selected_port, "message": "Port enumerated; firmware NOT VERIFIED.",
                "action": "Inspect the board and explicitly perform canonical HELLO. Port access is not probed automatically.",
                "descriptors": [p.to_dict() for p in ports if p.port_name == selected_port],
            }
        # Explicit access probe may toggle DTR/reset; it still cannot verify firmware.
        accessible, code, err_msg = self.check_port_accessibility(selected_port)
        if not accessible:
            if code == "AF-USB-002":
                return DiscoveryDiagnosticState.PORT_BUSY_ACCESS_DENIED, {
                    "port": selected_port,
                    "fault_code": code,
                    "message": err_msg,
                    "action": "Close serial monitors (PuTTY, Arduino IDE, minicom) or restart backend.",
                }
            return DiscoveryDiagnosticState.PORT_UNAVAILABLE, {
                "port": selected_port,
                "fault_code": code,
                "message": err_msg,
                "action": "Unplug and reconnect the device or check cable integrity.",
            }

        return DiscoveryDiagnosticState.PORTS_ENUMERATED_NO_VERIFIED_DEVICE, {
            "port": selected_port,
            "message": f"Port '{selected_port}' is available and ready for canonical B/C HELLO handshake.",
            "descriptors": [p.to_dict() for p in ports if p.port_name == selected_port],
        }

    # --------------------------------------------------------------------------
    # Internal Helpers
    # --------------------------------------------------------------------------
    def _list_system_ports(self) -> list[Any]:
        """Fetch port objects from serial.tools.list_ports or mock."""
        if self._custom_comports_fn is not None:
            return self._custom_comports_fn()
        try:
            import serial.tools.list_ports
            return list(serial.tools.list_ports.comports())
        except Exception:
            return []

    def _parse_port(self, p: Any) -> UsbPortDescriptor:
        """Parse pyserial ListPortInfo object into structured descriptor."""
        device = getattr(p, "device", str(p))
        description = getattr(p, "description", "") or ""
        hwid = getattr(p, "hwid", "") or ""
        vid = getattr(p, "vid", None)
        pid = getattr(p, "pid", None)
        serial_number = getattr(p, "serial_number", None)
        manufacturer = getattr(p, "manufacturer", None)
        product = getattr(p, "product", None)
        interface = getattr(p, "interface", None)

        is_cand = False
        reason = "Generic peripheral"

        # Check Espressif VID
        if vid == ESPRESSIF_VID:
            if pid == ESP32_S3_CDC_ACM_PID:
                is_cand = True
                reason = "Espressif USB Serial/JTAG candidate (0x303A:0x1001); canonical HELLO required"
            elif pid == ESP32_S3_JTAG_SERIAL_PID:
                is_cand = True
                reason = "Espressif candidate (0x303A:0x1002); application/controller unverified"
            else:
                is_cand = True
                reason = f"Espressif VID 0x303A (PID {pid}); canonical HELLO required"
        elif any(kw in description.upper() or kw in (hwid or "").upper() for kw in ("ESP32", "ESPRESSIF", "AUSCULTAFORGE", "CDC-ACM")):
            is_cand = True
            reason = "Keyword match in USB device description"
        elif vid in (0x10C4,0x1A86,0x0403,0x067B):
            reason = "External USB-UART bridge candidate; attached silicon unknown, inspect PCB"

        return UsbPortDescriptor(
            port_name=device,
            description=description,
            hwid=hwid,
            vid=vid,
            pid=pid,
            serial_number=serial_number,
            manufacturer=manufacturer,
            product=product,
            interface=interface,
            is_espressif_candidate=is_cand,
            candidate_reason=reason,
        )
