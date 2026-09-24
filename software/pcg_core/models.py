from dataclasses import dataclass
import numpy as np

@dataclass(slots=True)
class SampleBlock:
    """UI ve donanımdan bağımsız ortak örnek bloğu.

    Wire protocol DEĞİLDİR. MCU verisi ileride parse edilip bu yapıya çevrilebilir.
    """
    sequence: int
    timestamp_s: float
    sample_rate_hz: int
    samples: np.ndarray
    source: str = "unknown"

    def __post_init__(self) -> None:
        self.samples = np.asarray(self.samples, dtype=np.float32)
        if self.samples.ndim != 1:
            raise ValueError("samples tek kanallı 1-D olmalı")
        if self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz pozitif olmalı")
