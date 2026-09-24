"""AuscultaForge — Rolling Buffer for Streaming Audio Samples.

Retains a configurable window of recent audio samples (e.g. 5.0 or 10.0 seconds)
for real-time metrics calculation, DSP analysis, and UI visualization.
"""

from typing import Union
import numpy as np

from .models import SampleBlock


class RollingBuffer:
    """Fixed-duration sliding window buffer for 1D float32 audio samples.
    
    Drops oldest samples when capacity is reached (FIFO).
    """

    def __init__(self, capacity_seconds: float = 5.0, sample_rate_hz: int | None = None):
        if capacity_seconds <= 0.0:
            raise ValueError("capacity_seconds must be positive.")
        if sample_rate_hz is not None and sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive.")

        self.capacity_seconds = float(capacity_seconds)
        self.sample_rate_hz = int(sample_rate_hz) if sample_rate_hz is not None else None
        
        self._capacity_samples: int = (
            max(1, int(self.capacity_seconds * self.sample_rate_hz))
            if self.sample_rate_hz is not None
            else 0
        )
        self._buffer: np.ndarray = np.zeros(self._capacity_samples, dtype=np.float32)
        self._count: int = 0
        self._total_samples_appended: int = 0

    @property
    def capacity_samples(self) -> int:
        return self._capacity_samples

    @property
    def count(self) -> int:
        return self._count

    @property
    def duration_s(self) -> float:
        if not self.sample_rate_hz or self.sample_rate_hz <= 0:
            return 0.0
        return self._count / float(self.sample_rate_hz)

    @property
    def is_full(self) -> bool:
        return self._count >= self._capacity_samples and self._capacity_samples > 0

    def reset_sample_rate(self, new_sample_rate_hz: int) -> None:
        """Reconfigure buffer capacity for a new sample rate and reset contents."""
        if new_sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive.")
        self._initialize_capacity(new_sample_rate_hz)

    def _initialize_capacity(self, sample_rate_hz: int) -> None:
        self.sample_rate_hz = int(sample_rate_hz)
        self._capacity_samples = max(1, int(self.capacity_seconds * self.sample_rate_hz))
        self._buffer = np.zeros(self._capacity_samples, dtype=np.float32)
        self._count = 0

    def append(
        self,
        data: Union[np.ndarray, list[float], SampleBlock],
        adapt_sample_rate: bool = False,
    ) -> None:
        """Append new samples or SampleBlock into the rolling buffer.
        
        If adapt_sample_rate is True, reconfigures capacity if a block with a
        new sample rate arrives.
        """
        if isinstance(data, SampleBlock):
            if self.sample_rate_hz is None:
                self._initialize_capacity(data.sample_rate_hz)
            elif data.sample_rate_hz != self.sample_rate_hz:
                if adapt_sample_rate:
                    self.reset_sample_rate(data.sample_rate_hz)
                else:
                    raise ValueError(
                        f"Sample rate mismatch: buffer configured for {self.sample_rate_hz} Hz, "
                        f"received block with {data.sample_rate_hz} Hz"
                    )
            chunk = data.samples
        else:
            chunk = np.asarray(data, dtype=np.float32)

        if chunk.ndim != 1:
            raise ValueError("Data must be 1-dimensional.")

        if len(chunk) == 0:
            return

        if self.sample_rate_hz is None:
            raise ValueError("sample_rate_hz not set; pass a SampleBlock first or set in __init__.")

        n_new = len(chunk)
        self._total_samples_appended += n_new

        if n_new >= self._capacity_samples:
            # New chunk is larger than whole buffer capacity; keep last N samples
            self._buffer[:] = chunk[-self._capacity_samples:]
            self._count = self._capacity_samples
        else:
            space_left = self._capacity_samples - self._count
            if n_new <= space_left:
                self._buffer[self._count : self._count + n_new] = chunk
                self._count += n_new
            else:
                # Shift buffer left by overflow amount
                overflow = n_new - space_left
                self._buffer[:-n_new] = self._buffer[overflow : self._count]
                self._buffer[-n_new:] = chunk
                self._count = self._capacity_samples

    def get_samples(self) -> np.ndarray:
        """Return a copy of currently retained samples (chronological order)."""
        return self._buffer[: self._count].copy()

    def get_view(self) -> np.ndarray:
        """Return a read-only view of currently retained samples."""
        view = self._buffer[: self._count].view()
        view.flags.writeable = False
        return view

    def clear(self) -> None:
        """Reset buffer contents."""
        self._count = 0
        self._total_samples_appended = 0
        self._buffer.fill(0.0)
