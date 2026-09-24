from pathlib import Path
import numpy as np
from scipy.io import wavfile

from .sources import MockPCGSource
from .dsp import StreamingBandpass
from .metrics import rms, peak_abs, crest_factor


def main() -> None:
    source = MockPCGSource(
        sample_rate_hz=4000,
        heart_rate_bpm=72,
        block_size=256,
        duration_s=10,
    )

    filt = StreamingBandpass(
        sample_rate_hz=4000,
        low_hz=20,
        high_hz=600,
        order=4,
    )

    raw_parts = []
    filtered_parts = []

    for block in source.blocks():
        raw_parts.append(block.samples)
        filtered_parts.append(filt.process(block).samples)

    raw = np.concatenate(raw_parts)
    filtered = np.concatenate(filtered_parts)

    print(f"raw RMS       : {rms(raw):.5f}")
    print(f"filtered RMS  : {rms(filtered):.5f}")
    print(f"filtered peak : {peak_abs(filtered):.5f}")
    print(f"crest factor  : {crest_factor(filtered):.3f}")

    # WAV için güvenli normalize.
    def to_int16(x: np.ndarray) -> np.ndarray:
        m = float(np.max(np.abs(x)))
        if m == 0:
            return np.zeros_like(x, dtype=np.int16)
        return np.int16(np.clip(x / m, -1, 1) * 32767)

    wavfile.write("demo_raw.wav", 4000, to_int16(raw))
    wavfile.write("demo_filtered.wav", 4000, to_int16(filtered))

    print("demo_raw.wav ve demo_filtered.wav oluşturuldu.")


if __name__ == "__main__":
    main()
