# ADR-0008: Packet Framing — 40-byte Packet Proposal vs. Bulk Blocks
**Status:** `PROPOSED` / `DOCUMENTED_PROPOSAL`  
**Date:** 2026-10-17  
**Deciders:** Module B (Ozan — Author), Module C (Ege — Reviewer)  
**Technical Area:** Wire Protocol & Frame Synchronization

## Context & Problem Statement
To stream continuous audio over USB CDC-ACM, bytes must be delimited into structured packets so the host can detect synchronization loss, calculate dropped packets, and verify frame integrity.

## Proposals Evaluated
1. **Raw Continuous Binary Blocks (Bulk Streaming):**
   * Firmware pushes raw 512-sample (2048-byte) chunks into the USB FIFO without frame headers or sync preambles.
   * Minimal overhead, but if a single byte is dropped on the wire, the host loses 4-byte sample alignment indefinitely, corrupting all subsequent audio into noise.
2. **Fixed 40-byte Structured Frames (Module B Proposal, PR #30):**
   * Preamble: 2-byte magic sync word (`0xAA55`).
   * Header: 2-byte sequence counter, 2-byte flags, 2-byte payload length (32 bytes).
   * Payload: 8 audio samples in `S32_LE` format (32 bytes).
   * Checksum: 2-byte CRC-16-CCITT.
   * Total frame size: Exactly 40 bytes.

## Decision & Current Status
The 40-byte framing specification is recorded as a **`PROPOSED` Wire Standard**:
* The host transport architecture (`software/pcg_app/transport.py`) implements a 3-layer parser fully capable of syncing to `0xAA55`, validating the CRC-16, and extracting payloads.
* Final approval remains open pending physical bench measurements with Module B (Ozan) to evaluate whether a 6,000 packet/second interrupt rate causes USB host controller starvation on Windows.

## Consequences & Trade-Offs
* **Positive:** Instantaneous error recovery (at most 8 samples lost during wire noise); robust synchronization.
* **Negative:** 20% protocol overhead; higher OS packet processing rate.
