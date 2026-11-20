# Wednesday 2026-11-18 — G1 / G2 Quiet / G2 Stimulus Summary (Run 1 — 23.2 dB)

> [!NOTE]
> **Acoustic Trial Context:**  
> This comparison reflects **Stimulus Run 1** (`session_20261118_093225_19cde788`) evaluated against Quiet Baseline (`session_20261118_091909_9e6baa63`). Due to high acoustic loudspeaker volume, near-clipping occurred on 0.2775% of samples (>0.98 FS), producing an in-band power ratio of **23.2 dB**. A subsequent trial with lower stimulus drive level (**Stimulus Run 3**, `session_20261118_100102_4e58ac08`) yielded **8.0 dB** with reduced near-clipping (0.0575%), documented separately in [`wednesday_g2_comparison_run3_8db.md`](wednesday_g2_comparison_run3_8db.md). Both records are preserved as empirical evidence.

- **Generated UTC:** `2026-11-18T09:32:36.719557+00:00`
- **Trial Identifier:** Stimulus Run 1 vs. Quiet Baseline
- **20–500 Hz Stimulus-to-Quiet SNR (dB):** `23.2`
- **Stimulus Separation Verdict:** **`PASSED`**

| Capture Role | `source_mode` | Provenance | Samples | Duration (s) | RMS (FS) | Peak (FS) | Clipping | Drops / CRC | SHA-256 (Raw WAV) |
| --- | :---: | --- | ---: | ---: | ---: | ---: | :---: | :---: | --- |
| `quiet` | `0` | `physical_i2s_inmp441` | 480000 | 10.000 | 0.082773 | 0.637463 | `False` | 256 / 0 | `eb4f218c3a221584...` |
| `stimulus` | `0` | `physical_i2s_inmp441` | 480000 | 10.000 | 0.239739 | 0.999982 | `True` | 256 / 0 | `76698e92fea31bed...` |
