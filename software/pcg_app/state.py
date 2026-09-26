"""AuscultaForge — Application State & Live Stream Orchestration Manager.

Coordinates real-time PCG signal generation, streaming DSP filtering,
quality monitoring, and session recording in a clean, UI-independent layer.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Callable, Optional, Set

import numpy as np

from pcg_core.models import SampleBlock
from pcg_core.sources import MockPCGSource, WavSource, RealtimeWavSource
from pcg_core.streaming import LiveStreamingPipeline
from pcg_core.recording import (
    SessionRecorder,
    SessionMetadata,
    create_session_source,
    list_sessions,
    get_session,
    validate_session_id,
)
from .protocol import (
    FILTER_PRESETS,
    make_hello_message,
    make_stream_state_message,
    make_signal_frame_message,
    make_recording_state_message,
    make_error_message,
)


class StreamManager:
    """Central state and streaming task manager for the local desktop application."""

    def __init__(self, sessions_dir: str | Path = "experiments/sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Filter configuration
        self.filter_preset: str = "recommended"
        low, high = FILTER_PRESETS[self.filter_preset]
        self.filter_low_hz: float = low
        self.filter_high_hz: float = high

        # Ingestion pipeline
        self.sample_rate_hz: int = 4000
        self.block_size: int = 128
        self.pipeline = LiveStreamingPipeline(
            buffer_duration_s=5.0,
            filter_low_hz=self.filter_low_hz,
            filter_high_hz=self.filter_high_hz,
            filter_order=4,
        )

        # Source management
        self.source_type: str = "mock"
        self.source_path: Optional[str] = None
        self.source_session_id: Optional[str] = None
        self.active_source_name: str = "Synthetic PCG (S1/S2 Normal)"
        self._source_generator = None

        # Streaming loop state
        self.is_streaming: bool = True
        self.is_paused: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        self._active_connections: Set[Any] = set()

        # Session recorder
        self.recorder = SessionRecorder(output_dir=self.sessions_dir, wav_format="float32")
        self._recording_started_wall: float = 0.0

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "block_size": self.block_size,
            "sources": ["mock", "realtime_wav", "session"],
            "filter_presets": list(FILTER_PRESETS.keys()),
            "max_buffer_seconds": 15,
        }

    def get_state_dict(self) -> dict[str, Any]:
        return {
            "is_streaming": self.is_streaming,
            "is_paused": self.is_paused,
            "is_recording": self.recorder.is_recording,
            "active_session_id": self.recorder.session_id,
            "source_type": self.source_type,
            "active_source_name": self.active_source_name,
            "sample_rate_hz": self.sample_rate_hz,
            "filter_preset": self.filter_preset,
            "filter_low_hz": self.filter_low_hz,
            "filter_high_hz": self.filter_high_hz,
            "connected_clients": len(self._active_connections),
        }

    def register_client(self, websocket: Any) -> None:
        self._active_connections.add(websocket)

    def unregister_client(self, websocket: Any) -> None:
        self._active_connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self._active_connections:
            return

        dead_clients = set()
        for ws in self._active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead_clients.add(ws)

        for dead in dead_clients:
            self._active_connections.discard(dead)

    def _create_source_generator(self):
        """Construct the generator for the active source."""
        if self.source_type == "mock":
            src = MockPCGSource(
                sample_rate_hz=self.sample_rate_hz,
                heart_rate_bpm=72.0,
                block_size=self.block_size,
                duration_s=30.0,
            )
            return src.blocks()
        elif self.source_type == "realtime_wav" and self.source_path:
            p = Path(self.source_path)
            if not p.exists():
                raise FileNotFoundError(f"Source WAV not found: {p}")
            src = WavSource(p, block_size=self.block_size)
            return src.blocks()
        elif self.source_type == "session" and self.source_session_id:
            src = create_session_source(
                self.source_session_id,
                sessions_dir=self.sessions_dir,
                block_size=self.block_size,
                realtime=False,
            )
            return src.blocks()
        else:
            # Fallback to mock
            src = MockPCGSource(
                sample_rate_hz=self.sample_rate_hz,
                heart_rate_bpm=72.0,
                block_size=self.block_size,
                duration_s=30.0,
            )
            return src.blocks()

    def set_filter(
        self,
        preset: Optional[str] = None,
        low_hz: Optional[float] = None,
        high_hz: Optional[float] = None,
    ) -> dict[str, Any]:
        """Update active streaming bandpass filter cutoffs."""
        if preset and preset in FILTER_PRESETS:
            self.filter_preset = preset
            self.filter_low_hz, self.filter_high_hz = FILTER_PRESETS[preset]
        else:
            if low_hz is not None:
                self.filter_low_hz = float(low_hz)
            if high_hz is not None:
                self.filter_high_hz = float(high_hz)
            self.filter_preset = "custom"

        # Re-initialize pipeline with new cutoffs
        self.pipeline = LiveStreamingPipeline(
            buffer_duration_s=5.0,
            filter_low_hz=self.filter_low_hz,
            filter_high_hz=self.filter_high_hz,
            filter_order=4,
        )
        return self.get_state_dict()

    def select_source(
        self,
        source_type: str,
        path: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Switch active stream source."""
        self.source_type = source_type
        self.source_path = path
        self.source_session_id = session_id

        if source_type == "mock":
            self.active_source_name = "Synthetic PCG (S1/S2 Normal)"
        elif source_type == "realtime_wav" and path:
            self.active_source_name = f"Replay: {Path(path).name}"
        elif source_type == "session":
            if not session_id:
                raise ValueError("session_id must be provided when source_type is 'session'")
            validate_session_id(session_id, self.sessions_dir)
            self.active_source_name = f"Session Replay: {session_id}"
        else:
            self.active_source_name = f"Source ({source_type})"

        # Reset generator
        self._source_generator = None
        return self.get_state_dict()

    def start_recording(self, source_label: Optional[str] = None) -> str:
        """Start recording incoming blocks into a new session."""
        source = source_label or self.active_source_name
        sid = self.recorder.start(source=source)
        self._recording_started_wall = time.time()
        return sid

    def stop_recording(self) -> SessionMetadata:
        """Finalize and save the active recording session."""
        meta = self.recorder.stop()
        return meta

    def start_stream(self) -> None:
        self.is_streaming = True
        self.is_paused = False

    def pause_stream(self) -> None:
        self.is_paused = True

    def resume_stream(self) -> None:
        self.is_paused = False

    def stop_stream(self) -> None:
        self.is_streaming = False

    async def start_streaming_task(self) -> None:
        """Start the background stream generator task."""
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._stream_loop())

    async def stop_streaming_task(self) -> None:
        """Stop the background stream generator task."""
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

    async def _stream_loop(self) -> None:
        """Continuous background loop consuming blocks, filtering, and broadcasting."""
        while True:
            try:
                if not self.is_streaming or self.is_paused:
                    await asyncio.sleep(0.05)
                    continue

                if self._source_generator is None:
                    self._source_generator = self._create_source_generator()

                # Fetch next block
                try:
                    block: SampleBlock = next(self._source_generator)
                except StopIteration:
                    # Loop source indefinitely for continuous display
                    self._source_generator = self._create_source_generator()
                    block = next(self._source_generator)

                # Process through pipeline
                frame = self.pipeline.process_block(block)

                # Record if session active
                if self.recorder.is_recording:
                    try:
                        self.recorder.record_block(block)
                    except Exception as e:
                        await self.broadcast(make_error_message(f"Recording error: {e}", "RECORDING_ERROR"))

                # Duration of current block in seconds
                block_duration = len(block.samples) / block.sample_rate_hz

                # Broadcast signal frame to clients
                quality_rep = self.pipeline.quality_monitor.report
                quality_summary = {
                    "total_blocks": quality_rep.total_blocks,
                    "dropped_blocks": quality_rep.dropped_blocks,
                    "repeated_sequences": quality_rep.repeated_sequences,
                    "sequence_discontinuities": quality_rep.sequence_discontinuities,
                    "is_healthy": quality_rep.is_healthy,
                }

                raw_list = [round(float(v), 5) for v in block.samples]
                filt_list = [round(float(v), 5) for v in frame.filtered_block.samples]

                msg = make_signal_frame_message(
                    sequence=block.sequence,
                    timestamp_s=block.timestamp_s,
                    sample_rate_hz=block.sample_rate_hz,
                    raw_samples=raw_list,
                    filtered_samples=filt_list,
                    rms_val=frame.metrics.rms,
                    peak_val=frame.metrics.peak_abs,
                    crest_factor_val=frame.metrics.crest_factor,
                    quality_summary=quality_summary,
                    recording_active=self.recorder.is_recording,
                )

                await self.broadcast(msg)

                # Wall-clock pacing
                await asyncio.sleep(block_duration)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.broadcast(make_error_message(f"Streaming error: {e}", "STREAM_ERROR"))
                await asyncio.sleep(0.1)
