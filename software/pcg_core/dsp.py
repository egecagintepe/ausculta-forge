import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

from .models import SampleBlock


class StreamingBandpass:
    """Blok blok çalışan stateful Butterworth band-pass filtre.

    Başlangıç değerleri 20–600 Hz; bunlar proje kararı değildir.
    """

    def __init__(self, sample_rate_hz: int, low_hz: float = 20.0,
                 high_hz: float = 600.0, order: int = 4):
        fs = float(sample_rate_hz)
        nyq = fs / 2.0
        if not (0 < low_hz < high_hz < nyq):
            raise ValueError(
                f"Geçersiz bant: 0 < {low_hz} < {high_hz} < Nyquist({nyq}) olmalı"
            )

        self.fs = int(sample_rate_hz)
        self.sos = butter(
            order,
            [low_hz, high_hz],
            btype="bandpass",
            fs=fs,
            output="sos",
        )
        self.zi = sosfilt_zi(self.sos) * 0.0

    def process(self, block: SampleBlock) -> SampleBlock:
        if block.sample_rate_hz != self.fs:
            raise ValueError("Filtre sample rate'i ile blok sample rate'i eşleşmiyor")

        y, self.zi = sosfilt(self.sos, block.samples, zi=self.zi)
        return SampleBlock(
            sequence=block.sequence,
            timestamp_s=block.timestamp_s,
            sample_rate_hz=block.sample_rate_hz,
            samples=np.asarray(y, dtype=np.float32),
            source=f"{block.source}|bandpass",
        )
