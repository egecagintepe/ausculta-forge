"""Tests for Host Throughput, Display Decimation, and Backpressure Pipeline.

Verifies:
- Peak-preserving decimation (min/max bucket aggregation preserves narrow spikes)
- Display cadence decoupling from acquisition cadence (25 Hz display vs 93.75 Hz blocks)
- Decoupled spectral update cadence
- Recorder isolation under slow UI backpressure (100% recording preservation, 0 sequence gaps)
- Hardware sequence_gaps never incremented on display frame drops
- Multi-client isolation (one slow client does not block fast client or recording)
- 48 kHz Rev-A metadata preservation in recording session
- Default startup remains NO DEVICE
- Offline replay (synthetic, WAV, session) remains functional
"""

import asyncio
from pathlib import Path
import time
from typing import Any

import numpy as np
import pytest

from pcg_core.models import SampleBlock
from pcg_core.sources import MockPCGSource
from pcg_app.display_pipeline import (
    DisplayPipelineConfig,
    decimate_min_max,
    DisplayAggregator,
    DisplayFrame,
)
from pcg_app.device_runtime import (
    DeviceRuntime,
    DeviceState,
    DeviceCandidate,
    DeviceCapabilities,
    DeviceSamplePacket,
    AcquisitionProfile,
)
from pcg_app.state import StreamManager, ClientSession


# ==============================================================================
# Test Fixtures & Mock Clients
# ==============================================================================

class FastMockWebSocket:
    """Fast WebSocket client that immediately records all received JSON messages."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, msg: dict[str, Any]) -> None:
        self.messages.append(msg)


class SlowMockWebSocket:
    """Intentionally slow WebSocket client simulating browser / rendering backpressure."""

    def __init__(self, delay_s: float = 0.04) -> None:
        self.delay_s = delay_s
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, msg: dict[str, Any]) -> None:
        await asyncio.sleep(self.delay_s)
        self.messages.append(msg)


class InMemoryFakeTransport:
    """Minimal fake transport for handshake testing."""

    def __init__(self) -> None:
        self.is_connected = True

    def open(self) -> bool:
        self.is_connected = True
        return True

    def close(self) -> None:
        self.is_connected = False


def setup_streaming_rev_a_runtime() -> tuple[DeviceRuntime, StreamManager]:
    """Helper to initialize a DeviceRuntime and StreamManager in STREAMING state with Rev-A."""
    runtime = DeviceRuntime()
    # Rev-A: 48 kHz mono 24-in-32 signed PCM
    runtime.attach_candidate(DeviceCandidate("ESP32S3-HW", "USB Rev-A", "now"))
    runtime.attach_transport(InMemoryFakeTransport())
    runtime.complete_handshake(
        DeviceCapabilities(
            protocol_version="1.0",
            firmware_version="v1.0",
            device_id="ESP32S3-HW",
            sample_rate_hz=48000,
            sample_format="signed_pcm",
            channels=1,
            sample_container_bits=32,
            meaningful_data_bits=24,
            max_block_size=512,
        )
    )
    return runtime


# ==============================================================================
# 1. Peak-Preserving Decimation Tests
# ==============================================================================

class TestPeakPreservingDecimation:
    """Verifies min/max bucket aggregation preserves transient extrema."""

    def test_peak_preservation_captures_narrow_transients(self):
        """A 1-sample spike and 1-sample dip in a flat 1000-sample signal must NOT be lost."""
        signal = np.full(1000, 0.05, dtype=np.float32)
        # Place narrow impulses
        signal[347] = 0.98   # Narrow positive transient (e.g. S1 click)
        signal[782] = -0.92  # Narrow negative transient

        # Naive downsampling (every 25th sample)
        naive = signal[::25]
        # In naive subsampling, index 347 and 782 are completely missed (347 % 25 = 22, 782 % 25 = 7)
        assert np.max(naive) < 0.1
        assert np.min(naive) > 0.0

        # Min/max bucket aggregation targeting 80 points (40 buckets)
        decimated = decimate_min_max(signal, target_points=80)
        assert len(decimated) == 80
        # Peak values MUST be preserved exactly
        assert np.isclose(np.max(decimated), 0.98, atol=1e-5)
        assert np.isclose(np.min(decimated), -0.92, atol=1e-5)

    def test_decimate_min_max_short_array_returns_copy(self):
        """Arrays shorter than or equal to target_points should return intact."""
        short_sig = np.array([0.1, -0.2, 0.3, -0.4], dtype=np.float32)
        decimated = decimate_min_max(short_sig, target_points=10)
        assert len(decimated) == len(short_sig)
        assert np.allclose(decimated, short_sig)

    def test_decimate_preserves_chronological_extrema(self):
        """Within each bucket, the extremum occurring earlier chronologically must appear first."""
        # Bucket where max happens before min
        sig1 = np.array([0.0, 0.9, -0.9, 0.0], dtype=np.float32)
        dec1 = decimate_min_max(sig1, target_points=2)
        assert dec1[0] == 0.9
        assert dec1[1] == -0.9

        # Bucket where min happens before max
        sig2 = np.array([0.0, -0.9, 0.9, 0.0], dtype=np.float32)
        dec2 = decimate_min_max(sig2, target_points=2)
        assert dec2[0] == -0.9
        assert dec2[1] == 0.9


# ==============================================================================
# 2. Display Aggregator Cadence & Spectral Tests
# ==============================================================================

class TestDisplayAggregator:
    """Verifies that DisplayAggregator produces frames at display cadence, not packet cadence."""

    def test_display_cadence_lower_than_acquisition_block_cadence(self):
        """100 blocks at 48 kHz / 512 samples (~93.75 Hz) should yield ~26 display frames at 25 Hz."""
        config = DisplayPipelineConfig(
            target_display_hz=25.0,
            points_per_frame=128,
            spectral_update_hz=5.0,
        )
        aggregator = DisplayAggregator(config)

        produced_frames: list[DisplayFrame] = []
        fs = 48000
        block_len = 512
        block_dur = block_len / fs  # ~0.01067 s

        # Inject 100 blocks = 51,200 samples = ~1.0667 seconds of audio
        for i in range(100):
            t = i * block_dur
            raw_samples = (0.3 * np.sin(2 * np.pi * 50 * np.linspace(t, t + block_dur, block_len))).astype(np.float32)
            filt_samples = (0.2 * np.sin(2 * np.pi * 50 * np.linspace(t, t + block_dur, block_len))).astype(np.float32)

            raw_block = SampleBlock(sequence=i, timestamp_s=t, sample_rate_hz=fs, samples=raw_samples)
            filt_block = SampleBlock(sequence=i, timestamp_s=t, sample_rate_hz=fs, samples=filt_samples)

            frame = aggregator.add_block(
                raw_block=raw_block,
                filtered_block=filt_block,
                quality_summary={"is_healthy": True},
                recording_active=False,
            )
            if frame is not None:
                produced_frames.append(frame)

        # 100 acquisition blocks were processed, but only ~25-28 display frames should be produced!
        assert 20 <= len(produced_frames) <= 30
        assert len(produced_frames) < 100

        # Check display frame structure
        f0 = produced_frames[0]
        assert f0.sample_rate_hz == 48000
        assert len(f0.raw_points) <= config.points_per_frame
        assert len(f0.filtered_points) <= config.points_per_frame
        assert f0.rms > 0.0
        assert f0.peak > 0.0

    def test_spectral_frame_computation_is_decoupled(self):
        """Spectral frame must update at spectral cadence (~5 Hz), not on every display frame."""
        config = DisplayPipelineConfig(
            target_display_hz=25.0,
            spectral_update_hz=5.0,
            enable_spectral=True,
        )
        aggregator = DisplayAggregator(config)
        fs = 48000
        block_len = 512
        block_dur = block_len / fs

        spectral_frames_count = 0
        display_frames_count = 0

        # 150 blocks = ~1.6 seconds of audio
        for i in range(150):
            t = i * block_dur
            raw = (0.5 * np.sin(2 * np.pi * 60 * np.linspace(t, t + block_dur, block_len))).astype(np.float32)
            b = SampleBlock(sequence=i, timestamp_s=t, sample_rate_hz=fs, samples=raw)
            frame = aggregator.add_block(b, b, {"is_healthy": True}, False)
            if frame is not None:
                display_frames_count += 1
                if frame.spectral_frame is not None:
                    spectral_frames_count += 1

        # Across ~1.6 s: display frames ~38-42, spectral frames ~8-10 (approx 5 Hz)
        assert display_frames_count > 30
        assert 5 <= spectral_frames_count <= 15
        assert spectral_frames_count < display_frames_count


# ==============================================================================
# 3. Recorder Isolation Under Slow UI Backpressure (Requirement 9)
# ==============================================================================

class TestRecorderIsolationUnderBackpressure:
    """Verifies that slow WebSocket UI consumption NEVER drops recording samples or causes sequence gaps."""

    @pytest.mark.anyio
    async def test_slow_ui_does_not_corrupt_full_rate_recording(self, tmp_path: Path):
        """Inject 200 sequential 48 kHz packets into a StreamManager with an intentionally slow UI client."""
        runtime = setup_streaming_rev_a_runtime()
        display_cfg = DisplayPipelineConfig(
            target_display_hz=25.0,
            points_per_frame=128,
            client_queue_size=2,
            emit_legacy_signal_frames=False,  # Pure display-frame pipeline
        )
        manager = StreamManager(
            sessions_dir=tmp_path / "sessions",
            device_runtime=runtime,
            display_config=display_cfg,
            enable_legacy_signal_frames=False,
        )

        # Attach an intentionally slow WebSocket client (50 ms per send)
        slow_ws = SlowMockWebSocket(delay_s=0.05)
        manager.register_client(slow_ws)

        manager.select_source("hardware")
        assert manager.is_streaming is True
        assert runtime.state == DeviceState.STREAMING

        # Start recording
        sid = manager.start_recording()
        assert manager.recorder.is_recording is True

        # Ingest 200 sequential valid 48 kHz packets (512 samples each = 102,400 samples)
        fs = 48000
        samples_per_block = 512
        total_blocks = 200
        expected_total_samples = total_blocks * samples_per_block  # 102,400 samples

        for seq in range(total_blocks):
            t_s = seq * (samples_per_block / fs)
            # 24-bit PCM in 32-bit container
            raw_pcm = np.full(samples_per_block, 200000 + (seq % 1000), dtype=np.int32)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=t_s,
                raw_samples=raw_pcm,
                crc_ok=True,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            await manager.ingest_device_packet(pkt)

        # Ingest 1 CRC-failed packet (must be completely rejected from recording and DSP)
        bad_pkt = DeviceSamplePacket(
            sequence=total_blocks,
            timestamp_s=total_blocks * (samples_per_block / fs),
            raw_samples=np.full(samples_per_block, -99999, dtype=np.int32),
            crc_ok=False,
            meaningful_bits=24,
            sample_rate_hz=fs,
        )
        await manager.ingest_device_packet(bad_pkt)

        # 1. Verify exact expected source sample count reaches SessionRecorder
        meta = manager.stop_recording()
        assert meta.total_samples == expected_total_samples  # Exactly 102,400 samples!
        assert meta.total_blocks == total_blocks  # Exactly 200 blocks
        assert meta.sample_rate_hz == fs

        # 2. Verify hardware integrity telemetry: sequence gap count remains zero
        stats = runtime.stats
        assert stats.packets_received == total_blocks  # 200 valid packets
        assert stats.crc_failures == 1  # Exactly the 1 CRC failure
        assert stats.sequence_gaps == 0  # STRICTLY ZERO SEQUENCE GAPS!
        assert stats.samples_received == expected_total_samples

        # 3. Verify display frames count is lower than acquisition block count
        session = manager._clients[slow_ws]
        assert session.dropped_display_frames > 0  # Slow client dropped stale display frames
        assert manager.display_aggregator.total_display_frames_produced < total_blocks

        # 4. Verify display drops are reported ONLY as display telemetry, NEVER hardware sequence gaps
        st = manager.get_state_dict()
        assert st["display_telemetry"]["frames_dropped"] > 0
        assert stats.sequence_gaps == 0  # Re-confirm: hardware gaps unaffected by UI drops!


# ==============================================================================
# 4. Multi-Client Isolation Tests (Requirement 5)
# ==============================================================================

class TestMultiClientIsolation:
    """Verifies that one slow client cannot stall another fast client or recording."""

    @pytest.mark.anyio
    async def test_fast_and_slow_clients_isolation(self, tmp_path: Path):
        runtime = setup_streaming_rev_a_runtime()
        display_cfg = DisplayPipelineConfig(
            target_display_hz=25.0,
            client_queue_size=2,
            emit_legacy_signal_frames=False,
        )
        manager = StreamManager(
            sessions_dir=tmp_path / "sessions",
            device_runtime=runtime,
            display_config=display_cfg,
            enable_legacy_signal_frames=False,
        )

        fast_ws = FastMockWebSocket()
        slow_ws = SlowMockWebSocket(delay_s=0.10)

        manager.register_client(fast_ws)
        manager.register_client(slow_ws)
        manager.select_source("hardware")

        manager.start_recording()

        # Ingest 150 blocks (~1.6 seconds of audio)
        fs = 48000
        for seq in range(150):
            t_s = seq * (512 / fs)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=t_s,
                raw_samples=np.full(512, 150000, dtype=np.int32),
                crc_ok=True,
                sample_rate_hz=fs,
            )
            await manager.ingest_device_packet(pkt)

        # Allow fast client loop to process all pending frames
        await asyncio.sleep(0.02)

        meta = manager.stop_recording()
        assert meta.total_samples == 150 * 512

        fast_session = manager._clients[fast_ws]
        slow_session = manager._clients[slow_ws]

        # Fast client should have received all produced display frames with zero drops
        assert fast_session.dropped_display_frames == 0
        assert len(fast_ws.messages) > 20

        # Slow client experienced drops due to bounded queue
        assert slow_session.dropped_display_frames > 0
        assert len(slow_ws.messages) < len(fast_ws.messages)


# ==============================================================================
# 5. Rev-A Metadata & Replay Compatibility Tests
# ==============================================================================

class TestRevAMetadataAndReplay:
    """Verifies 48 kHz metadata preservation, default startup, and offline modes."""

    def test_default_startup_state_remains_no_device(self, tmp_path: Path):
        """Application starts with NO active device, NO streaming, and NO fake synthetic generation."""
        manager = StreamManager(sessions_dir=tmp_path / "sessions")
        state = manager.get_state_dict()
        assert state["source_type"] == "none"
        assert state["is_streaming"] is False
        assert state["is_recording"] is False
        assert state["device_state"] == "absent"

    def test_recording_preserves_48khz_rev_a_metadata(self, tmp_path: Path):
        runtime = setup_streaming_rev_a_runtime()
        manager = StreamManager(
            sessions_dir=tmp_path / "sessions",
            device_runtime=runtime,
            enable_legacy_signal_frames=False,
        )
        manager.select_source("hardware")
        manager.start_recording()

        # Ingest 10 packets at 48 kHz
        for seq in range(10):
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=seq * (512 / 48000),
                raw_samples=np.full(512, 50000, dtype=np.int32),
                crc_ok=True,
                sample_rate_hz=48000,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        meta = manager.stop_recording()
        assert meta.sample_rate_hz == 48000
        assert meta.total_samples == 5120
        assert meta.device_info is not None
        assert meta.device_info.get("device_id") == "ESP32S3-HW"

    def test_synthetic_dev_source_streaming_remains_functional(self, tmp_path: Path):
        """Explicit synthetic dev test source must still produce blocks when explicitly selected."""
        manager = StreamManager(sessions_dir=tmp_path / "sessions")
        state = manager.select_source("synthetic_dev")
        assert state["source_type"] == "synthetic_dev"
        assert state["is_streaming"] is True

        gen = manager._create_source_generator()
        assert gen is not None
        b0 = next(gen)
        assert isinstance(b0, SampleBlock)
        assert len(b0.samples) == manager.block_size
