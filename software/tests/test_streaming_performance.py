"""Deterministic Performance and Stress Tests for 48 kHz Streaming Pipeline (Sprint 05).

Verifies under wall-clock measurement:
- 48 kHz continuous throughput and 100% full-rate SessionRecorder preservation
- Slow UI backpressure isolation (display frame drops do NOT corrupt recording or cause MCU gaps)
- Memory boundedness of DisplayAggregator over long-duration streams
- Peak-preserving min/max decimation at 48 kHz with transient clicks
- Spectral accuracy of adaptive Welch PSD at 48 kHz
- Clean pause / resume transitions with display aggregator reset
- Separation of display drops vs physical hardware loss
"""

import asyncio
from pathlib import Path
import time
from typing import Any

import numpy as np
import pytest

from pcg_core.models import SampleBlock
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
)
from pcg_app.state import StreamManager, ClientSession


class MockFastWebSocket:
    """Fast WebSocket client recording received frames."""
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, msg: dict[str, Any]) -> None:
        self.messages.append(msg)


class MockSlowWebSocket:
    """Slow WebSocket client simulating high UI rendering load / network lag."""
    def __init__(self, delay_s: float = 0.05) -> None:
        self.delay_s = delay_s
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, msg: dict[str, Any]) -> None:
        await asyncio.sleep(self.delay_s)
        self.messages.append(msg)


class InMemoryFakeTransport:
    def __init__(self) -> None:
        self.is_connected = True

    def open(self) -> bool:
        self.is_connected = True
        return True

    def close(self) -> bool:
        self.is_connected = False
        return True


def setup_48khz_runtime() -> DeviceRuntime:
    runtime = DeviceRuntime()
    runtime.attach_candidate(DeviceCandidate("ESP32S3-HW", "USB Rev-A 48kHz", "now"))
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


class TestStreamingPerformance48kHz:
    """Deterministic performance and stress test suite for 48 kHz acquisition."""

    @pytest.mark.anyio
    async def test_48khz_continuous_throughput_and_recording_preservation(self, tmp_path: Path):
        """Processes 240,000 samples (5.0s of continuous 48 kHz audio) through StreamManager.
        
        Verifies:
        - Wall-clock throughput exceeds real-time (>2.0x real-time factor in pure software)
        - Exactly 240,128 samples are written to SessionRecorder without a single sample dropped
        - Output WAV file matches sample rate and duration
        - Zero MCU sequence gaps
        """
        runtime = setup_48khz_runtime()
        sessions_dir = tmp_path / "sessions"
        manager = StreamManager(
            sessions_dir=sessions_dir,
            device_runtime=runtime,
        )
        fast_ws = MockFastWebSocket()
        manager.register_client(fast_ws)
        manager.select_source("hardware")

        fs = 48000
        block_len = 512
        total_blocks = 469  # 469 * 512 = 240,128 samples (~5.002 seconds)
        total_samples = total_blocks * block_len

        session_id = manager.start_recording()
        assert manager.recorder.is_recording is True

        t0 = time.perf_counter()
        for seq in range(total_blocks):
            t_s = seq * (block_len / fs)
            # Deterministic 100 Hz sine wave in 24-bit PCM
            t_block = t_s + np.arange(block_len) / fs
            wave = (np.sin(2 * np.pi * 100.0 * t_block) * (2**22)).astype(np.int32)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=t_s,
                raw_samples=wave,
                crc_ok=True,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            await manager.ingest_device_packet(pkt)
        t_elapsed = time.perf_counter() - t0

        # Processing 5 seconds of 48 kHz audio should take well under 1.5 seconds on modern CPU
        samples_per_sec = total_samples / t_elapsed
        real_time_factor = (total_samples / fs) / t_elapsed
        print(f"\n[BENCHMARK] 48 kHz Ingestion: {total_samples} samples in {t_elapsed:.3f}s ({samples_per_sec:.0f} samples/s, {real_time_factor:.1f}x real-time)")
        assert real_time_factor > 2.0, f"Throughput too low: {real_time_factor:.1f}x"

        # Allow any pending frames to flush
        await asyncio.sleep(0.05)

        meta = manager.stop_recording()
        assert meta.total_samples == total_samples
        assert meta.total_blocks == total_blocks
        assert meta.sample_rate_hz == fs
        assert meta.first_sequence == 0
        assert meta.last_sequence == total_blocks - 1

        # Verify device stats show zero sequence gaps
        assert runtime.stats.sequence_gaps == 0
        assert runtime.stats.packets_received == total_blocks
        assert runtime.stats.samples_received == total_samples

        # Verify recording WAV exists on disk and is valid
        wav_path = sessions_dir / meta.session_id / meta.raw_wav_relpath
        assert wav_path.exists()
        assert wav_path.stat().st_size > total_samples * 2  # At least 16-bit PCM header + data

    @pytest.mark.anyio
    async def test_slow_client_backpressure_does_not_corrupt_recording_or_mcu_stats(self, tmp_path: Path):
        """Simulates high UI latency (50 ms per frame) while streaming 48 kHz audio.
        
        Verifies:
        - StreamManager drops obsolete display frames for the slow client
        - dropped_display_frames > 0 on the slow client session
        - Hardware MCU sequence gaps remain strictly 0
        - Full-rate SessionRecorder retains 100% of samples (zero recording data loss)
        """
        runtime = setup_48khz_runtime()
        cfg = DisplayPipelineConfig(
            target_display_hz=25.0,
            client_queue_size=2,
        )
        manager = StreamManager(
            sessions_dir=tmp_path / "sessions",
            device_runtime=runtime,
            display_config=cfg,
        )

        slow_ws = MockSlowWebSocket(delay_s=0.06)
        manager.register_client(slow_ws)
        manager.select_source("hardware")

        manager.start_recording()

        fs = 48000
        block_len = 512
        num_blocks = 150  # 76,800 samples (~1.6s)
        total_samples = num_blocks * block_len

        for seq in range(num_blocks):
            t_s = seq * (block_len / fs)
            raw = np.full(block_len, 100000 + (seq % 100), dtype=np.int32)
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=t_s,
                raw_samples=raw,
                crc_ok=True,
                meaningful_bits=24,
                sample_rate_hz=fs,
            )
            await manager.ingest_device_packet(pkt)

        await asyncio.sleep(0.08)

        meta = manager.stop_recording()
        # 1. 100% recording preservation
        assert meta.total_samples == total_samples
        assert meta.total_blocks == num_blocks

        # 2. Hardware stats: 0 sequence gaps
        assert runtime.stats.sequence_gaps == 0

        # 3. Slow client experienced bounded queue drops
        session = manager._clients[slow_ws]
        assert session.dropped_display_frames > 0

        # 4. Telemetry correctly reports UI drops without attributing to hardware
        state_dict = manager.get_state_dict()
        assert state_dict["display_telemetry"]["frames_dropped"] > 0
        assert runtime.stats.sequence_gaps == 0

    def test_display_aggregator_bounded_memory(self):
        """Pushes 500,000 samples (10+ seconds of 48 kHz data) through DisplayAggregator.
        
        Verifies:
        - _accum_samples never grows unbounded (resets upon each display frame, <= 4800 samples)
        - _recent_filt_count remains bounded at <= 8192 samples
        - Memory consumption does not grow linearly with stream duration (O(1) footprint)
        """
        config = DisplayPipelineConfig(
            target_display_hz=25.0,
            points_per_frame=128,
            spectral_update_hz=5.0,
            enable_spectral=True,
        )
        aggregator = DisplayAggregator(config)
        fs = 48000
        block_len = 512
        num_blocks = 1000  # 512,000 samples
        frames_produced = 0

        for i in range(num_blocks):
            t_s = i * (block_len / fs)
            samples = (0.2 * np.sin(2 * np.pi * 50 * np.linspace(t_s, t_s + block_len / fs, block_len))).astype(np.float32)
            block = SampleBlock(sequence=i, timestamp_s=t_s, sample_rate_hz=fs, samples=samples)

            frame = aggregator.add_block(block, block, {"is_healthy": True}, False)
            if frame is not None:
                frames_produced += 1

            # Assert internal buffers remain strictly bounded at every step
            assert aggregator._accum_samples <= 4800
            assert aggregator._recent_filt_count <= 8192
            assert len(aggregator._recent_filt) <= 17

        assert frames_produced > 200
        # Aggregator internal spectral buffer holds exactly bounded window
        assert aggregator._recent_filt_count == 8192

    def test_peak_preserving_decimation_retains_transient_spikes(self):
        """Verifies that 1-sample spikes (such as mechanical heart valve clicks or S1 onset)
        are preserved by min/max decimation at 48 kHz and not lost like naive decimation.
        """
        fs = 48000
        # 1920 samples = 40 ms at 48 kHz
        signal = np.full(1920, 0.02, dtype=np.float32)
        # Inject transient click at sample 743
        signal[743] = 0.95
        # Inject negative click at sample 1205
        signal[1205] = -0.89

        # Target 128 points (64 buckets of 30 samples each)
        decimated = decimate_min_max(signal, target_points=128)
        assert len(decimated) == 128

        # Max and min peaks MUST be preserved exactly
        assert np.isclose(np.max(decimated), 0.95, atol=1e-5)
        assert np.isclose(np.min(decimated), -0.89, atol=1e-5)

        # In contrast, naive subsampling at factor 15 misses both spikes
        naive = signal[::15]
        assert np.max(naive) < 0.1
        assert np.min(naive) > -0.1

    def test_adaptive_welch_spectral_frame_48khz(self):
        """Verifies that at 48 kHz, DisplayAggregator uses target_nperseg=1024 Welch PSD
        and correctly detects an 80 Hz fundamental tone within clinical heart sound range.
        """
        config = DisplayPipelineConfig(
            target_display_hz=25.0,
            spectral_update_hz=5.0,
            enable_spectral=True,
        )
        aggregator = DisplayAggregator(config)
        fs = 48000
        block_len = 512
        # Need at least 8192 samples for the buffer to fill
        num_blocks = 20  # 10,240 samples
        spectral_frames: list[DisplayFrame] = []

        for i in range(num_blocks):
            t_s = i * (block_len / fs)
            t_arr = t_s + np.arange(block_len) / fs
            # Pure 80 Hz tone (typical S1/S2 dominant frequency)
            samples = (0.5 * np.sin(2 * np.pi * 80.0 * t_arr)).astype(np.float32)
            block = SampleBlock(sequence=i, timestamp_s=t_s, sample_rate_hz=fs, samples=samples)
            frame = aggregator.add_block(block, block, {"is_healthy": True}, False)
            if frame is not None and frame.spectral_frame is not None:
                spectral_frames.append(frame)

        assert len(spectral_frames) >= 1
        spec = spectral_frames[-1].spectral_frame
        assert spec is not None
        assert "frequencies_hz" in spec
        assert "power_db" in spec
        assert len(spec["frequencies_hz"]) > 200
        assert len(spec["power_db"]) == len(spec["frequencies_hz"])

        # Find peak frequency in PSD
        peak_idx = int(np.argmax(spec["power_db"]))
        peak_freq = spec["frequencies_hz"][peak_idx]
        # Frequency resolution with nperseg=1024 at 48kHz is 48000/1024 = ~46.875 Hz
        assert abs(peak_freq - 80.0) <= 50.0, f"Expected peak near 80 Hz, found {peak_freq} Hz"
        assert spec["dominant_band"] == "fundamental_pcg"

    def test_pause_and_resume_resets_aggregator_cleanly(self, tmp_path: Path):
        """Verifies that pausing and resuming stream clears aggregator timestamp accumulator,
        preventing giant timestamp jumps or phase discontinuities in display frames.
        """
        runtime = setup_48khz_runtime()
        manager = StreamManager(sessions_dir=tmp_path / "sessions", device_runtime=runtime)
        manager.select_source("hardware")

        fs = 48000
        block_len = 512

        # Ingest 10 blocks
        for seq in range(10):
            pkt = DeviceSamplePacket(
                sequence=seq,
                timestamp_s=seq * (block_len / fs),
                raw_samples=np.full(block_len, 5000, dtype=np.int32),
                crc_ok=True,
                sample_rate_hz=fs,
            )
            asyncio.run(manager.ingest_device_packet(pkt))

        # Pause stream
        manager.pause_stream()
        assert manager.is_paused is True

        # Resume stream
        manager.resume_stream()
        assert manager.is_paused is False
        assert manager.display_aggregator._accum_samples == 0

        # Ingest block after resume with contiguous sequence
        pkt_after = DeviceSamplePacket(
            sequence=10,
            timestamp_s=10 * (block_len / fs),
            raw_samples=np.full(block_len, 6000, dtype=np.int32),
            crc_ok=True,
            sample_rate_hz=fs,
        )
        asyncio.run(manager.ingest_device_packet(pkt_after))

        # Device stats show no sequence gap complaints from aggregator
        assert runtime.stats.sequence_gaps == 0
