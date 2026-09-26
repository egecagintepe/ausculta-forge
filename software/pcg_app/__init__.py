"""AuscultaForge — Desktop Application & Local Bridge Package."""

from .protocol import PROTOCOL_VERSION, FILTER_PRESETS
from .state import StreamManager
from .app import create_app

__all__ = ["PROTOCOL_VERSION", "FILTER_PRESETS", "StreamManager", "create_app"]
