# AuscultaForge — EEE 495 Dönem İlerleme Durumu Raporu (As-Of 2026-11-17)

- **Tarih:** 17 Kasım 2026 Salı
- **Hedef Fiziksel Entegrasyon:** 18 Kasım 2026 Çarşamba (Kaan & Ozan — [Handoff Paketi](../handoff/README.md))
- **Resmî Dayanak Belgeleri:**
- [SDP4_Digital_Stethoscope_Plan_TR.docx](../official-docs/SDP4_Digital_Stethoscope_Plan_TR.docx) | [SDP4_Component_Requirements_EN.docx](../official-docs/SDP4_Component_Requirements_EN.docx) | [SDP_Assessment_Criteria_for_Students.docx](../official-docs/SDP_Assessment_Criteria_for_Students.docx)
- Önceki 1–6. Hafta Taslağı (korundu): [SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md](SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md)

---

## Resmî Sorumluluk Dağılımı vs. Fiilî Repo Katkısı

| Modül | Resmî Görevli | Resmî Kapsam | Repo Üzerinde Doğrulanabilir Fiilî Durum (2026-11-17) |
| :--- | :--- | :--- | :--- |
| **Modül A** | **Kaan** | Dönüştürücü, ön uç, göğüs başlığı, fantom, laboratuvar ölçümleri | Hafta 1–5 literatür, aday seçimi (`INMP441`, `KECG2740PBJ`), parça teslim envanteri (`f0f6b57`) ve mekanik taslak tamamlandı. **Fiziksel multimetre, kısa devre, gürültü tabanı ve fantom ölçümleri henüz yapılmadı (`PENDING`).** |
| **Modül B** | **Ozan** | Gömülü örnekleme, tamponlama, zaman damgası, cihaz–PC protokolü, verim/gecikme | Ön şartname ve BOM revizyonları mevcuttur. **Fiilî C/FreeRTOS firmware, TinyUSB CDC, I²S sürücüsü (`i2s_source.c`), G1/G2 derleme ve testlerin tamamı Ege tarafından yazılmıştır.** Ozan imzalı donanım ölçümü Çarşamba (18 Kasım) oturumunda alınacaktır. |
| **Modül C** | **Ege** | Bilgisayar uygulaması (FastAPI/React/Tauri), DSP, kayıt kütüphanesi, kalite kontrol, otomasyon | Tüm backend, frontend, Welch spektrogram, CirCor/CinC2016 oynatma, metrologi CLI, kontrollü artefakt enjeksiyonu, G1 USB motoru ve devir altyapısı geliştirilip birim/regresyon testleriyle doğrulandı. Fiziksel G2 ve fantom verisi bekleniyor. |

> [!IMPORTANT]
> **METODOLOJİ VE TARİHSEL DOĞRULUK İLKESİ:**
> - Hiçbir fiziksel laboratuvar testine gerçek kanıt olmadan `PASS` yazılmamıştır; simülasyon/yazılım testleri `SOFTWARE VERIFIED` olarak fiziksel ölçümlerden kesinlikle ayrılmıştır.
> - 2 Kasım–15 Kasım sınav arası dönemi için yapay lab verisi uydurulmamış, 16–17 Kasım çalışmaları gerçek tarihine yazılmıştır.
> - **Bugün (17 Kasım):** Kart fiziksel olarak bağlı olmadığı için bugünkü donanım USB testi `NOT_EXECUTED` durumundadır (26 Ekim ve 16 Kasım G1 kanıtları tarihsel referans olarak korunmaktadır).

---

## Hafta 1–14 Genel Durum Matrisi (2026-11-17 İtibarıyla)

### Dönem İçi Gerçekleşen ve Devam Eden Haftalar (Hafta 1–9)

| Hafta | Konu / Kilometre Taşı | Modül A (Kaan) | Modül B (Ozan — Resmî) | Modül C & Fiilî Entegrasyon (Ege) | Durum & Kanıt |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **W01–W05**<br>*(21 Eyl – 25 Eki)* | Takım, literatür, aday seçimi, şartname dondurma, sentetik akış | W01–W04 **PASS**; W05 **PARTIAL** (parça teslim alındı; breadboard ölçümü `PENDING`) | Şartname/BOM **PARTIAL**; fiziki G1 öncesi yazılım simülasyonu hazır | W01–W05 **PASS** (CirCor okuyucu, Welch/SNR, canlı ekran/kayıt) | [W01–W06 Taslak Rapor](SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md), `7a99ff4` |
| **W06**<br>*(26 Eki – 1 Kas)* | İlk dönüştürücü, zaman damgası sürekliliği, spektrogram & kayıt | Fiziksel kazanç/bant genişliği **`PENDING`** ([W06_A](week-06/submissions/module-a-kaan/W06_A_first-transducer-gain-bandwidth.md)) | `2026-10-26`: Fiziksel G1 (`480k` örnek) **PASS**; G2 I²S sürücüsü yazıldı (fiziksel mic `PENDING`) | **PASS** (Welch waterfall, 2/4 kHz CirCor/CinC2016, WASAPI loopback `125.16 dB`, `069b810`) | [`W06_C`](week-06/submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md), [`WEEK6_SPRINT_REPORT.md`](../engineering/release/WEEK6_SPRINT_REPORT.md) |
| **W07**<br>*(2–8 Kas + 17 Kas yazılım)* | Akustik fantom kurulumu, cihaz durum/kayıp tespiti, veri seti oynatma | Fantom kurulumu **`NOT STARTED` / `PENDING`** (göğüs başlığı/silikon bekleniyor) | Fiziksel paket kaybı raporu **`NOT STARTED` / `PENDING`** (firmware tarafı Ege kodladı) | **SOFTWARE PASS**: `WavSource`, `RealtimeWavSource`, `StimulusRecord`, `upload_source_wav`, FSM reconnect | [`W07_C_dataset-playback-path.md`](week-07/submissions/module-c-ege/W07_C_dataset-playback-path.md) |
| **W08**<br>*(9–15 Kas + 17 Kas yazılım)* | Fantom FRF taraması, 30 dk/gecikme testi, otomatik ölçüm betiği | Fantom frekans cevabı **`NOT STARTED` / `PENDING`** | Gecikme / 30 dk fiziksel koşu **`NOT_EXECUTED`** *(Not: Firmware `G1_TARGET_SAMPLES=480000U` $\approx 10\text{ s}$ limitlidir)* | **SOFTWARE PASS**: `pcg_core.metrology` CLI/workflows, `phantom.py`, `bringup.py qualify` hazır | [`W08_C_automated-measurement-script.md`](week-08/submissions/module-c-ege/W08_C_automated-measurement-script.md) |
| **W09**<br>*(16–22 Kas, As-Of 17 Kas)* | **Fizibilite Kapısı:** Fantom S1/S2, kesintisiz kayıt, kaynak–kayıt karşılaştırma | Çarşamba `18.11` H0 + ilk G2 kurulumu **`PENDING`** | `16.11`: G1 COM10 **PASS** (`480,000` örnek, 0 kayıp); `17.11`: G1+G2 IDF build + staged paketler hazır; fiziksel G2 **`PENDING`** | `16.11`: Device Center gerçek G1 WAV (`194,304` örnek) **PASS**; `17.11`: kontrollü artefakt benchmark (`5/5`) + Çarşamba devir paketi **PASS** | [`W09_C_source-capture-comparison.md`](week-09/submissions/module-c-ege/W09_C_source-capture-comparison.md), [`RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md`](../handoff/RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md) |

### Planlanan Gelecek Haftalar (Hafta 10–14 — `PLANNED`)

| Hafta | Resmî Kapsam (Modül A / B / C) | Yazılım Altyapı Hazırlığı (Ege) | Resmî Durum |
| :--- | :--- | :--- | :--- |
| **W10** | A: İki dönüştürücü karşılaştırması; B: Kazanç/filtre modu; C: Kalite eşik ayarı | `butterworth` ön ayarları (`recommended`, `bell`, `diaphragm`, `extended`) ve kalite boyutları hazır | **`PLANNED`** (Fiziksel fantom kayıtları gerekli) |
| **W11** | A: 10+ kez tekrarlanabilirlik; B: Tampon zorlama; C: Kontrollü artefakt enjeksiyonu | `compute_repeatability_study` (`workflows.py`) ve `inject_controlled_artifact` (`signal_quality.py`) hazır | **`PLANNED`** (Fiziksel tekrar ve zorlama verisi bekliyor) |
| **W12** | A: 50 Hz şebeke girişimi; B: Protokol dondurma; C: Artefakt tespit oranı | `compute_mains_interference` ve `evaluate_quality_detection_benchmark` (sentetik `%100`) hazır; `PROTOCOL` v0.1 | **`PLANNED`** (Gerçek ortam 50 Hz ölçümü ve B/C ortak dondurma bekliyor) |
| **W13** | Ara rapor yazımı (Donanım, Gömülü/Protokol, Yazılım/Karşılaştırma) | Otomatik JSON/MD/CSV rapor üreteci (`pcg_core.metrology.reports`) mevcut | **`PLANNED`** |
| **W14** | Ara rapor birleştirme ve tasarım inceleme sunum provası | Tüm takım birlikte gerçekleştirecek | **`PLANNED`** |

---

## 16–17 Kasım Somut Mühendislik Kazanımları (Özet Kanıt)

1. **Windows Üretim Ortamı ve Testler:** `662` Python/Protocol/Firmware-C testi PASS (`587` backend/bilimsel + `59` protocol lab + `16` GCC firmware host), Frontend `9` TS suite + lint + Vite build PASS (`3.93 s`).
2. **Gerçek ESP32 G1 Uçtan Uca Kanıtı (16 Kasım — Tarihsel Kanıt):** COM10 (`UID: 0xb1aa7cc4`) ile hem `bringup.py g1` (`480,000` örnek) hem de FastAPI/React Device Center üzerinden canlı `raw.wav` kaydı (`194,304` örnek, `4.048 s`, `48 kHz`, 0 kayıp, strictly `physical_deterministic_g1`) doğrulandı — özet kanıt: [`laptop_20261116_g1_and_wav_summary.json`](../../firmware/evidence/laptop_20261116_g1_and_wav_summary.json).
3. **Git'siz Çarşamba Devir ve Dönüş Paketi (17 Kasım):** GitHub Download ZIP (`GITHUB_DOWNLOAD_ZIP`) modunu destekleyen [`scripts/handoff/`](../../scripts/handoff/), tek tık sonuç paketleyici [`pack_wednesday_results.ps1`](../../scripts/handoff/pack_wednesday_results.ps1) / [`pack_lab_return.py`](../../tools/hardware/pack_lab_return.py), emniyet kilitli [`authorize-g2`](../../tools/hardware/bringup.py), staged [`firmware/releases/`](../../firmware/releases/g2_candidate_20261117/README.md) ve [`docs/handoff/`](../handoff/README.md) eksiksiz üretildi.
