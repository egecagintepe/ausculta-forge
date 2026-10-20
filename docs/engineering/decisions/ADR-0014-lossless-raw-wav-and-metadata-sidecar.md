# ADR-0014: Persistence Architecture — Directory-Based Normalized WAV + JSON Metadata Sidecar
**Status:** `ACCEPTED`  
**Date:** 2026-09-26 (Hardened in Sprint 04, PR #20; schema v2.0 in Sprint 06)  
**Deciders:** Module C (Ege)  
**Technical Area:** Data Storage, Archiving & Provenance

## Context & Problem Statement
Scientific PCG recordings must be archived in a format that guarantees complete reproducibility, compatibility with standard biomedical signal processing tools (MATLAB, Python SciPy, Audacity), and verifiable integrity against silent file corruption or mid-stream truncation.

## Decision Drivers
* **Universal Interoperability:** Audio files must open seamlessly in standard engineering tools without proprietary decoders.
* **Provenance Richness:** Must preserve UTC start/end timestamps, sample rate, exact block and sample counts, stream quality reports, Git commit SHA, runtime environment, and hardware device info.
* **Integrity Auditing:** Must support automated file integrity verification to detect bit rot, storage corruption, or file truncation.
* **Crash Resilience:** Must preserve a detectable trace if recording is interrupted prematurely by an unexpected disconnection.

## Considered Alternatives
1. **Proprietary HDF5 / NetCDF Single-Container Format:**
   - *Advantages:* Stores multi-dimensional arrays, audio, and metadata in a single file.
   - *Disadvantages:* Cannot be previewed or played back in standard audio players (Audacity, VLC) without specialized software.
2. **Single WAV with Embedded RIFF Metadata Chunks (INFO / BEXT):**
   - *Advantages:* Single file portability.
   - *Disadvantages:* Length limits on metadata fields; standard editors frequently strip custom chunks upon saving.
3. **Flat File Pairs (`<session_id>.wav` + `<session_id>.meta.json` in single directory):**
   - *Disadvantages:* Clutters root folder; difficult to bundle export manifests and secondary analysis artifacts cleanly.
4. **Dedicated Directory per Session (`experiments/sessions/<session_id>/`):**
   - `raw.wav`: Canonical accepted samples serialized via `scipy.io.wavfile.write()` in normalized IEEE float32 ($[-1.0, 1.0]$).
   - `session.json`: Authoritative JSON metadata sidecar containing full acquisition parameters and whole-file SHA-256 digest.
   - `manifest.json`: Machine-readable benchmark manifest for phantom benchmarks and reproducible replay.

## Decision
Selected **Alternative 4: Dedicated Directory per Session**:
* Implemented in `software/pcg_core/recording.py` (`SessionRecorder`).
* Upon `start()`, an in-progress placeholder `session.json` is written with `status: "recording"`, `termination_reason: "incomplete"`.
* Samples are accumulated in memory as normalized `np.float32` arrays during streaming to eliminate disk write jitter.
* Upon `stop()`, `full_audio` is concatenated and verified against counted samples, written to `raw.wav`, read back for verification, and hashed with whole-file SHA-256. `session.json` is replaced atomically.
* Replay is provided via `create_session_source()` returning `WavSource` or `RealtimeWavSource`.

## Consequences & Trade-Offs
* **Positive:** Standard float32 WAV is universally playable; pre-created placeholder detects interrupted runs; whole-file SHA-256 detects disk corruption.
* **Negative:** Sessions must be moved as complete directories; normalized float32 WAV is not an unparsed bit-for-bit copy of the raw wire stream (noted explicitly in metadata disclaimer).
* **Security Boundary:** SHA-256 provides storage integrity comparison, not cryptographic authenticity proof against an attacker who modifies both audio and metadata.
