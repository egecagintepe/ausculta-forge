# ADR-0007: Container Format — S32_LE for 24-bit PCM Audio
**Status:** `ACCEPTED`  
**Date:** 2026-10-20  
**Deciders:** Module B (Ozan), Module C (Ege)  
**Technical Area:** Wire Protocol, Memory Layout & Portability

## Context & Problem Statement
The INMP441 transducer produces 24-bit signed audio samples. The team needed to choose how these 3-byte samples should be formatted across the 32-bit DMA controller, serial wire transport, and host Python unpacker.

## Decision Drivers
* CPU bus alignment: Modern 32-bit and 64-bit microprocessors perform word reads at 4-byte boundaries with single-cycle efficiency; unaligned 3-byte packing requires slow bit-shifting and triggers hardware alignment faults on some architectures.
* Endianness determinism: Preventing endianness divergence between Xtensa and x86-64 CPUs.
* Mathematical sign extension: Preserving two's-complement negative numbers without mathematical corruption.

## Considered Alternatives
1. **Packed 24-bit (`S24_3LE`, 3 bytes per sample):** Saves 25% wire bandwidth (3 bytes instead of 4), but requires complex byte-reassembly loops on both MCU and PC, incurring CPU overhead.
2. **16-bit Downscaled (`S16_LE`):** Discards the lowest 8 bits of ADC resolution at the firmware boundary.
3. **32-bit Little-Endian Container (`S32_LE`):** Aligns each 24-bit sample into a standard 4-byte integer.

## Decision
Selected the **`S32_LE` Container Format**:
* Each sample occupies exactly 4 bytes in Little-Endian byte order.
* The system supports both MSB-aligned (native INMP441 I2S DMA) and LSB-aligned (sign-extended) formats, with bitwise logic verified by portable C golden vectors (`tools/c_golden_vectors/`).

## Consequences & Trade-Offs
* **Positive:** Maximum memory alignment efficiency; direct mapping to standard C `int32_t` and NumPy `np.int32`.
* **Negative:** Consumes 4 bytes per sample on USB wire instead of 3, but the 1.536 Mbps bitrate easily fits within the 12 Mbps Full-Speed USB pipe.
