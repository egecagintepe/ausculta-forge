"""AuscultaForge — Local Application WebSocket Message Protocol (v1.0).

Defines the message contracts for real-time communication between the Python
application backend and the local desktop frontend (React/Vite).

IMPORTANT ARCHITECTURAL DISTINCTION:
This protocol is strictly an application-layer bridge protocol operating over local
WebSockets/HTTP (JSON framing). It is entirely decoupled from the MCU-to-PC wire
transport protocol defined in `docs/protocol/PROTOCOL_DRAFT.md` (which governs
physical Native USB packet framing from ESP32-S3 hardware).
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional
import json


PROTOCOL_VERSION = "1.0"


FILTER_PRESETS: dict[str, tuple[float, float]] = {
    "recommended": (20.0, 200.0),
    "bell": (20.0, 120.0),
    "diaphragm": (100.0, 500.0),
    "extended": (20.0, 600.0),
}


def make_hello_message(capabilities: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "hello",
        "version": PROTOCOL_VERSION,
        "app": "AuscultaForge Bridge",
        "capabilities": capabilities,
        "state": state,
    }


def make_stream_state_message(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "stream_state",
        "version": PROTOCOL_VERSION,
        **state,
    }


def make_signal_frame_message(
    sequence: int,
    timestamp_s: float,
    sample_rate_hz: int,
    raw_samples: list[float],
    filtered_samples: list[float],
    rms_val: float,
    peak_val: float,
    crest_factor_val: float,
    quality_summary: dict[str, Any],
    recording_active: bool = False,
) -> dict[str, Any]:
    return {
        "type": "signal_frame",
        "version": PROTOCOL_VERSION,
        "sequence": sequence,
        "timestamp_s": round(timestamp_s, 4),
        "sample_rate_hz": sample_rate_hz,
        "raw_samples": raw_samples,
        "filtered_samples": filtered_samples,
        "metrics": {
            "rms": round(rms_val, 5),
            "peak": round(peak_val, 5),
            "crest_factor": round(crest_factor_val, 3),
        },
        "stream_quality": quality_summary,
        "recording_active": recording_active,
    }


def make_recording_state_message(
    is_recording: bool,
    session_id: Optional[str] = None,
    elapsed_seconds: float = 0.0,
    samples_recorded: int = 0,
    blocks_recorded: int = 0,
    source: str = "unknown",
    sample_rate_hz: int = 4000,
) -> dict[str, Any]:
    return {
        "type": "recording_state",
        "version": PROTOCOL_VERSION,
        "is_recording": is_recording,
        "session_id": session_id,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "samples_recorded": samples_recorded,
        "blocks_recorded": blocks_recorded,
        "source": source,
        "sample_rate_hz": sample_rate_hz,
    }


def make_error_message(message: str, code: str = "ERROR") -> dict[str, Any]:
    return {
        "type": "error",
        "version": PROTOCOL_VERSION,
        "code": code,
        "message": message,
    }
