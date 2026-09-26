"""AuscultaForge — Application State & Live Stream Orchestration Manager.

Coordinates real-time PCG signal processing, device lifecycle, streaming DSP filtering,
quality monitoring, and session recording in a clean, UI-independent layer.

CORE PRODUCT RULE:
The application starts with NO device connected and NO active stream.
Synthetic sources never activate automatically and never masquerade as physical hardware.
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
from .device_runtime import (
    DeviceRuntime,
    DeviceState,
    DeviceCapabilities,
    DeviceSamplePacket,
    packet_to_sample_block,
)
from .protocol import (
    FILTER_PRESETS,
    make_hello_message,
    make_stream_state_message,
    make_signal_frame_message,
    make_display_frame_message,
    make_recording_state_message,
    make_device_state_message,
    make_device_event_message,
    make_device_stats_message,
    make_error_message,
)
from .display_pipeline import (
    DisplayPipelineConfig,
    DisplayAggregator,
    DisplayFrame,
)


class ClientSession:
    """Encapsulates a connected WebSocket client with bounded display frame queuing and an isolated sender."""

    def __init__(self, ws: Any, queue_size: int = 2) -> None:
        self.ws = ws
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=queue_size)
        self.dropped_display_frames: int = 0
        self.total_frames_sent: int = 0
        self.is_alive: bool = True
        self._sender_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self.is_alive and (self._sender_task is None or self._sender_task.done()):
            try:
                loop = asyncio.get_running_loop()
                self._sender_task = loop.create_task(self._sender_loop())
            except RuntimeError:
                pass

    def stop(self) -> None:
        self.is_alive = False
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()

    def push_display_frame(self, frame_dict: dict[str, Any]) -> bool:
        """Bounded drop-oldest enqueue. Never blocks ingestion or recording."""
        if not self.is_alive:
            return False

        self.start()
        dropped = False

        if self.queue.full():
            try:
                _ = self.queue.get_nowait()
                self.dropped_display_frames += 1
                dropped = True
            except asyncio.QueueEmpty:
                pass

        try:
            self.queue.put_nowait(frame_dict)
        except asyncio.QueueFull:
            self.dropped_display_frames += 1
            dropped = True

        return dropped

    async def _sender_loop(self) -> None:
        try:
            while self.is_alive:
                msg = await self.queue.get()
                try:
                    await self.ws.send_json(msg)
                    self.total_frames_sent += 1
                except Exception:
                    self.is_alive = False
                    break
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            pass


class StreamManager:
    """Central state and streaming task manager for the local desktop application."""

    def __init__(
        self,
        sessions_dir: str | Path = "experiments/sessions",
        device_runtime: Optional[DeviceRuntime] = None,
        display_config: Optional[DisplayPipelineConfig] = None,
        enable_legacy_signal_frames: Optional[bool] = None,
    ) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Device runtime foundation
        self.device_runtime: DeviceRuntime = device_runtime or DeviceRuntime()

        # Display pipeline configuration and aggregator (single source of truth)
        self.display_config = display_config or DisplayPipelineConfig()
        if enable_legacy_signal_frames is not None:
            # Opt-in override: map directly into single authoritative display_config
            self.display_config.emit_legacy_signal_frames = enable_legacy_signal_frames

        self.display_aggregator = DisplayAggregator(self.display_config)
        self._clients: dict[Any, ClientSession] = {}

        # Filter configuration
        self.filter_preset: str = "recommended"
        low, high = FILTER_PRESETS[self.filter_preset]
        self.filter_low_hz: float = low
        self.filter_high_hz: float = high

        # Ingestion pipeline — decoupled spectral computation (handled by display pipeline)
        self.sample_rate_hz: int = 4000
        self.block_size: int = 128
        self.pipeline = LiveStreamingPipeline(
            buffer_duration_s=5.0,
            filter_low_hz=self.filter_low_hz,
            filter_high_hz=self.filter_high_hz,
            filter_order=4,
            enable_spectral_frame=False,
        )

        # Source management — Core Rule: starts with NO active source and NO streaming
        self.source_type: str = "none"
        self.source_path: Optional[str] = None
        self.source_session_id: Optional[str] = None
        self.active_source_name: str = "None"
        self._source_generator = None

        # Streaming loop state — Starts idle
        self.is_streaming: bool = False
        self.is_paused: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        self._active_connections: Set[Any] = set()

        # Session recorder
        self.recorder = SessionRecorder(output_dir=self.sessions_dir, wav_format="float32")
        self._recording_started_wall: float = 0.0

    @property
    def enable_legacy_signal_frames(self) -> bool:
        """Compatibility property; authoritative source is display_config.emit_legacy_signal_frames."""
        return self.display_config.emit_legacy_signal_frames

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "block_size": self.block_size,
            "sources": ["none", "hardware", "session", "realtime_wav", "synthetic_dev"],
            "filter_presets": list(FILTER_PRESETS.keys()),
            "max_buffer_seconds": 15,
            "device_runtime": {
                "transport": "native_usb_pending",
                "rev_a_proposal": "cdc_acm_under_review",
                "active_profile": self.device_runtime.profile.to_dict(),
            },
            "display_pipeline": {
                "target_display_hz": self.display_config.target_display_hz,
                "points_per_frame": self.display_config.points_per_frame,
                "spectral_update_hz": self.display_config.spectral_update_hz,
                "max_rolling_window_s": self.display_config.max_rolling_window_s,
                "emit_legacy_signal_frames": self.display_config.emit_legacy_signal_frames,
            },
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
            "device_state": self.device_runtime.state.value,
            "device_info": self.device_runtime.get_state_dict(),
            "connected_clients": len(self._active_connections),
            "display_telemetry": {
                "frames_produced": self.display_aggregator.total_display_frames_produced,
                "frames_dropped": self.display_aggregator.total_display_frames_dropped,
                "target_display_hz": self.display_config.target_display_hz,
            },
        }

    def register_client(self, websocket: Any) -> None:
        self._active_connections.add(websocket)
        session = ClientSession(websocket, queue_size=self.display_config.client_queue_size)
        session.start()
        self._clients[websocket] = session

    def unregister_client(self, websocket: Any) -> None:
        self._active_connections.discard(websocket)
        session = self._clients.pop(websocket, None)
        if session:
            session.stop()

    def publish_display_frame(self, frame: DisplayFrame) -> None:
        """Publish display frame to all connected clients with backpressure isolation."""
        frame_dict = frame.to_dict()
        dead = []
        for ws, session in list(self._clients.items()):
            if not session.is_alive:
                dead.append(ws)
                continue
            if session.push_display_frame(frame_dict):
                self.display_aggregator.total_display_frames_dropped += 1
        for ws in dead:
            self.unregister_client(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast control/state messages to all connected clients."""
        if not self._active_connections:
            return

        dead_clients = set()
        for ws in list(self._active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead_clients.add(ws)

        for dead in dead_clients:
            self.unregister_client(dead)

    def _create_source_generator(self):
        """Construct the generator for the active source."""
        if self.source_type == "none":
            return None
        elif self.source_type == "session" and self.source_session_id:
            src = create_session_source(
                self.source_session_id,
                sessions_dir=self.sessions_dir,
                block_size=self.block_size,
                realtime=False,
            )
            return src.blocks()
        elif self.source_type == "realtime_wav" and self.source_path:
            p = Path(self.source_path)
            if not p.exists():
                raise FileNotFoundError(f"Source WAV not found: {p}")
            src = WavSource(p, block_size=self.block_size)
            return src.blocks()
        elif self.source_type == "synthetic_dev":
            # Explicit engineering development mode ONLY
            src = MockPCGSource(
                sample_rate_hz=self.sample_rate_hz,
                heart_rate_bpm=72.0,
                block_size=self.block_size,
                duration_s=30.0,
            )
            return src.blocks()
        else:
            return None

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
            enable_spectral_frame=False,
        )
        return self.get_state_dict()

    def select_source(
        self,
        source_type: str,
        path: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Switch active stream source with strict validation.

        Does NOT silently fall back to mock on invalid requests.
        """
        # If switching away from hardware, stop device streaming cleanly
        if self.source_type == "hardware" and source_type != "hardware":
            self.device_runtime.stop_streaming()

        self.display_aggregator.reset()

        if source_type == "none":
            self.source_type = "none"
            self.source_path = None
            self.source_session_id = None
            self.active_source_name = "None"
            self.is_streaming = False
            self.is_paused = False
            self._source_generator = None

        elif source_type == "session":
            if not session_id:
                raise ValueError("session_id must be provided when source_type is 'session'")
            validate_session_id(session_id, self.sessions_dir)
            self.source_type = "session"
            self.source_path = None
            self.source_session_id = session_id
            self.active_source_name = f"Session Replay: {session_id}"
            self._source_generator = None
            self.is_streaming = True
            self.is_paused = False

        elif source_type == "realtime_wav":
            if not path:
                raise ValueError("path must be provided when source_type is 'realtime_wav'")
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"Source WAV not found: {p}")
            self.source_type = "realtime_wav"
            self.source_path = str(p)
            self.source_session_id = None
            self.active_source_name = f"Replay: {p.name}"
            self._source_generator = None
            self.is_streaming = True
            self.is_paused = False

        elif source_type in ("synthetic_dev", "mock"):
            # Explicit engineering test signal
            self.source_type = "synthetic_dev"
            self.source_path = None
            self.source_session_id = None
            self.active_source_name = "Synthetic Development Signal — Not Hardware"
            self._source_generator = None
            self.is_streaming = True
            self.is_paused = False

        elif source_type == "hardware":
            if self.device_runtime.state not in (DeviceState.READY, DeviceState.STREAMING):
                raise ValueError(
                    f"Hardware device not ready (current state: {self.device_runtime.state.value})"
                )
            self.source_type = "hardware"
            dev_id = self.device_runtime.get_state_dict().get("device_id") or "ESP32-S3"
            self.active_source_name = f"Hardware: {dev_id}"
            if self.device_runtime.capabilities:
                self.sample_rate_hz = self.device_runtime.capabilities.sample_rate_hz
                self.block_size = self.device_runtime.profile.negotiated_block_size
            self.device_runtime.start_streaming()
            self._source_generator = None
            self.is_streaming = True
            self.is_paused = False

        else:
            raise ValueError(f"Invalid or unsupported source type: {source_type!r}")

        return self.get_state_dict()

    def start_recording(self, source_label: Optional[str] = None) -> str:
        """Start recording incoming blocks into a new session.

        Requires an active stream and source.
        """
        if not self.is_streaming or self.source_type == "none":
            raise ValueError("Cannot record: no active stream or source is selected.")

        source = source_label or self.active_source_name
        dev_info = self.device_runtime.get_state_dict() if self.source_type == "hardware" else None

        sid = self.recorder.start(
            source=source,
            acquisition_mode=self.source_type,
            device_info=dev_info,
        )
        self._recording_started_wall = time.time()
        return sid

    def stop_recording(self, termination_reason: str = "completed") -> SessionMetadata:
        """Finalize and save the active recording session."""
        meta = self.recorder.stop(termination_reason=termination_reason)
        return meta

    def handle_device_disconnect(self, error_msg: Optional[str] = None) -> None:
        """Handle hardware device disconnect cleanly."""
        was_hardware = (self.source_type == "hardware")

        if was_hardware:
            # If recording was active from hardware, safely finalize with termination_reason
            if self.recorder.is_recording:
                try:
                    meta = self.recorder.stop(termination_reason="device_disconnected")
                    self.device_runtime.event_log.log(
                        "RECORDING_ABORTED",
                        f"Session recording {meta.session_id} finalized due to device disconnect",
                        severity="warning",
                        metadata={"session_id": meta.session_id},
                    )
                except Exception as e:
                    self.device_runtime.event_log.log(
                        "RECORDING_ABORT_ERROR",
                        f"Error while finalizing interrupted recording: {e}",
                        severity="error",
                    )

            self.is_streaming = False
            self.is_paused = False
            self.source_type = "none"
            self.active_source_name = "None"
            self._source_generator = None

        self.display_aggregator.reset()
        self.device_runtime.handle_disconnect(error_msg)

    def start_stream(self) -> None:
        if self.source_type != "none":
            self.is_streaming = True
            self.is_paused = False

    def pause_stream(self) -> None:
        self.is_paused = True

    def resume_stream(self) -> None:
        if self.source_type != "none":
            self.is_paused = False

    def stop_stream(self) -> None:
        self.is_streaming = False
        self.display_aggregator.reset()
        if self.source_type == "hardware":
            self.device_runtime.stop_streaming()

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

    async def ingest_device_packet(self, packet: DeviceSamplePacket) -> None:
        """Entry point for push-driven physical hardware sample packets.

        Called by the transport decoder when new physical packets arrive from USB.
        Flow:
        1. Only accept packets when hardware is actively STREAMING and stream manager is active
        2. Update DeviceIntegrityStats
        3. Drop CRC-failed packets without feeding DSP or recording
        4. Convert valid packet to SampleBlock (checks integer range, normalizes to float32)
        5. Process through DSP pipeline, record if active, and broadcast signal_frame
        """
        if (
            self.device_runtime.state != DeviceState.STREAMING
            or self.source_type != "hardware"
            or not self.is_streaming
            or self.is_paused
        ):
            return

        # Update integrity telemetry
        self.device_runtime.stats.record_packet(packet)

        # Drop CRC-failed packets without feeding DSP or recording
        if not packet.crc_ok:
            return

        # Adapt to SampleBlock (checks legal integer range and normalizes to float32)
        block = packet_to_sample_block(
            packet,
            sample_rate_hz=self.sample_rate_hz,
            profile=self.device_runtime.profile,
        )

        # Dispatch to shared processing, recording, and WebSocket broadcast
        await self._dispatch_sample_block(block)

    async def _dispatch_sample_block(self, block: SampleBlock) -> None:
        """Shared pipeline processing, session recording, and decoupled display publishing.

        Invoked by both pull-driven offline sources and push-driven hardware packets.
        """
        # 1. Process through full-rate DSP pipeline
        frame = self.pipeline.process_block(block)

        # 2. Record if session active (FULL-RATE: every valid sample recorded immediately)
        if self.recorder.is_recording:
            try:
                self.recorder.record_block(block)
            except Exception as e:
                await self.broadcast(make_error_message(f"Recording error: {e}", "RECORDING_ERROR"))

        # 3. Stream quality report
        quality_rep = self.pipeline.quality_monitor.report
        quality_summary = {
            "total_blocks": quality_rep.total_blocks,
            "dropped_blocks": quality_rep.dropped_blocks,
            "repeated_sequences": quality_rep.repeated_sequences,
            "sequence_discontinuities": quality_rep.sequence_discontinuities,
            "is_healthy": quality_rep.is_healthy,
        }

        # 4. Decoupled display frame aggregation
        display_frame = self.display_aggregator.add_block(
            raw_block=block,
            filtered_block=frame.filtered_block,
            quality_summary=quality_summary,
            recording_active=self.recorder.is_recording,
        )

        if display_frame is not None:
            self.publish_display_frame(display_frame)

        # 5. Legacy signal_frame broadcast if explicitly opted-in (compatibility/dev only)
        if self.display_config.emit_legacy_signal_frames:
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

        # 6. Yield briefly so client sender background tasks can dispatch
        await asyncio.sleep(0)

    async def _stream_loop(self) -> None:
        """Continuous background loop consuming blocks, filtering, and broadcasting."""
        while True:
            try:
                # Do not emit signal frames when idle, paused, or no source selected
                if not self.is_streaming or self.is_paused or self.source_type == "none":
                    await asyncio.sleep(0.05)
                    continue

                if self.source_type == "hardware":
                    # Hardware acquisition is push-driven via ingest_device_packet().
                    # The background generator loop idles while physical hardware is active.
                    await asyncio.sleep(0.05)
                    continue

                if self._source_generator is None:
                    self._source_generator = self._create_source_generator()
                    if self._source_generator is None:
                        self.is_streaming = False
                        await asyncio.sleep(0.05)
                        continue

                # Fetch next block
                try:
                    block: SampleBlock = next(self._source_generator)
                except StopIteration:
                    # Loop offline source for continuous playback
                    self._source_generator = self._create_source_generator()
                    if self._source_generator is None:
                        self.is_streaming = False
                        continue
                    block = next(self._source_generator)

                # Duration of current block in seconds
                block_duration = len(block.samples) / block.sample_rate_hz

                # Dispatch block through shared processing
                await self._dispatch_sample_block(block)

                # Wall-clock pacing
                await asyncio.sleep(block_duration)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.broadcast(make_error_message(f"Streaming error: {e}", "STREAM_ERROR"))
                await asyncio.sleep(0.1)
