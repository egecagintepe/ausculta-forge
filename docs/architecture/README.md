# System Architecture & DSP Pipeline
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Senior Design Project (Platform / Software Codename: `AuscultaForge`)

## Overview

The digital stethoscope system acquires cardiac acoustic signals via an acoustic chestpiece and microphone/transducer front-end, streams digital audio to an MCU/acquisition unit, and transfers the data to a host PC for digital signal processing (DSP), visualization, and quality analysis.

```text
+------------------------+        +--------------------------+        +--------------------+
| Reference PCG / Phantom| -----> | ESP32-S3 Dev Board       | -----> |      Host PC       |
| Transducer (Module A)  | (I2S)  | Sampling & Continuity    | (USB)  | Ingestion, DSP, UI |
|   (Kaan)               |        |   Driver (Module B, Ozan)|        |   (Module C, Ege)  |
+------------------------+        +--------------------------+        +--------------------+
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
- **Decoupled Sources:** The DSP pipeline, metrics calculation, and UI decimation pipeline consume only `SampleBlock` streams.
- **Interchangeable Input Streams:**
  - `MockPCGSource`: Synthetic S1/S2 heart sound generator for off-hardware testing.
  - `WavSource`: Reads benchmark WAV recordings in batch blocks (e.g. PhysioNet CinC 2016).
  - `RealtimeWavSource`: Replays WAV recordings paced to wall-clock time (or unpaced with `--fast`). **Note:** This is a software development and testing adapter, not production acquisition; it exists to simulate future live MCU digital streams before hardware is finalized.
  - *Future* `NativeUsbSource`: Hardware stream from MCU acquisition unit.
- **Wire Protocol Independence:** The byte format on the wire (USB packets, framing, headers) is translated by a driver into `SampleBlock` instances. The wire format can change without touching DSP or consumer code.

## Streaming Ingestion Pipeline

```text
Real PCG WAV / Mock Source / Hardware Stream
                   │
                   ▼
  Source Adapter (e.g. RealtimeWavSource)
                   │
                   ▼
          SampleBlock Stream
                   │
                   ▼
       StreamQualityMonitor
     (Discontinuities, drops, fs)
                   │
                   ▼
     StreamingBandpass (DSP Filter)
                   │
                   ▼
             RollingBuffer
   (Configurable FIFO window, e.g. 5s)
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   Live Metrics          Spectral Frame
(RMS, Peak, Crest)    (Welch PSD, Bands)
        │                     │
        └──────────┬──────────┘
                   ▼
       Display Decimation Pipeline
       (Peak-Preserving <= 600 pts)
                   │
                   ▼
       React Desktop Client UI
```
