"""AuscultaForge — Application State & Live Stream Orchestration Manager.

Coordinates real-time PCG signal processing, device lifecycle, streaming DSP filtering,
quality monitoring, and session recording in a clean, UI-independent layer.

CORE PRODUCT RULE:
The application starts with NO device connected and NO active stream.
Synthetic sources never activate automatically and never masquerade as physical hardware.
"""

import asyncio
import math
from datetime import datetime, timezone
from pathlib import Path
import time
import threading
from typing import Any, Callable, Optional, Set

import numpy as np

from pcg_core.models import SampleBlock
from pcg_core.sources import MockPCGSource, WavSource, RealtimeWavSource
from pcg_core.streaming import LiveStreamingPipeline
from pcg_core.validation import load_wav_as_float32
from pcg_core.experiment import compute_file_sha256
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
        self._owner_loop = None
        self._delivery_lock = threading.Lock()
        self._pending_frame = None

    def start(self) -> None:
        if self.is_alive and (self._sender_task is None or self._sender_task.done()):
            try:
                loop = asyncio.get_running_loop()
                self._owner_loop = loop
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

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if self._owner_loop and current_loop is not self._owner_loop:
            # Coalesce before scheduling: a stalled UI has at most one callback pending.
            with self._delivery_lock:
                already_pending = self._pending_frame is not None
                self._pending_frame = frame_dict
                if already_pending:
                    self.dropped_display_frames += 1
                else:
                    try:
                        self._owner_loop.call_soon_threadsafe(self._deliver_pending_frame)
                    except RuntimeError:
                        self._pending_frame = None
                        self.is_alive = False
            return already_pending

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

    def _deliver_pending_frame(self) -> None:
        with self._delivery_lock:
            frame, self._pending_frame = self._pending_frame, None
        if frame is not None:
            self.push_display_frame(frame)

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
        self._last_rec_broadcast_time: float = 0.0

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
        if frame_dict.get("spectral_frame") is not None:
            frame_dict["spectral_frame"]["acquisition_origin"] = self.acquisition_origin()
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
        """Update the active bandpass; omitted arguments preserve current settings."""
        if preset is not None:
            if preset in FILTER_PRESETS:
                next_preset = preset
                next_low_hz, next_high_hz = FILTER_PRESETS[preset]
            elif preset == "custom":
                next_preset = "custom"
                next_low_hz, next_high_hz = self.filter_low_hz, self.filter_high_hz
            else:
                raise ValueError(f"Unknown filter preset: {preset}")
        else:
            next_preset = self.filter_preset
            next_low_hz, next_high_hz = self.filter_low_hz, self.filter_high_hz

        if low_hz is not None:
            next_low_hz = float(low_hz)
            next_preset = "custom"
        if high_hz is not None:
            next_high_hz = float(high_hz)
            next_preset = "custom"
        if not (math.isfinite(next_low_hz) and math.isfinite(next_high_hz)
                and 0 < next_low_hz < next_high_hz):
            raise ValueError("Filter cutoffs must be finite and satisfy 0 < low_hz < high_hz")

        changed = (
            next_preset != self.filter_preset
            or next_low_hz != self.filter_low_hz
            or next_high_hz != self.filter_high_hz
        )
        self.filter_preset = next_preset
        self.filter_low_hz = next_low_hz
        self.filter_high_hz = next_high_hz

        # Re-initialize pipeline with new cutoffs
        if changed:
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
            self.device_runtime.stop_supervisor()
            self.device_runtime.stop_streaming()

        self.display_aggregator.reset()
        self.pipeline.notify_rewind()

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
            _, source_fs = load_wav_as_float32(self.sessions_dir / session_id / "raw.wav")
            self.sample_rate_hz = source_fs
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
            _, source_fs = load_wav_as_float32(p)
            self.sample_rate_hz = source_fs
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
            self._source_generator = None
            self.is_streaming = True
            self.is_paused = False

            # If physical transport and decoder are configured, start the supervisor read loop
            if (
                self.device_runtime.active_transport is not None
                and self.device_runtime.decoder is not None
                and not (self.device_runtime.supervisor and self.device_runtime.supervisor.is_running)
            ):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                def _on_pkt(pkt: DeviceSamplePacket) -> None:
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(self.ingest_device_packet(pkt), loop)
                    else:
                        asyncio.run(self.ingest_device_packet(pkt))

                def _on_disc(reason: str) -> None:
                    if loop and loop.is_running():
                        loop.call_soon_threadsafe(self.handle_device_disconnect, reason)
                    else:
                        self.handle_device_disconnect(reason)

                self.device_runtime.start_supervisor(
                    on_packet=_on_pkt,
                    on_disconnect=_on_disc,
                )
            else:
                self.device_runtime.start_streaming()

        else:
            raise ValueError(f"Invalid or unsupported source type: {source_type!r}")

        self.pipeline = LiveStreamingPipeline(
            buffer_duration_s=5.0, filter_low_hz=self.filter_low_hz,
            filter_high_hz=self.filter_high_hz, filter_order=4, enable_spectral_frame=False,
        )
        return self.get_state_dict()

    def acquisition_origin(self) -> str:
        if self.source_type != "hardware":
            return self.source_type
        engine = self.device_runtime.canonical_engine
        if engine is None:
            return "hardware_unverified"
        if engine.is_simulated:
            return "software_simulated"
        config = engine.session.active_start_config
        if config is None:
            return "hardware_unverified"
        return "physical_deterministic_g1" if config.source_mode == 1 else "physical_i2s_unqualified"

    def start_recording(self, source_label: Optional[str] = None) -> str:
        """Start recording incoming blocks into a new session.

        Requires an active stream and source.
        """
        if not self.is_streaming or self.source_type == "none":
            raise ValueError("Cannot record: no active stream or source is selected.")

        source = source_label or self.active_source_name
        is_hardware = (self.source_type == "hardware")
        simulated = is_hardware and bool(getattr(self.device_runtime.canonical_engine, "is_simulated", False))
        dev_info = self.device_runtime.get_state_dict() if is_hardware and not simulated else None

        if is_hardware:
            if self.device_runtime.capabilities:
                wire_fmt = (
                    f"{self.device_runtime.capabilities.sample_format}_"
                    f"{self.device_runtime.capabilities.meaningful_data_bits}bit_in_"
                    f"{self.device_runtime.capabilities.sample_container_bits}bit_slot"
                )
            else:
                wire_fmt = (
                    f"signed_pcm_{self.device_runtime.profile.meaningful_data_bits}bit_in_"
                    f"{self.device_runtime.profile.sample_container_bits}bit_container"
                )
        else:
            wire_fmt = "synthetic_or_offline_float32"

        processing_profile = {
            "filter_preset": self.filter_preset,
            "low_hz": self.filter_low_hz,
            "high_hz": self.filter_high_hz,
            "acquisition_origin": self.acquisition_origin(),
        }
        if self.source_type == "realtime_wav" and self.source_path:
            processing_profile["source_wav_sha256"] = compute_file_sha256(Path(self.source_path))
        if self.source_type == "session" and self.source_session_id:
            processing_profile["replay_session_id"] = self.source_session_id
            original = get_session(self.source_session_id, self.sessions_dir)
            processing_profile["replay_origin"] = {
                key: original.get(key) for key in ("source", "acquisition_mode", "raw_wav_sha256", "processing_profile")
            }

        sid = self.recorder.start(
            source=source,
            acquisition_mode="software_simulated" if simulated else self.source_type,
            device_info=dev_info,
            wire_format=wire_fmt,
            processing_profile=processing_profile,
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
        if self.recorder.is_recording and self._active_connections:
            rec_msg = make_recording_state_message(
                is_recording=True,
                session_id=self.recorder.session_id,
                elapsed_seconds=self.recorder.elapsed_seconds,
                samples_recorded=self.recorder.total_samples,
                blocks_recorded=self.recorder.total_blocks,
                source=self.recorder.source,
                sample_rate_hz=self.recorder.sample_rate_hz or self.sample_rate_hz,
            )
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(self.broadcast(rec_msg), loop)
            except RuntimeError:
                pass

    def resume_stream(self) -> None:
        if self.source_type != "none":
            self.display_aggregator.reset()
            self.pipeline.notify_rewind()
            self.is_paused = False
            if self.recorder.is_recording and self._active_connections:
                rec_msg = make_recording_state_message(
                    is_recording=True,
                    session_id=self.recorder.session_id,
                    elapsed_seconds=self.recorder.elapsed_seconds,
                    samples_recorded=self.recorder.total_samples,
                    blocks_recorded=self.recorder.total_blocks,
                    source=self.recorder.source,
                    sample_rate_hz=self.recorder.sample_rate_hz or self.sample_rate_hz,
                )
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(self.broadcast(rec_msg), loop)
                except RuntimeError:
                    pass

    def stop_stream(self) -> None:
        self.is_streaming = False
        self.display_aggregator.reset()
        self.pipeline.notify_rewind()
        if self.source_type == "hardware":
            self.device_runtime.stop_supervisor()
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

    def ingest_device_packet_sync(self, packet: DeviceSamplePacket) -> bool:
        """Synchronous entry point for push-driven physical hardware sample packets.

        Called directly by the transport worker thread without event-loop overhead or contention.
        Guarantees full-rate 48 kHz ingestion, continuous DSP filtering, and bit-preserving recording.
        """
        if (
            self.device_runtime.state != DeviceState.STREAMING
            or self.source_type != "hardware"
            or not self.is_streaming
            or self.is_paused
        ):
            return False

        # Update integrity telemetry
        self.device_runtime.stats.record_packet(packet)

        # Drop CRC-failed packets without feeding DSP or recording
        if not packet.crc_ok:
            return False

        # Adapt to SampleBlock (checks legal integer range and normalizes to float32)
        block = packet_to_sample_block(
            packet,
            sample_rate_hz=self.sample_rate_hz,
            profile=self.device_runtime.profile,
        )

        # Preserve acquisition evidence even if downstream DSP fails.
        if self.recorder.is_recording:
            try:
                self.recorder.record_block(block)
                now = time.monotonic()
                if now - self._last_rec_broadcast_time >= 0.2:
                    self._last_rec_broadcast_time = now
                    rec_msg = make_recording_state_message(
                        is_recording=True,
                        session_id=self.recorder.session_id,
                        elapsed_seconds=self.recorder.elapsed_seconds,
                        samples_recorded=self.recorder.total_samples,
                        blocks_recorded=self.recorder.total_blocks,
                        source=self.recorder.source,
                        sample_rate_hz=self.recorder.sample_rate_hz or self.sample_rate_hz,
                    )
                    if self._active_connections:
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.run_coroutine_threadsafe(self.broadcast(rec_msg), loop)
                        except RuntimeError:
                            pass
            except Exception as e:
                self.device_runtime.event_log.log(
                    "RECORDING_WRITE_ERROR",
                    f"Error writing block to active session: {e}",
                    severity="error",
                )
                raise RuntimeError("Raw recording write failed") from e

        frame = self.pipeline.process_block(block)

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
        return True

    async def ingest_device_packet(self, packet: DeviceSamplePacket) -> None:
        """Async entry point for push-driven physical hardware sample packets."""
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
        # Preserve acquisition evidence before downstream DSP.
        if self.recorder.is_recording:
            try:
                self.recorder.record_block(block)
                now = time.monotonic()
                if now - self._last_rec_broadcast_time >= 0.2:
                    self._last_rec_broadcast_time = now
                    rec_msg = make_recording_state_message(
                        is_recording=True,
                        session_id=self.recorder.session_id,
                        elapsed_seconds=self.recorder.elapsed_seconds,
                        samples_recorded=self.recorder.total_samples,
                        blocks_recorded=self.recorder.total_blocks,
                        source=self.recorder.source,
                        sample_rate_hz=self.recorder.sample_rate_hz or self.sample_rate_hz,
                    )
                    await self.broadcast(rec_msg)
            except Exception as e:
                await self.broadcast(make_error_message(f"Recording error: {e}", "RECORDING_ERROR"))
                raise RuntimeError("Raw recording write failed") from e

        frame = self.pipeline.process_block(block)

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
                    # Normal EOF reached: if recording is active, safely finalize session
                    if self.recorder.is_recording:
                        try:
                            meta = self.recorder.stop(termination_reason="completed")
                            rec_msg = make_recording_state_message(
                                is_recording=False,
                                session_id=meta.session_id,
                                elapsed_seconds=meta.duration_s,
                                samples_recorded=meta.total_samples,
                                blocks_recorded=meta.total_blocks,
                                source=meta.source,
                                sample_rate_hz=meta.sample_rate_hz,
                            )
                            await self.broadcast(rec_msg)
                        except Exception:
                            pass
                    # Acknowledge conscious EOF loop wrap
                    self.pipeline.notify_rewind()
                    self.display_aggregator.reset()
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
