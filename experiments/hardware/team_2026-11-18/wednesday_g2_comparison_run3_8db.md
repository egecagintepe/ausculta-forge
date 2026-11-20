# Wednesday 2026-11-18 — G1 / G2 Quiet / G2 Stimulus Summary (Run 3 — 8.0 dB)

> [!NOTE]
> **Acoustic Trial Context:**  
> This comparison reflects **Stimulus Run 3** (`session_20261118_100102_4e58ac08`) evaluated against Quiet Baseline (`session_20261118_091909_9e6baa63`). Generated at `10:01:14Z` in the second lab package, this run used a lower acoustic drive level / repositioned source, resulting in reduced near-clipping (0.0575%) and an in-band power ratio of **8.0 dB**. The earlier high-volume run (**Stimulus Run 1**, 23.2 dB, 0.2775% near-clipping) is preserved separately in [`wednesday_g2_comparison.md`](wednesday_g2_comparison.md).

- **Generated UTC:** `2026-11-18T10:01:14.498091+00:00`
- **Trial Identifier:** Stimulus Run 3 vs. Quiet Baseline
- **20–500 Hz Stimulus-to-Quiet SNR (dB):** `8.0`
- **Stimulus Separation Verdict:** **`PASSED`**

| Capture Role | `source_mode` | Provenance | Samples | Duration (s) | RMS (FS) | Peak (FS) | Clipping | Drops / CRC | SHA-256 (Raw WAV) |
| --- | :---: | --- | ---: | ---: | ---: | ---: | :---: | :---: | --- |
| `quiet` | `0` | `physical_i2s_inmp441` | 480000 | 10.000 | 0.082773 | 0.637463 | `False` | 256 / 0 | `eb4f218c3a221584...` |
| `stimulus` | `0` | `physical_i2s_inmp441` | 480000 | 10.000 | 0.105337 | 0.999967 | `True` | 256 / 0 | `26c78582df26bcd2...` |
