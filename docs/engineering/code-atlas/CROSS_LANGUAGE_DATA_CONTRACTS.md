# AuscultaForge — Cross-Language Data Contracts & Type Governance
**Document ID:** `AF-CODE-CONTRACTS-V01`  
**Classification:** `CODE_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Files:**
- C: `tools/c_golden_vectors/golden_common.h`
- Python: `software/pcg_core/models.py`, `software/pcg_app/models.py`
- TypeScript: `software/frontend/src/types.ts`

---

## 1. Type Governance Across C, Python & TypeScript

Data in AuscultaForge flows through three distinct programming languages:
1. **Embedded C (C11):** Low-level memory buffers, bit shifts, and hardware registers.
2. **Backend Python (Python 3.11):** Asynchronous servers, NumPy arrays, and scientific algorithms.
3. **Frontend TypeScript (TS 5.2):** Strongly-typed web state, canvas renderers, and chart data models.

A breakdown in data types across language boundaries can lead to silent data corruption (e.g. integer truncation, sign flip, endianness inversion, or lost JSON precision).

---

## 2. Core Data Model Mappings

### 2.1 The Streaming Audio Sample Block Contract

```mermaid
classDiagram
    class C_AudioBlock {
        +uint32_t samples[512]
        +uint16_t sequence_number
        +uint16_t flags
        +uint32_t timestamp_ticks
    }

    class Python_SampleBlock {
        +np.ndarray samples (float64)
        +int sample_rate (48000)
        +float timestamp (epoch seconds)
        +int sequence_number
    }

    class TS_WebSocketFrame {
        +string type ("signal_frame")
        +number sequence
        +number timestamp
        +number sample_rate
        +number[] points (decimated)
        +StreamMetrics metrics
        +StreamHealth stream_health
    }

    C_AudioBlock --> Python_SampleBlock : Normalized via Layer 3 Unpacker
    Python_SampleBlock --> TS_WebSocketFrame : Decimated via DisplayDecimator
```

### 2.2 Side-by-Side Type Mapping Table

| Logical Concept | Embedded C (`tools/`) | Host Python (`pcg_core`, `pcg_app`) | Frontend TypeScript (`types.ts`) | Wire / Serialization Format |
|---|---|---|---|---|
| **Audio Sample Container** | `int32_t` / `uint32_t` | `np.int32` / `np.float64` | `number` (Float32 in Canvas) | Little-Endian 32-bit (`S32_LE`) |
| **Sampling Frequency** | `uint32_t` (e.g. `48000U`) | `int` | `number` | JSON integer: `48000` |
| **Monotonic Sample Counter** | `uint64_t` | `int` (unbounded Python int) | `number` | JSON integer |
| **Frame Sequence Counter** | `uint16_t` ($0\text{--}65535$) | `int` | `number` | 2 bytes on wire / JSON integer |
| **Timestamp (Hardware)** | `uint32_t` (FreeRTOS ticks) | `int` (converted to seconds) | `number` | 4 bytes on wire |
| **Timestamp (Host Timebase)**| N/A | `float` (`time.time()`) | `number` | ISO-8601 string or epoch float |
| **Device State Enum** | N/A | `DeviceState(str, Enum)` | `type DeviceState = "ABSENT" \| "DETECTED" \| ...` | JSON string (`"READY"`, `"STREAMING"`) |
| **Integrity Checksum** | `uint16_t` (CRC-16) | `str` (64-character SHA-256 hex) | `string` | 2 bytes wire / 64-char JSON string |

---

## 3. Strict Schema Declarations

### 3.1 Python Dataclass (`software/pcg_core/models.py`)
```python
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class SampleBlock:
    """Universal immutable container for an ingested audio block."""
    samples: np.ndarray       # 1D float64 array, shape (N,)
    sample_rate: int          # Sampling frequency (Hz), e.g. 48000
    timestamp: float          # Monotonic arrival timestamp (seconds)
    sequence_number: int      # Monotonic sequence counter
```

### 3.2 TypeScript Interface (`software/frontend/src/types.ts`)
```typescript
export type DeviceState =
  | "ABSENT"
  | "DETECTED"
  | "OPENING"
  | "HANDSHAKING"
  | "READY"
  | "STREAMING"
  | "CLOSING"
  | "INTERRUPTED";

export interface DeviceCapabilities {
  sample_rate: number;
  channels: number;
  container: string;
  bit_depth: number;
}

export interface StreamHealth {
  mcu_drops: number;
  display_drops: number;
  continuity_ok: boolean;
}

export interface WebSocketSignalFrame {
  type: "signal_frame";
  sequence: number;
  timestamp: number;
  sample_rate: number;
  points: number[];
  metrics: {
    rms: number;
    peak: number;
    crest_factor: number;
    clipping: boolean;
  };
  stream_health: StreamHealth;
}
```

---

## 4. Contract Drift Prevention & Verification

To prevent schema divergence between backend Python models and frontend TypeScript interfaces:
1. **Automated Unit Tests:** `software/tests/test_app.py` exercises API endpoints and verifies that JSON field names and types match frontend expectations.
2. **Frontend Type Check:** `npm run lint` (`tsc --noEmit`) validates that all incoming WebSocket payloads and REST responses conform strictly to `types.ts` without using unsafe `any` casts.
3. **C Golden Vector Tests:** `software/tests/test_c_golden_vectors.py` asserts that byte-level serialization routines produce identical numerical values across C and Python.
