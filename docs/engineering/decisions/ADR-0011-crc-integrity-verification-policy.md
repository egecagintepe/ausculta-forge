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
1. **Wire Level — CRC-16-CCITT:** Firmware computes a 16-bit CRC ($G(x) = x^{16} + x^{12} + x^5 + 1$, init `0xFFFF`) over each wire frame. The host Layer 2 decoder validates this CRC in real-time, discarding corrupted frames.
2. **File Level — Cryptographic SHA-256:** As audio samples are streamed to disk, `SessionRecorder` updates an incremental SHA-256 digest. The final 64-character hexadecimal hash is committed to `<session_id>.meta.json`. Replaying or analyzing the session requires matching this hash.

## Consequences & Trade-Offs
* **Positive:** Lightweight hardware verification on the wire; rock-solid cryptographic immutability on disk.
* **Negative:** Modifying a recorded audio file in external software (e.g. Audacity) invalidates the SHA-256 hash, causing the AuscultaForge analysis pipeline to reject it. (This is an intended scientific protection).
