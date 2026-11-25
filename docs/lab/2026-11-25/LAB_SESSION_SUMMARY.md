# AuscultaForge — Lab Session Summary | 25 November 2026

> **English:** On November 25, 2026, the AuscultaForge team successfully demonstrated an integrated physical PCG phantom proof of concept. A reference heart-sound recording (`40058_AV.wav`) was reproduced through a PAM8403 amplifier, 12 Ω exciter, cardboard support plate, and cured RTV-2 silicone phantom, then acquired through a stethoscope-coupled INMP441 and ESP32-S3 (`COM10`, `48 kHz`) system. Exploratory measurements (`trial_20261125_095717_275ae8`, `1–10 s` window) achieved **`0.8820` coherence (20–250 Hz)**, **`+17.30 dB` contextual SNR**, and **`10/16` (`62.5%`) S1/S2 matches** with `0` packet loss and `0` CRC errors, while formal Q01/P01 acceptance and acquisition stability remain ongoing engineering tasks.
>
> **Türkçe:** 25 Kasım 2026 tarihinde AuscultaForge ekibi, bütünleşik fiziksel PCG fantom kavram kanıtını (Proof of Concept) başarıyla göstermiştir. Referans kalp sesi (`40058_AV.wav`); PAM8403 amplifikatör, 12 Ω exciter, asılı karton plaka ve kürlenmiş RTV-2 silikon fantom üzerinden iletilmiş, stetoskop kuplajlı INMP441 ve ESP32-S3 (`COM10`, `48 kHz`) hattıyla kaydedilmiştir. Keşif amaçlı ölçümde (`1–10 s`) **`0.8820` koherans**, **`+17.30 dB` bağlamsal SNR** ve **`10/16` (%62.5) S1/S2 eşleşmesi** elde edilmiştir; resmî Q01/P01 kabulü ve başlatma kararlılığı sonraki mühendislik adımları olarak planlanmıştır.

## Scorecard

| Milestone Gate | Verdict | Key Evidence |
| :--- | :--- | :--- |
| **Prototype PoC Milestone** | **ACCEPTED** | End-to-end physical PCG chain working |
| **Physical PCG Transmission** | **DEMONSTRATED** | `trial_20261125_095717_275ae8` (`coh=0.8820`, `+17.30 dB`, `0` drops) |
| **Stethoscope 3-Tap Coupling** | **PASS (2x)** | `session_20261125_083848_02ff521c` & `session_20261125_100542_a818e843` |
| **Official Q01 Quiet Baseline** | **FAIL** | `session_20261125_093843_959d7eb0` (`0–1 s` I²S startup transient) |
| **Official P01 Gate** | **NOT YET ACCEPTED** | Pending Q01 PASS, `NCC >= 0.35`, and `S1/S2 >= 70%` |
| **Clinical Validation** | **NOT CLAIMED** | Uncalibrated engineering phantom only |

*Contributors: Ege Çağın Tepe, Kaan (`kaan0443-crypto`), Ozan (`0zan0`).*
*Full report: [LAB_MILESTONE_REPORT.md](LAB_MILESTONE_REPORT.md) · Results register: [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md)*
