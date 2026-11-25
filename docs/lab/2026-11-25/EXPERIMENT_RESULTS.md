# Experiment Results Register — 25 November 2026

All metrics below are verified directly from preserved `session.json`, `coupling_diagnostic_report.json`, `phantom_pcg_experiment_report.json`, and `raw.wav` artifacts.

## 1. Standalone & Coupling Diagnostics (Mic-Only, No Stimulus Playback)

| Session ID | Role / Label | Time (UTC) | Samples (`nonzero`) | Drops / CRC | Raw RMS / Peak (FS) | 20–500 Hz RMS (0–10 s / 1–10 s) | Clipping (`>0.98`) | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `session_20261125_074126_5317e121` | `MIC_DIAGNOSTIC` (`SCK` on GPIO3) | `07:41:26` | `480,000` (`0`) | `0` / `0` | `0.000000` / `0.000000` | `0.000000` / `0.000000` | `0` | **FAIL** (`DIGITAL_SILENCE`) |
| `session_20261125_075205_9923da49` | `MIC_DIAGNOSTIC` (`SCK` fixed to GPIO4) | `07:52:05` | `480,000` (`479,784`) | `0` / `0` | `0.078581` / `0.688231` | `0.012834` / `0.013264` | `0` | **PASS** (Mic signal verified) |
| `session_20261125_082614_a84648cb` | `STETHOSCOPE_COUPLING` (unguided) | `08:26:14` | `480,000` (`479,791`) | `0` / `0` | `0.064583` / `0.401116` | `0.011328` / `0.011279` | `0` | **INCONCLUSIVE** (Continuous ambient noise) |
| `session_20261125_083848_02ff521c` | `STETHOSCOPE_COUPLING_DIAGNOSTIC` (guided) | `08:38:48` | `480,000` (`398,188`) | `0` / `0` | `0.041824` / `0.998572` | `0.018099` / `0.019078` | `10` (`0.0021%`) | **PASS** (`COUPLING_VERIFIED`, 3/3 taps, silence `0.004013 FS`) |
| `session_20261125_100347_bec2d02b` | `STETHOSCOPE_COUPLING_DIAGNOSTIC` (recovery #1) | `10:03:47` | `480,000` (`0`) | `0` / `0` | `0.000000` / `0.000000` | `0.000000` / `0.000000` | `0` | **FAIL** (`DIGITAL_SILENCE`) |
| `session_20261125_100542_a818e843` | `STETHOSCOPE_COUPLING_DIAGNOSTIC` (recovery #2) | `10:05:42` | `480,000` (`479,812`) | `0` / `0` | `0.119181` / `0.999829` | `0.021025` / `0.022103` | `82` (`0.0171%`) | **PASS** (`COUPLING_VERIFIED`, 3/3 taps, silence `0.001110 FS`) |

---

## 2. Official Q01 Quiet Baseline Attempt

| Session ID | Time (UTC) | Samples (`nonzero`) | Drops / CRC | Full `0–10 s` 20–500 Hz RMS | Stable `1–10 s` 20–500 Hz RMS | Clipping (`>0.98`) | Official Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `session_20261125_093843_959d7eb0` | `09:38:43` | `480,000` (`479,986`) | `0` / `0` | `0.045325 FS` (`>= 0.005`) | `0.001469 FS` | `254` (`0.0529%`, all in `0–1 s`) | **OFFICIAL_Q01: FAIL** *(Startup transient; NOT relabeled)* |

---

## 3. Exploratory Physical Phantom PCG Trials (`40058_AV.wav`, Realtek AUX)

| Trial ID (Session ID) | Label & Config | Vol | Drops / CRC | Full `0–10 s` Clip | `1–10 s` 20–500 Hz RMS | Contextual SNR (vs Q01 `1–10 s`) | `1–10 s` NCC (Lag) | `1–10 s` Coh (20–250 Hz) | `1–10 s` S1/S2 Match | Exploratory / Formal Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trial_20261125_094357_0309bb` (`session_20261125_094358_f9926dad`) | `P01_EXPLORATORY_PHYSICAL_PHANTOM` (Cardboard plate) | ~3–5% | `0` / `0` | `261` (`0.0544%`, `0` in `1–10 s`) | `0.001330 FS` | `-0.86 dB` (`0.91x`) | `0.0081` (`+154.5 ms`) | `0.1911` | `0/15` | **INCONCLUSIVE** |
| `trial_20261125_094850_1d84e4` (`session_20261125_094851_d2fc49f1`) | `P01_EXPLORATORY_RETEST_02_VOLUME_10` (Cardboard plate) | 10% | `0` / `0` | `159` (`0.0331%`, `0` in `1–10 s`) | `0.001524 FS` | `+0.32 dB` (`1.04x`) | `0.0930` (`+375.0 ms`) | `0.0226` | `0/16` (`7` cap peaks) | **INCONCLUSIVE** |
| **`trial_20261125_095717_275ae8`** (`session_20261125_095718_2d385ca8`) | **`P01_EXPLORATORY_RETEST_03_VOLUME_20`** (Cardboard plate) | **20%** | `0` / `0` | `243` (`0.0506%`, **`0` in `1–10 s`**) | **`0.010761 FS`** | **`+17.30 dB` (`7.33x`)** | **`0.1772`** (`+142.1 ms`) | **`0.8820`** | **`10/16 (62.5%)`**, jitter `16.47 ms` | **POC TRANSMISSION DEMONSTRATED** *(Official P01: NOT YET ACCEPTED)* |
| `trial_20261125_100205_921544` (`session_20261125_100207_7928af69`) | `P01_SIDEQUEST_DIRECT_SILICONE_NO_PLATE` | 20% | `0` / `0` | `0` | `0.000000 FS` (`0` nonzero) | N/A | N/A | N/A | N/A | **FAIL** (`DIGITAL_SILENCE`) |
| `trial_20261125_100747_443db6` (`session_20261125_100748_111817a0`) | `P01_SIDEQUEST_DIRECT_SILICONE_NO_PLATE_RETEST` | 20% | `0` / `0` | `0` | `0.000000 FS` (`0` nonzero) | N/A | N/A | N/A | N/A | **FAIL** (`DIGITAL_SILENCE`) |
