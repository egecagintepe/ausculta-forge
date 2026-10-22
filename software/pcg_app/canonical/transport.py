"""AuscultaForge Host Transport Adapter Boundary (USB CDC-ACM & Simulation).

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Joint Reviewer: Ozan (Module B)

STATUS:
Provides clean host adapter interface for USB CDC-ACM communication with
ESP32-S3 and duplex simulation loopback for automated CI testing.
CRITICAL: Real hardware USB transport is NOT declared verified until real ESP32-S3
board is physically attached and tested.
"""

from abc import ABC, abstractmethod
from enum import Enum
import time
from typing import Any, Dict, Optional

try:
    from .simulator import SimulatedEsp32Device
except ImportError:
    from .simulated_device import SimulatedEsp32Device


class TransportState(str, Enum):
    """Transport layer connection state."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING   = "CONNECTING"
    CONNECTED    = "CONNECTED"
    ERROR        = "ERROR"
    CLOSED       = "CLOSED"


class BaseTransportAdapter(ABC):
    """Abstract interface for AuscultaForge bidirectional binary byte transport."""

    @abstractmethod
    def open(self, port: str, baudrate: int = 115200, timeout_s: float = 0.5) -> None:
        """Open transport connection."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close transport connection and release resources."""
        pass

    @abstractmethod
    def read(self, max_bytes: int = 1024) -> bytes:
        """Read up to max_bytes from transport (non-blocking or bounded by timeout)."""
        pass

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write binary data bytes to transport."""
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flush any pending transport buffers."""
        pass

    @abstractmethod
    def get_state(self) -> TransportState:
        """Return current transport state."""
        pass

    @abstractmethod
    def get_telemetry(self) -> Dict[str, Any]:
        """Return structured transport error and byte statistics."""
        pass


class UsbCdcAcmAdapter(BaseTransportAdapter):
    """Real host USB CDC-ACM adapter utilizing pyserial."""

    def __init__(self) -> None:
        self.state: TransportState = TransportState.DISCONNECTED
        self._serial: Optional[Any] = None
        self._port_name: Optional[str] = None
        self._baudrate: int = 115200
        self._timeout_s: float = 0.5

        # Telemetry
        self.bytes_read: int = 0
        self.bytes_written: int = 0
        self.read_errors: int = 0
        self.write_errors: int = 0
        self.last_error_message: Optional[str] = None

    def open(self, port: str, baudrate: int = 115200, timeout_s: float = 0.5) -> None:
        """Open actual COM port. Fails gracefully if pyserial missing or port unreachable."""
        self._port_name = port
        self._baudrate = baudrate
        self._timeout_s = timeout_s
        self.state = TransportState.CONNECTING

        try:
            import serial
        except ImportError:
            self.state = TransportState.ERROR
            self.last_error_message = "Python package 'pyserial' is not installed."
            raise RuntimeError(self.last_error_message)

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout_s,
                write_timeout=timeout_s,
            )
            # ESP32-S3 CDC-ACM control line configuration
            self._serial.dtr = True
            self._serial.rts = True
            time.sleep(0.05)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self.state = TransportState.CONNECTED
        except Exception as e:
            self.state = TransportState.ERROR
            self.last_error_message = str(e)
            raise ConnectionError(f"Failed to open USB CDC-ACM port '{port}': {e}") from e

    def close(self) -> None:
        """Close physical port gracefully."""
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self.state = TransportState.CLOSED

    def read(self, max_bytes: int = 1024) -> bytes:
        if self._serial is None or self.state != TransportState.CONNECTED:
            return b""
        try:
            n_avail = self._serial.in_waiting
            to_read = max(n_avail, 1) if n_avail > 0 else 1
            to_read = min(to_read, max_bytes)
            data = self._serial.read(to_read)
            if data:
                self.bytes_read += len(data)
            return data
        except Exception as e:
            self.read_errors += 1
            self.last_error_message = f"Read error: {e}"
            self.state = TransportState.ERROR
            return b""

    def write(self, data: bytes) -> int:
        if self._serial is None or self.state != TransportState.CONNECTED:
            return 0
        try:
            written = self._serial.write(data)
            self.bytes_written += written
            return written
        except Exception as e:
            self.write_errors += 1
            self.last_error_message = f"Write error: {e}"
            self.state = TransportState.ERROR
            return 0

    def flush(self) -> None:
        if self._serial is not None and self.state == TransportState.CONNECTED:
            try:
                self._serial.flush()
            except Exception:
                pass

    def get_state(self) -> TransportState:
        return self.state

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "transport_type": "USB_CDC_ACM",
            "port": self._port_name,
            "baudrate": self._baudrate,
            "state": self.state.value,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
            "read_errors": self.read_errors,
            "write_errors": self.write_errors,
            "last_error": self.last_error_message,
        }


class DuplexLoopbackAdapter(BaseTransportAdapter):
    """In-memory duplex pipe connecting to SimulatedEsp32Device."""

    def __init__(self, device: SimulatedEsp32Device, max_chunk_size: int = 1024) -> None:
        self.device = device
        self.max_chunk_size = max_chunk_size
        self.state: TransportState = TransportState.DISCONNECTED
        self._host_to_device_buf = bytearray()
        self._device_to_host_buf = bytearray()

        self.bytes_read: int = 0
        self.bytes_written: int = 0

    def open(self, port: str = "LOOPBACK", baudrate: int = 115200, timeout_s: float = 0.5) -> None:
        self.device.connect()
        self.state = TransportState.CONNECTED

    def close(self) -> None:
        self.device.disconnect()
        self.state = TransportState.CLOSED
        self._host_to_device_buf.clear()
        self._device_to_host_buf.clear()

    def write(self, data: bytes) -> int:
        if self.state != TransportState.CONNECTED:
            return 0
        self._host_to_device_buf.extend(data)
        self.bytes_written += len(data)

        # Device processes incoming command bytes immediately
        reply = self.device.process_incoming_bytes(bytes(self._host_to_device_buf))
        self._host_to_device_buf.clear()
        if reply:
            self._device_to_host_buf.extend(reply)

        return len(data)

    def read(self, max_bytes: int = 1024) -> bytes:
        if self.state != TransportState.CONNECTED:
            return b""

        # If streaming, device produces audio frames into buffer
        if self.device.device_state == "STREAMING" and len(self._device_to_host_buf) < 1068:
            frame = self.device.produce_next_audio_frame()
            if frame:
                self._device_to_host_buf.extend(frame)

        chunk_size = min(len(self._device_to_host_buf), max_bytes, self.max_chunk_size)
        if chunk_size == 0:
            return b""

        chunk = bytes(self._device_to_host_buf[:chunk_size])
        del self._device_to_host_buf[:chunk_size]
        self.bytes_read += len(chunk)
        return chunk

    def flush(self) -> None:
        pass

    def get_state(self) -> TransportState:
        return self.state

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "transport_type": "DUPLEX_LOOPBACK_SIMULATION",
            "state": self.state.value,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
        }


# Authoritative Production Aliases
UsbCdcAcmTransport = UsbCdcAcmAdapter
SimulatedLoopbackAdapter = DuplexLoopbackAdapter
SimulatedTransport = DuplexLoopbackAdapter

