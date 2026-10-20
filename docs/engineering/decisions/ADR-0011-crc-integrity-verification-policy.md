# ADR-0011: Data Integrity — CRC-16 Wire Check & SHA-256 File Policy
**Status:** `ACCEPTED`  
**Date:** 2026-10-18  
**Deciders:** Module C (Ege), Module B (Ozan)  
**Technical Area:** Cryptographic Integrity & Quality Assurance

## Context & Problem Statement
Data integrity must be verified at two radically different timescales:
1. **Microsecond Timescale (Wire Level):** Detecting noisy bits or electromagnetic interference over the USB serial cable.
2. **Long-Term Timescale (File Level):** Guaranteeing that recorded scientific audio sessions have not been altered, truncated, or tampered with before analysis.

## Decision Drivers
* Microcontroller computational limits: Computing heavy cryptographic hashes (e.g. SHA-256) inside an embedded MCU on every tiny 40-byte packet consumes excessive CPU cycles.
* Scientific provenance: Research recordings require tamper-evident verification.

## Considered Alternatives
1. **Simple Additive Checksum (Wire Level):** Trivial to compute, but fails to detect transposed bytes, double-bit errors, or bursts of zeros.
2. **CRC-32 on Every Wire Packet:** Provides higher polynomial strength than CRC-16, but consumes 4 bytes of packet header overhead instead of 2.
3. **No Cryptographic File Hashing:** Leaves WAV files vulnerable to silent modification or manual splicing.

## Decision
Enforced a **Dual-Tiered Integrity Policy**:
1. **Wire Level — Reference CRC-16-CCITT:** The proposed framing protocol and reference decoder (`software/pcg_app/device_runtime.py`) calculate a 16-bit CRC ($G(x) = x^{16} + x^{12} + x^5 + 1$, init `0xFFFF`) over each frame. While currently implemented in host test utilities and reference decoders, the final trailer policy and algorithm remain an active candidate proposal awaiting joint Module B/C physical bring-up approval.
2. **File Level — Whole-File Storage SHA-256:** Upon session finalization, `SessionRecorder.stop()` invokes `compute_file_sha256(raw_wav_path)` to compute the cryptographic SHA-256 digest over the complete serialized `raw.wav` file on disk. This digest is committed to `session.json` (as `raw_wav_sha256`) and `manifest.json`. Session verification (`verify_session()`) recomputes this hash to detect bit rot, truncation, or accidental editing.
   * *Security Boundary:* SHA-256 provides file integrity detection, not cryptographic proof of recording authenticity or tamper-proofing against an attacker with filesystem access.

## Consequences & Trade-Offs
* **Positive:** Clear separation of wire-level transport integrity from post-acquisition disk integrity; automated detection of file corruption or truncation.
* **Negative:** Modifying a recorded audio file in external software (e.g. Audacity) invalidates the SHA-256 hash, causing `verify_session()` to flag `sha256_match: false`. (This is an intended scientific protection).
