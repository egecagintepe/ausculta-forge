# AuscultaForge — Python Backend Runtime Walkthrough
**Document ID:** `AF-CODE-PY-WALKTHROUGH-V01`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Files:**
- `software/pcg_app/device_runtime.py`
- `software/pcg_app/state.py`
- `software/pcg_app/display_pipeline.py`
- `software/pcg_app/virtual_bench.py`
- `software/pcg_app/analysis_service.py`

---

## 1. Architectural Philosophy of the Host Runtime

The Python host runtime (`pcg_app`) serves as the core bridge connecting physical or simulated acquisition sources to modern web client interfaces. It is designed around four architectural pillars:
1. **Asynchronous Non-Blocking Execution:** Built on Python's `asyncio` framework to handle simultaneous WebSocket streaming, HTTP API polling, and disk persistence without thread starvation.
2. **State Machine Invariant Enforcement:** Strict state transitions preventing phantom connections or uninitialized streaming sessions.
3. **Lossless Scientific Preservation:** Background audio persistence is prioritized above all user-interface rendering tasks.
4. **Comprehensive Test Traceability:** Every core class has dedicated unit and integration tests under `software/tests/`.

---

## 2. Core Python Runtime Classes

### 2.1 `DeviceRuntime` (`software/pcg_app/device_runtime.py`)
`DeviceRuntime` is the authoritative state machine managing the physical USB CDC-ACM peripheral and its virtual simulation fallbacks.

#### Key Methods & Execution Logic:
* **`poll_device() -> DeviceStatus`:**
  * Enumerates operating system serial ports via `serial.tools.list_ports.comports()`.
  * Matches against official Espressif USB Vendor ID (`0x303A`) or simulated Virtual Bench targets.
  * Transitions state: $\text{ABSENT} \to \text{DETECTED}$ upon discovering a valid candidate.
* **`open_device(port: Optional[str]) -> bool`:**
  * Instantiates the serial handle with 115200 baud, 8 data bits, no parity, 1 stop bit, and a non-blocking timeout of $1.0 \text{ s}$.
  * Asserts the Data Terminal Ready (DTR) modem line: `ser.dtr = True` to signal the ESP32-S3 firmware to begin transmission.
  * Transitions state: $\text{DETECTED} \to \text{OPENING} \to \text{HANDSHAKING}$.
* **`start_streaming() -> bool`:**
  * Preconditions: Device state MUST be `READY`.
  * Spawns an asynchronous background task `_stream_reader_loop()` to ingest incoming packets continuously.
  * Transitions state: $\text{READY} \to \text{STREAMING}$.
* **`handle_interruption(error_msg: str)`:**
  * Synchronously catches IO exceptions (`SerialException`).
  * Transitions state: $\text{STREAMING} \to \text{INTERRUPTED}$.
  * Flushes active session recorder and emits an urgent error notification over the WebSocket bridge.

---

### 2.2 `StreamManager` (`software/pcg_app/state.py`)
`StreamManager` coordinates active audio streams, routing data from sources to listeners.

#### Core Responsibilities:
1. **Source Multiplexing:** Can attach to a physical `DeviceRuntime` stream, an offline `RealtimeWavSource`, or a synthetic `VirtualBench` scenario.
2. **Rolling Memory Window:** Maintains a thread-safe `RollingBuffer` holding the latest 5.0 seconds of audio ($240,000 \text{ samples}$ at $48\text{ kHz}$) for immediate spectral snapshot generation.
3. **Subscriber Fan-Out:** Maintains an internal list of asynchronous queues (`asyncio.Queue`). When a new `SampleBlock` arrives, it is fanned out to:
   - The active `SessionRecorder` (if disk recording is enabled).
   - The `DisplayDecimator` (for WebSocket push to React).
   - The real-time metric monitor (computing RMS, peak, crest factor, and clipping counts).

---

### 2.3 `DisplayAggregator` (`software/pcg_app/display_pipeline.py`)
`DisplayAggregator` decouples high-speed physical acquisition (48 kHz mono) from UI rendering by aggregating incoming samples into peak-preserving display frames at a controlled cadence (e.g. 20–30 Hz, configured via `DisplayPipelineConfig`).

#### Algorithmic Implementation (`decimate_min_max`):
```python
def decimate_min_max(samples: np.ndarray, target_points: int) -> np.ndarray:
    """Downsample signal using min/max bucket aggregation (peak-preserving decimation).
    
    Divides the signal into target_points / 2 bins and extracts both the minimum
    and maximum values in each bin (in chronological order). This preserves sharp
    acoustic transients, murmurs, and valve clicks without aliasing.
    """
    n_samples = len(samples)
    if n_samples <= target_points:
        return samples.astype(np.float32)

    num_bins = target_points // 2
    bin_size = n_samples / num_bins
    out = np.empty(target_points, dtype=np.float32)

    for i in range(num_bins):
        start = int(i * bin_size)
        end = int((i + 1) * bin_size) if i < num_bins - 1 else n_samples
        sub = samples[start:end]
        if len(sub) == 0:
            continue
        min_idx = np.argmin(sub)
        max_idx = np.argmax(sub)
        if min_idx <= max_idx:
            out[2 * i] = sub[min_idx]
            out[2 * i + 1] = sub[max_idx]
        else:
            out[2 * i] = sub[max_idx]
            out[2 * i + 1] = sub[min_idx]

    return out
```
* **Performance Guarantee:** Tested and verified in `software/tests/test_display_pipeline.py`. Retains sharp transient acoustic clicks while reducing WebSocket payload size by over $98\%$.

---

### 2.4 `VirtualBench` (`software/pcg_app/virtual_bench.py`)
`VirtualBench` provides a suite of 8 deterministic, known-answer test scenarios, allowing full-pipeline verification in headless environments where physical hardware is not present:

| Scenario ID | Name | Mathematical Stimulus | Invariant Verified |
|---|---|---|---|
| **Scenario 1** | `sine_100hz` | Pure 100 Hz tone ($A = 0.5$, $f_s = 48\text{ kHz}$) | PSD peak at exactly 100 Hz ($> 50\text{ dB}$ harmonic purity). |
| **Scenario 2** | `ascending_counter` | Monotonic ramp ($-256$ to $+255$) | Exact bit-level sign extension and linearity. |
| **Scenario 3** | `boundary_stress` | Full-scale $+1.0, -1.0$, and zero transitions | Zero numerical overflow or sign inversion. |
| **Scenario 4** | `clipped_and_impulse` | Dirac impulses and hard-clipped sine | Immediate clipping counter and crest factor alert. |
| **Scenario 5** | `injected_gaps` | Injected sequence counter jumps ($\Delta S = 5$) | `StreamQualityMonitor` registers exact dropped sample count. |
| **Scenario 6** | `timestamp_regression` | Timebase jitter and timestamp jumps | Timestamp monotonicity invariant enforcement. |
| **Scenario 7** | `corrupt_crc_inputs` | Intentional CRC-16 corruption | Resynchronization and zero frame leakage into DSP. |
| **Scenario 8** | `lifecycle_interruption` | Mid-stream simulated disconnect | Automatic session finalization and SHA-256 sidecar commit. |

---

### 2.5 `SessionAnalysisService` (`software/pcg_app/analysis_service.py`)
Provides offline scientific analysis of recorded sessions:
* Loads `experiments/sessions/<session_id>/raw.wav` and verifies its cryptographic hash against `session.json`.
* Computes Welch Power Spectral Density (PSD) across standard frequency bands:
  * Infrasound: $0\text{--}20\text{ Hz}$
  * Cardiac Core: $20\text{--}500\text{ Hz}$
  * High-Frequency Acoustic Noise: $500\text{--}2000\text{ Hz}$
* Estimates mains hum pickup ($50\text{ Hz}$ fundamental and $100, 150, 200, 250\text{ Hz}$ harmonics).
* Generates analytic signal envelopes (Hilbert, Moving RMS, TKEO) and packages results into typed JSON for frontend visualization.
