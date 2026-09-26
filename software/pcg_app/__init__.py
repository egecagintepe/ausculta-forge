"""AuscultaForge — Desktop Application & Local Bridge Package."""

from .protocol import PROTOCOL_VERSION, FILTER_PRESETS
from .state import StreamManager
from .app import create_app
from .device_runtime import (
    DeviceState,
    DeviceRuntime,
    DeviceCapabilities,
    DeviceSamplePacket,
    DeviceTransport,
    packet_to_sample_block,
)
from .analysis_service import AnalysisService

__all__ = [
    "PROTOCOL_VERSION",
    "FILTER_PRESETS",
    "StreamManager",
    "AnalysisService",
    "create_app",
    "DeviceState",
    "DeviceRuntime",
    "DeviceCapabilities",
    "DeviceSamplePacket",
    "DeviceTransport",
    "packet_to_sample_block",
]
