# W09 Module B: Continuity and Clipping Verification — Lab Electrical & Acquisition Continuity

- **Week:** 9 (16–22 Kasım 2026)
- **Date of Lab Execution:** 18 Kasım 2026
- **Module:** B (Embedded Acquisition and Data Path)
- **Owner:** Ozan
- **Status:** COMPLETED (Electrical & Acquisition Continuity) / LOW-SPL ACOUSTIC RETEST PENDING

## Objective

Verify electrical safety and continuity of the ESP32-S3 + INMP441 breadboard setup, measure the 3.3V power rail, execute firmware flashing and physical test scripts, verify I²S stream continuity over USB CDC, and perform root-cause analysis on signal clipping and telemetry metrics.

## Inputs / Dependencies

- Agilent U1232A Handheld Digital Multimetre.
- Pre-compiled firmware release `firmware/releases/g2_candidate_20261117` provided by Ege.
- Python verification scripts (`tools/hardware/bringup.py`).
- Hardware setup assembled by Kaan.

## Work Performed

1. **Pre-Power Continuity & Power Rail Measurement:**
   - Conducted cold continuity and resistance checks between VDD and GND to ensure no short circuit.
   - Powered board via USB-C and measured VDD rail voltage on the breadboard using the Agilent U1232A multimeter.
   - Result: **3.28 V** (Attested in `g2_physical_attestation.json`; nominal 3.3V, well within INMP441 safe operating limits 1.62V–3.63V).
2. **Firmware Flashing & G1 Dual-Mode Rollback Verification:**
   - Pre-flash G1 verification on COM3: 480,000 samples, 1,875 blocks, 0 dropped blocks, 0 value errors (`PHYSICAL_G1_PASSED`).
   - Flashed `g2_candidate_20261117` firmware using esptool v5.6.0 on COM4 (`Hash of data verified` on bootloader, partition table, and app).
   - Post-flash G1 rollback check on COM3: 480,000 samples, 1,875 blocks, 0 dropped (`PHYSICAL_G1_PASSED`).
3. **Physical G2 I²S Continuous Stream Verification:**
   - Captured 10-second quiet baseline session (`session_20261118_091909_9e6baa63`): 480,000 samples, 1,875 blocks.
   - Captured 10-second stimulus sessions (`093225_19cde788`, `094939_4888e670`, `100102_4e58ac08`).
   - **Stream Continuity:** Across all sessions, `dropped_blocks = 0`, `repeated_sequences = 0`, `sequence_discontinuities = 0`, `timestamp_regressions = 0`.
4. **Investigation of Signal Clipping & Saturation:**
   - In stimulus session 1 (`093225_19cde788`), `clipping_detected = True` was reported while `saturation_fraction = 0.0`.
   - Detailed inspection showed peak amplitude reached `0.999982 FS`. Samples exceeding `|x| > 0.98` represented `0.2775%` (1,332 samples), while samples at hard rail (`|x| >= 0.9999`) were only `0.0013%` (6 samples).
   - Technical distinction: Digital flat-topping did not saturate the stream, but acoustic over-excitation brought the MEMS sensor near its physical full-scale ceiling.
5. **Firmware Telemetry Analysis (`dropped_samples = 256`):**
   - Telemetry recorded `generated_samples = 480256`, `fully_queued_samples = 480000`, `dropped_samples = 256`.
   - Determined that `dropped_samples = 256` represents `post_target_drained_samples = 256`, which is exactly one leftover DMA buffer (256 samples) drained after STOP was requested at sample 480,000.
   - **In-stream sample drops were 0 (`in_stream_dropped_samples = 0`).**

## Evidence

- `experiments/hardware/team_2026-11-18/g2_physical_attestation.json` — Operator electrical measurement attestation (3.28V, Agilent U1232A, continuity checks).
- `experiments/hardware/team_2026-11-18/first_flash_log.md` — Complete esptool flashing log with SHA-256 verifications.
- `experiments/hardware/team_2026-11-18/g1_pre_acceptance_report.md` & `g1_post_acceptance_report.md` — G1 determinism pass reports.
- `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json` — Consolidated evidence summary.
- `experiments/hardware/team_2026-11-18/PHYSICAL_G2_ACCEPTANCE_REPORT.md` — Detailed technical acceptance report.

## Results

- **Electrical Rail:** 3.28V (Nominal 3.3V, safe and within specs).
- **Firmware Integrity:** Bit-exact hash verification on ESP32-S3 flash.
- **Data Continuity:** 100% loss-free transmission over native USB CDC across all 4 recorded sessions (1,920,000 total samples captured without a single dropped packet).
- **Clipping Finding:** Acoustic input level was excessively high in stimulus run 1; subsequent runs (`094939_4888e670`) showed near-clip dropping to 0.0006%.

## Open Decisions / Risks

1. **Multimeter Photographic Evidence:** The 3.28V rail measurement was recorded as an operator attestation; a photo of the multimeter display screen was omitted during the lab session.
2. **Acoustic Level Standardisation:** Acoustic stimulus loudness needs calibrated volume control to ensure strictly linear, non-clipped acoustic characterization.

## Next Week Handoff

Deliver continuous, zero-loss embedded acquisition pipeline to Week 10 for prolonged multi-minute stability runs, battery power supply ripple testing, and automated clipping alarm calibration in host software.


## Week 09 / REV04 — 20 Kasım 2026 dokümantasyon teslimi

- [Sistem tasarımı ve teknik şartname, Word REV04](W09_B_system-design-technical-specification_REV04_2026-11-20.docx)
- [Satın alma, BOM ve test matrisi, Excel REV04](W09_B_procurement-bom-test_REV04_2026-11-20.xlsx)
- [Rev04 son QA ve açık kalan deneyler](AuscultaForge_W09_REV04_QA_2026-11-20.md)

**Ayrım:** 18 Kasım fiziksel G1 ve INMP441 G2 fonksiyonel testleri PASS; ancak bağımsız fantom S1/S2, 30 dakika sürekli akış, 20–500 Hz karakterizasyonu ve ECM/AFE ölçümleri henüz tamamlanmadı. Yerel ZIP ile repo özetindeki iki WAV SHA farkı açık bulgudur; RAW WAV veya geçmiş deney kanıtı değiştirilmemiştir.
