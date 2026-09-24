# AuscultaForge — System Architecture & DSP Pipeline

## Overview

The AuscultaForge digital stethoscope system acquires cardiac acoustic signals via an acoustic head and microphone sensor, streams digital audio to an MCU, and transfers the data to a host PC for digital signal processing (DSP), visualization, and metrics analysis.

```text
+-------------------+        +--------------------+        +--------------------+
|  Acoustic Head &  | -----> |    MCU (ESP32)     | -----> |      Host PC       |
|  Microphone Unit  | (I2S)  | Sampling & Framing | (Wire) | Ingestion & Buffer |
|      (Ozan)       |        |       (Kaan)       |        |       (Ege)        |
+-------------------+        +--------------------+        +--------------------+
                                                                      |
                                                                      v
                                                            +-------------------+
                                                            |    SampleBlock    |
                                                            | Common Interface  |
                                                            +-------------------+
                                                                      |
                                                                      v
                                                            +-------------------+
                                                            |   DSP Pipeline    |
                                                            | (Filtering, RMS)  |
                                                            +-------------------+
                                                                      |
                                                                      v
                                                            +-------------------+
                                                            | UI / Storage / QA |
                                                            +-------------------+
```

## `SampleBlock` Abstraction

The core abstraction of the PC software is the `SampleBlock` dataclass:

```python
@dataclass(slots=True)
class SampleBlock:
    sequence: int
    timestamp_s: float
    sample_rate_hz: int
    samples: np.ndarray  # 1D float32 normalized [-1.0, 1.0]
    source: str = "unknown"
```

### Architectural Guarantees:
- **Decoupled Sources:** The DSP pipeline, metrics calculation, and future visualizer consume only `SampleBlock` streams.
- **Interchangeable Input Streams:**
  - `MockPCGSource`: Synthetic S1/S2 heart sound generator for off-hardware testing.
  - `WavSource`: Reads benchmark WAV recordings (e.g. PhysioNet CinC 2016).
  - *Future* `SerialSource`: USB-UART streaming from ESP32.
  - *Future* `NetworkSource`: Wi-Fi / socket stream.
- **Wire Protocol Independence:** The byte format on the wire (serial packets, framing, headers) is translated by a driver into `SampleBlock` instances. The wire format can change without touching DSP or consumer code.
