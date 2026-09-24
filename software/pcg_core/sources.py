from pathlib import Path
from typing import Iterator
import numpy as np
from scipy.io import wavfile

from .models import SampleBlock


class MockPCGSource:
    """Donanım yokken pipeline geliştirmek için PCG-benzeri sinyal üretir."""

    def __init__(self, sample_rate_hz: int = 4000, heart_rate_bpm: float = 72.0,
                 block_size: int = 256, duration_s: float = 10.0):
        self.fs = int(sample_rate_hz)
        self.hr = float(heart_rate_bpm)
        self.block_size = int(block_size)
        self.duration_s = float(duration_s)

    def _make_signal(self) -> np.ndarray:
        n = int(self.fs * self.duration_s)
        t = np.arange(n) / self.fs
        y = np.zeros(n, dtype=np.float32)

        period = 60.0 / self.hr
        beat_times = np.arange(0.4, self.duration_s, period)

        # S1 ve S2'yi kaba biçimde kısa, sönümlü sinüs paketleriyle taklit ediyoruz.
        for bt in beat_times:
            for offset, freq, amp, decay in [
                (0.00, 70.0, 1.0, 35.0),   # S1-benzeri
                (0.32, 95.0, 0.70, 45.0),  # S2-benzeri
            ]:
                tau = t - (bt + offset)
                mask = (tau >= 0) & (tau < 0.12)
                y[mask] += (
                    amp
                    * np.sin(2 * np.pi * freq * tau[mask])
                    * np.exp(-decay * tau[mask])
                )

        rng = np.random.default_rng(42)
        y += 0.025 * rng.standard_normal(n).astype(np.float32)
        return y

    def blocks(self) -> Iterator[SampleBlock]:
        y = self._make_signal()
        seq = 0
        for start in range(0, len(y), self.block_size):
            chunk = y[start:start + self.block_size]
            if len(chunk) == 0:
                break
            yield SampleBlock(
                sequence=seq,
                timestamp_s=start / self.fs,
                sample_rate_hz=self.fs,
                samples=chunk,
                source="mock",
            )
            seq += 1


class WavSource:
    """Mono WAV dosyasını aynı SampleBlock arayüzüne çevirir."""

    def __init__(self, path: str | Path, block_size: int = 256):
        self.path = Path(path)
        self.block_size = int(block_size)

    def blocks(self) -> Iterator[SampleBlock]:
        fs, data = wavfile.read(self.path)
        x = np.asarray(data)

        if x.ndim == 2:
            x = x.mean(axis=1)

        if np.issubdtype(x.dtype, np.integer):
            max_val = max(abs(np.iinfo(x.dtype).min), np.iinfo(x.dtype).max)
            x = x.astype(np.float32) / float(max_val)
        else:
            x = x.astype(np.float32)

        for seq, start in enumerate(range(0, len(x), self.block_size)):
            chunk = x[start:start + self.block_size]
            if len(chunk) == 0:
                break
            yield SampleBlock(
                sequence=seq,
                timestamp_s=start / fs,
                sample_rate_hz=int(fs),
                samples=chunk,
                source=self.path.name,
            )
