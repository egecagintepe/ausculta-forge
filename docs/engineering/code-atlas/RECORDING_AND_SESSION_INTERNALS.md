# AuscultaForge — Session Recording, Replay & Cryptographic Integrity Internals
**Document ID:** `AF-CODE-RECORDING-V01`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference File:** `software/pcg_core/recording.py`  
**Associated Tests:** `software/tests/test_recording.py` (20 automated tests)

---

## 1. Dual-File Scientific Persistence Architecture

In academic engineering research, audio recordings cannot be stored as standalone binary files lacking context. Without verifiable provenance, recordings are vulnerable to sample rate confusion, undocumented filtering, lost timestamps, and silent file truncation.

AuscultaForge mandates a **Dual-File Immutable Session Architecture**:
Every scientific recording session is stored as a twin pair of files under `experiments/sessions/`:
1. **`<session_id>.wav`:** The raw, uncompressed Pulse Code Modulated (PCM) audio waveform.
2. **`<session_id>.meta.json`:** A cryptographic metadata sidecar document recording acquisition provenance, environment state, sample counts, and an SHA-256 checksum of the audio payload.

```text
experiments/sessions/
├── session_20261020_143000_exp01.wav        # Raw 24-bit / 48 kHz PCM audio
└── session_20261020_143000_exp01.meta.json  # Immutable cryptographic sidecar
```

---

## 2. RIFF / WAV Audio Header Mechanics

### 2.1 RIFF Chunk Structure
A standard uncompressed WAV file is structured as nested Resource Interchange File Format (RIFF) chunks:

```text
Offset  Size  Field Name          Expected Value / Calculation
0       4     ChunkID             "RIFF" (0x52494646)
4       4     ChunkSize           Total file size - 8 bytes
8       4     Format              "WAVE" (0x57415645)
12      4     Subchunk1ID         "fmt " (0x666D7420)
16      4     Subchunk1Size       16 (PCM chunk size)
20      2     AudioFormat         1 (Linear PCM, uncompressed)
22      2     NumChannels         1 (Mono)
24      4     SampleRate          48,000 (0x0000BB80)
28      4     ByteRate            SampleRate × NumChannels × (BitsPerSample / 8)
32      2     BlockAlign          NumChannels × (BitsPerSample / 8)
34      2     BitsPerSample       16, 24, or 32
36      4     Subchunk2ID         "data" (0x64617461)
40      4     Subchunk2Size       NumSamples × NumChannels × (BitsPerSample / 8)
44      N     Data Payload        Contiguous raw audio samples
```

### 2.2 Header Rewriting on Finalization
* **The Streaming Problem:** When recording starts, the total duration and sample count are unknown. Writing a zero or fixed size into `ChunkSize` and `Subchunk2Size` causes standard media players (and Python `scipy.io.wavfile`) to report the file as empty or corrupt if stream terminates abruptly.
* **The AuscultaForge Solution:**
  1. At session initialization, `SessionRecorder` writes the full 44-byte RIFF header with placeholder sizes ($0\text{xFFFFFFFF}$).
  2. Samples are appended sequentially to disk using unbuffered binary stream writes.
  3. When `SessionRecorder.stop()` is called (or when an emergency disconnect is caught), the file pointer seeks back to byte offsets 4 and 40 (`f.seek(4)`, `f.seek(40)`) and rewrites the exact byte counts.
  4. The file is cleanly flushed to disk (`f.flush()`, `os.fsync(f.fileno())`).

---

## 3. Cryptographic Sidecar Schema & SHA-256 Hashing

### 3.1 Streaming SHA-256 Calculation
Rather than reading the entire file from disk after recording completes (which incurs heavy I/O latency for multi-gigabyte recordings), `SessionRecorder` maintains an active cryptographic hash object:
```python
self._sha256 = hashlib.sha256()

# Inside sample append loop:
pcm_bytes = raw_samples.tobytes()
self._file.write(pcm_bytes)
self._sha256.update(pcm_bytes)  # Incremental in-memory digest
```
The hash covers the **raw audio data payload only** (excluding the 44-byte RIFF header), ensuring the hash is invariant to audio container metadata reformatting.

### 3.2 Formal JSON Metadata Sidecar Schema
```json
{
  "session_id": "session_20261020_143000_exp01",
  "created_at": "2026-10-20T14:30:00.124Z",
  "completed_at": "2026-10-20T14:30:30.124Z",
  "duration_seconds": 30.000,
  "sample_rate": 48000,
  "channels": 1,
  "bit_depth": 24,
  "container_format": "S32_LE",
  "total_samples": 1440000,
  "expected_samples": 1440000,
  "dropped_samples": 0,
  "discontinuity_count": 0,
  "sha256_payload_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "provenance": {
    "git_commit_sha": "fa4b75a80d29aab04875534234574db9f6c0af43",
    "software_version": "1.0.0",
    "module_owner": "Module C (Ege)",
    "source_type": "hardware_serial",
    "device_port": "COM3",
    "device_vid": "0x303A",
    "device_pid": "0x4001"
  },
  "termination_reason": "user_stopped"
}
```

---

## 4. Replay 2.0 Engine & Tamper Rejection

The replay engine (`pcg_core.recording.SessionReplayer`) provides rate-controlled simulated playback of historical recordings.

### Integrity Rejection Invariant:
Before parsing audio bytes, the replayer executes a mandatory cryptographic audit:
1. Opens `<session_id>.wav` and computes its SHA-256 payload hash.
2. Compares against `sha256_payload_hash` in `<session_id>.meta.json`.
3. If hashes mismatch (indicating manual editing, bit rot, or data truncation), the replayer **refuses to load the session**, raising `SessionIntegrityError`.
4. This guarantees that fabricated or altered audio files can never be used in academic metrology reports.
