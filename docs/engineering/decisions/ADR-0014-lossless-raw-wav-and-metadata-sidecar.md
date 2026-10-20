# ADR-0014: Persistence Architecture — Lossless Raw WAV + JSON Sidecar
**Status:** `ACCEPTED`  
**Date:** 2026-09-26 (Hardened in Sprint 04, PR #20)  
**Deciders:** Module C (Ege)  
**Technical Area:** Data Storage, Archiving & Provenance

## Context & Problem Statement
Scientific measurement recordings must be archived in a format that guarantees complete reproducibility, compatibility with standard biomedical signal processing tools, and tamper-evident cryptographic protection.

## Decision Drivers
* Universal interoperability: Audio files must open seamlessly in standard engineering tools (MATLAB, Python SciPy, Audacity, librosa).
* Metadata richness: Must store Git commit SHAs, sample loss counters, hardware IDs, and sensor configurations.
* Lossless compression vs. uncompressed PCM: Lossy compression (MP3, AAC) permanently alters spectral phase and attenuates cardiac frequencies; uncompressed PCM preserves bit-exact ADC words.

## Considered Alternatives
1. **Proprietary HDF5 / NetCDF Formats:** Stores multi-dimensional arrays and metadata in a single container, but cannot be previewed in audio tools without custom Python scripts.
2. **Single WAV with Embedded RIFF INFO / BEXT Chunks:** Standard metadata chunks have strict length limits and are stripped by many third-party audio editors upon saving.
3. **Dual-File Pair (Raw PCM WAV + Immutable JSON Sidecar):**
   * `<session_id>.wav`: Standard uncompressed 24-bit linear PCM audio.
   * `<session_id>.meta.json`: Human-readable and machine-parseable JSON sidecar containing technical provenance and an SHA-256 hash of the audio payload.

## Decision
Selected the **Dual-File Architecture (WAV + JSON Sidecar)**:
* Implemented in `software/pcg_core/recording.py` (`SessionRecorder`).
* Hashing is performed incrementally during recording to ensure zero finalization latency.

## Consequences & Trade-Offs
* **Positive:** Uncompressed audio opens in any standard tool; JSON sidecar provides full provenance for peer-reviewed defense.
* **Negative:** Session pairs must be moved together; deleting the JSON sidecar flags the WAV file as untrusted during replay.
