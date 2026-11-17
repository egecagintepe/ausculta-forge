# AuscultaForge — EEE 495 Bitirme Tasarım Projesi I
## Dönem İçi İlerleme Raporu (1–6. Haftalar — Vize Sonrası Teslim Sürümü)

- **Ana Rapor Dönemi:** 21 Eylül 2026 – 1 Kasım 2026 (Güz Yarıyılı 1–6. Haftalar)
- **İlk Taslak Tarihi:** 29 Ekim 2026
- **Vize Sonrası Teslim Güncelleme Tarihi:** 17 Kasım 2026 *(Öğretim üyesinin vize sınavları sonrası teslim izni doğrultusunda düzenlenmiştir)*
- **Resmî Dayanak Belgeleri:**
  - Proje Planı: [`docs/official-docs/SDP4_Digital_Stethoscope_Plan_TR.docx`](../official-docs/SDP4_Digital_Stethoscope_Plan_TR.docx)
  - Bileşen Şartnamesi: [`docs/official-docs/SDP4_Component_Requirements_EN.docx`](../official-docs/SDP4_Component_Requirements_EN.docx)
  - Değerlendirme Kriterleri: [`docs/official-docs/SDP_Assessment_Criteria_for_Students.docx`](../official-docs/SDP_Assessment_Criteria_for_Students.docx)

---

> [!IMPORTANT]
> **TARİHSEL DÜRÜSTLÜK VE VİZE DÖNEMİ AÇIKLAMASI:**
> 1. **Kapsam Sınırı:** Bu ana rapor yalnızca **21 Eylül – 1 Kasım 2026 (1–6. Haftalar)** akademik aralığındaki gerçekleşen çalışmaları kapsar. **2–17 Kasım** dönemindeki vize arası ve devir hazırlıkları 1–6. haftalara geriye tarihlenmemiştir; ayrı bir ek bölümde tarihleriyle verilmiştir.
> 2. **Vize Dönemi Gecikmesi:** 2–15 Kasım tarihli vize sınavları ve laboratuvar montaj hazırlıklarının sarkması nedeniyle Modül A (analog ön uç / kısa devre gürültü tabanı / kazanç-bant genişliği ölçümü) ve Modül B fiziksel mikrofon (INMP441 G2) testleri rapor teslimi anında **eksiktir (`PENDING`)** ve 18 Kasım Çarşamba oturumuna bırakılmıştır.
> 3. **Tarihsel Hafta Ayrımı:** 26 Ekim 2026 Pazartesi günü yapılan gerçek fiziksel ESP32-S3 USB CDC G1 testi, gerçekleştiği takvim haftası olan **Hafta 6** içinde raporlanmıştır.
> 4. **Resmî Görevli vs. Fiilî Katkı Ayrımı:** Tablolarda her modülün resmî plan sorumlusu ile depoda doğrulanabilen fiilî kod/rapor katkısı ayrı sütunlarda dürüstçe gösterilmiştir.

---

### Hafta 1 (21–27 Eylül 2026)
**Kilometre Taşı:** Takım kuruldu, modüller dağıtıldı, proje anlaşıldı.

| Modül | Resmî Sorumlu | Fiilî Katkı | Yapılan İşlem (Resmî Plan Görevi) | Kanıt | Sonuç | Eksik İş |
|---|---|---|---|---|---|---|
| **Modül A** | Kaan | Kaan | Öneriyi inceledi; elektret (ECM) ve MEMS dönüştürücü adaylarını ve bölüm laboratuvar ekipmanı (osiloskop, fonksiyon üreteci, multimetre) gereksinimlerini listeledi. | [week-02/submissions/module-a-kaan/](week-02/submissions/module-a-kaan/), [official-docs/SDP4_Component_Requirements_EN.docx](../official-docs/SDP4_Component_Requirements_EN.docx) | **PASS** | Kavramsal başlangıç eksiksiz. |
| **Modül B** | Ozan | Ozan, Ege | Öneriyi inceledi; ESP32-S3 mikrodenetleyici seçeneklerini, Native USB CDC-ACM ve I²S arayüz gereksinimlerini belirledi. | [week-02/submissions/module-b-ozan/](week-02/submissions/module-b-ozan/), [ADR-0001](../engineering/decisions/ADR-0001-esp32-s3-mcu-selection.md) | **PASS** | Yok. |
| **Modül C** | Ege | Ege | Öneriyi inceledi; CirCor DigiScope (4 kHz) ve PhysioNet/CinC 2016 (2 kHz) açık veri setlerini ve temel kalite ölçütlerini (SNR, DC ofset, RMS, Welch PSD) belirledi. | [week-02/module-c-status.md](week-02/module-c-status.md) | **PASS** | Yok. |

---

### Hafta 2 (28 Eylül – 4 Ekim 2026)

| Modül | Resmî Sorumlu | Fiilî Katkı | Yapılan İşlem (Resmî Plan Görevi) | Kanıt | Sonuç | Eksik İş |
|---|---|---|---|---|---|---|
| **Modül A** | Kaan | Kaan | Kalp sesi genlik aralığını, 20–500 Hz bandını (S1/S2 20–150 Hz) ve 50 Hz şebeke / temas girişimi kaynaklarını literatürden çalıştı ve raporladı. | [`W02_A_heart-sound-characteristics_v01.pdf`](week-02/submissions/module-a-kaan/W02_A_heart-sound-characteristics_v01.pdf), [`W02_A_technical-selection-criteria_v01.pdf`](week-02/submissions/module-a-kaan/W02_A_technical-selection-criteria_v01.pdf) | **PASS** | Yok (literatür çalışması tamamlandı). |
| **Modül B** | Ozan | Ozan (teorik belge), Ege (mimari destek) | Mikrodenetleyicide 48 kHz örnekleme, DMA çift tamponlama ve zaman damgası mimarisini ve ilk BOM tablosunu taslak olarak hazırladı. | [`W02_B_system-design-technical-specification_REV01.docx`](week-02/submissions/module-b-ozan/W02_B_system-design-technical-specification_REV01.docx), [`W02_B_procurement-bom-test_REV01.xlsx`](week-02/submissions/module-b-ozan/W02_B_procurement-bom-test_REV01.xlsx) | **PASS** | Pratik C/FreeRTOS kodlaması henüz başlamamıştı (sonraki haftalar). |
| **Modül C** | Ege | Ege | Açık PCG veri seti okuyucusunu yazdı, B→C arayüz gereksinimlerini ve ölçüm/kalite planını tanımladı, örnek kayıt üzerinde ön dalga/spektrum çizimini doğruladı. | [`week-02/module-c-status.md`](week-02/module-c-status.md), [`bc-interface-requirements.md`](week-02/bc-interface-requirements.md), [`measurement-quality-plan.md`](week-02/measurement-quality-plan.md) | **PASS** | Yok (otomatik testlerle doğrulandı). |

---

### Hafta 3 (5–11 Ekim 2026)

| Modül | Resmî Sorumlu | Fiilî Katkı | Yapılan İşlem (Resmî Plan Görevi) | Kanıt | Sonuç | Eksik İş |
|---|---|---|---|---|---|---|
| **Modül A** | Kaan | Kaan | Elektret kondenser (KECG2740PBJ) ve dijital MEMS (INMP441) mikrofonları karşılaştırarak iki dönüştürücü adayını seçti ve seçim gerekçelerini yazdı. | [`W03_A_candidate-selection-report_v01.pdf`](week-03/submissions/module-a-kaan/W03_A_candidate-selection-report_v01.pdf), [`W03_A_transducer-candidate-selection.md`](week-03/submissions/module-a-kaan/W03_A_transducer-candidate-selection.md) | **PASS** | Satın alma ve fiziksel testler Hafta 4–5'e aktarıldı. |
| **Modül B** | Ozan | Ozan (belge/BOM), Ege (çerçeve tasarımı) | Haberleşme seçeneklerini değerlendirdi (Native USB vs BLE/Wi-Fi); 24-bit in 32-bit PCM + CRC-32 Profile B çerçeve taslağı ve BOM rev2 hazırlandı. | [`W03_B_device-to-host-frame-draft.md`](week-03/submissions/module-b-ozan/W03_B_device-to-host-frame-draft.md), [`W03_B_task-closeout.md`](week-03/submissions/module-b-ozan/W03_B_task-closeout.md), [`W03_B_procurement-bom-test_v02.xlsx`](week-03/submissions/module-b-ozan/W03_B_procurement-bom-test_v02.xlsx) | **PASS (Taslak)** | Çerçeve formatı ve CRC politikası fiziksel bench ölçümü beklediği için dondurulmadı (`OPEN`). |
| **Modül C** | Ege | Ege | Welch PSD, SNR, DC ofset, kırpılma kesri ve ZCR ölçütlerini Python çekirdeğinde gerçekledi ve bilinen sentetik işaretler üzerinde doğruladı. | [`W03_C_quality-metrics-validation.md`](week-03/submissions/module-c-ege/W03_C_quality-metrics-validation.md), `software/tests/` | **PASS** | Fiziksel kayıtlar üzerinde kalibrasyon eşiklemesi sonraki haftalara kaldı. |

---

### Hafta 4 (12–18 Ekim 2026)
**Kilometre Taşı:** Gereksinim şartnamesi donduruldu, temel elektronik bileşenler sipariş edildi.

| Modül | Resmî Sorumlu | Fiilî Katkı | Yapılan İşlem (Resmî Plan Görevi) | Kanıt | Sonuç | Eksik İş |
|---|---|---|---|---|---|---|
| **Modül A** | Kaan | Kaan | Veri toplama zinciri gereksinimlerini (kazanç, 20–500 Hz bant genişliği, gürültü tabanı, kırpılma payı) ve örnek yüksek geçiren hesapları raporladı. | [`W04_A_acquisition-requirements-freeze.md`](week-04/submissions/module-a-kaan/W04_A_acquisition-requirements-freeze.md), [`W04_A_acquisition-requirements-report_v01.pdf`](week-04/submissions/module-a-kaan/W04_A_acquisition-requirements-report_v01.pdf), [`W04_A_requirements-calculations_v01.py`](week-04/submissions/module-a-kaan/W04_A_requirements-calculations_v01.py) | **PASS** | Siparişlerin teslimatı bekleniyor. |
| **Modül B** | Ozan | Ozan (sipariş/şartname), Ege (protokol önerisi) | Gömülü katman gereksinimleri yazıldı; 16 Ekim 2026'da ESP32-S3 (2), INMP441 (3), MCP6022 (5), pasif set, exciter ve PAM8403 siparişi verildi. | [`W04_B_embedded-requirements-freeze.md`](week-04/submissions/module-b-ozan/W04_B_embedded-requirements-freeze.md), [`W04_B_actual-orders_2026-10-16_v01.csv`](week-04/W04_B_actual-orders_2026-10-16_v01.csv), [`procurement-closeout.md`](week-04/procurement-closeout.md), [`W04_B_procurement-bom-test_REV03.xlsx`](week-04/submissions/module-b-ozan/W04_B_procurement-bom-test_REV03.xlsx) | **PARTIAL** | **Tedarik Eksiği:** Stetoskop göğüs başlığı ve silikon fantom kuplaj malzemesi bu siparişte alınmadı; açık tedarik kalemidir. |
| **Modül C** | Ege | Ege | Bilgisayar uygulaması için canlı gösterim (25 Hz desimasyon), kayıt, JSON sidecar meta verisi, kalite geri bildirimi ve REST/WebSocket arayüz gereksinimleri donduruldu. | [`W04_C_application-requirements-freeze.md`](week-04/submissions/module-c-ege/W04_C_application-requirements-freeze.md) | **PASS** | Fiziksel protokol uçlarının B/C imzası açık. |

---

### Hafta 5 (19–25 Ekim 2026)
**Kilometre Taşı (Hedef):** Masaüstü düzeneği ve bilinen bir test işaretinin baştan sona yakalanması.

| Modül | Resmî Sorumlu | Fiilî Katkı | Yapılan İşlem (Resmî Plan Görevi) | Kanıt | Sonuç | Eksik İş |
|---|---|---|---|---|---|---|
| **Modül A** | Kaan | Kaan | Sipariş edilen parçalar (ESP32-S3, INMP441, MCP6022, pasifler, PAM8403, exciter) teslim alındı; mekanik adaptör taslağı ve Hafta 5–6 hazırlık raporu yazıldı (`7a99ff4`). | [`W05_A_material-inventory_v01.md`](week-05/submissions/module-a-kaan/W05_A_material-inventory_v01.md), [`W05_A_mechanical-design_v01.md`](week-05/submissions/module-a-kaan/W05_A_mechanical-design_v01.md), [`W05_A_acoustic-hardware-preparation-report_v01.pdf`](week-05/submissions/module-a-kaan/W05_A_acoustic-hardware-preparation-report_v01.pdf), [`W05_A_breadboard-front-end-bench-test.md`](week-05/submissions/module-a-kaan/W05_A_breadboard-front-end-bench-test.md) | **PARTIAL** | **Fiziksel Ölçüm Yok:** İlk breadboard ön ucu kurulup giriş kısa devre edilerek osiloskop/multimetre ile **gürültü tabanı ölçülmedi (`PENDING`)**; Kingstate ECM teslimatı bekleniyordu. |
| **Modül B** | Ozan | Ege (C firmware & G1 simülasyon kodu), Ozan (doküman/plan) | ESP32-S3 C firmware protokol çekirdeği, sentetik rampa üreteci ve portatif C/Python altın vektör testleri geliştirildi; G1 fiziksel bring-up planı yazıldı. | [`W05_B_g1-bringup-plan_v01.md`](week-05/submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md), `firmware/evidence/first_contact/`, [`W05_B_synthetic-stream-test.md`](week-05/submissions/module-b-ozan/W05_B_synthetic-stream-test.md) (`NOT STARTED`) | **PARTIAL (Simülasyon PASS)** | **Tarihsel Not:** Hafta 5 içinde yalnızca yazılım döngü simülasyonu geçti. Gerçek USB donanım G1 akışı 26 Ekim Pazartesi (**Hafta 6**) icra edildi. |
| **Modül C** | Ege | Ege | FastAPI/WebSocket akışı, 25 Hz canlı dalga ekranı, float32 WAV kayıt motoru, SHA-256 doğrulama ve sanal cihaz simülatörü kurularak sentetik akışla doğrulandı. | [`W05_C_live-display-recording-verification.md`](week-05/submissions/module-c-ege/W05_C_live-display-recording-verification.md), [`W05_C_host-integration-preflight_v01.md`](week-05/submissions/module-c-ege/W05_C_host-integration-preflight_v01.md), [`W05_C_host-transport-readiness_v01.md`](week-05/submissions/module-c-ege/W05_C_host-transport-readiness_v01.md) | **PASS** | Yeni arayüz ile fiziksel USB kabulü Hafta 6 içinde yapıldı. |

---

### Hafta 6 (26 Ekim – 1 Kasım 2026)

| Modül | Resmî Sorumlu | Fiilî Katkı | Yapılan İşlem (Resmî Plan Görevi) | Kanıt | Sonuç | Eksik İş |
|---|---|---|---|---|---|---|
| **Modül A** | Kaan | Kaan (kontrol listesi) | Hafta 6 test kontrol listesi (W6-A01..W6-A08) ve fiziksel inceleme planı hazırlandı; dönüştürücü bağlama ve fonksiyon üreteciyle kazanç/bant genişliği ölçümü planlandı. | [`W05_A_week06-test-readiness_v01.md`](week-05/submissions/module-a-kaan/W05_A_week06-test-readiness_v01.md), [`W06_A_first-transducer-gain-bandwidth.md`](week-06/submissions/module-a-kaan/W06_A_first-transducer-gain-bandwidth.md) (`NOT STARTED`) | **PENDING** | **Fiziksel kazanç/bant genişliği ölçümü ve INMP441 lehim/3.3V kontrolü YAPILMADI.** Vize sınavları nedeniyle Çarşamba (18.11) oturumuna ertelendi. |
| **Modül B** | Ozan | Ege (donanım G1, I²S sürücüsü, yedekleme) | **1. Fiziksel G1 Başarısı (26.10.2026):** Gerçek ESP32-S3 Native USB CDC üzerinden `480.000` örnek / `1.875` frame **0 kayıp** ile aktarıldı (`106d3e0` CLI & `59d773e` GUI).<br>**2. G2 I²S Sürücüsü (`i2s_source.c`):** 48 kHz Philips I²S 24-in-32 sürücüsü yazıldı ve 16/16 C birim testinden geçti.<br>**3. Rollback Yedeği:** Çalışan G1 binary'si `firmware/g1_rollback_backup/` içine kilitlendi (`319fcc5`). | [`WEEK6_SPRINT_REPORT.md`](../engineering/release/WEEK6_SPRINT_REPORT.md), [`firmware/g1_rollback_backup/README.md`](../../firmware/g1_rollback_backup/README.md), [`W06_B_real-input-timestamp-continuity.md`](week-06/submissions/module-b-ozan/W06_B_real-input-timestamp-continuity.md) (`NOT STARTED`) | **G1: PASS**<br>**G2: PARTIAL (Sürücü hazır, fiziksel akış PENDING)** | Gerçek INMP441 fiziksel bağlantısı, 3.3V ölçümü ve gerçek mikrofon zaman damgası sürekliliği Çarşamba (18.11) oturumunda test edilecek; Ozan'a ait imza/kayıt henüz yoktur. |
| **Modül C** | Ege | Ege | **1. Canlı Spektrogram & Kayıt:** Welch PSD şelalesi, 15 s eksen, oturum izolasyonu, float32 WAV + SHA-256 doğrulandı.<br>**2. Gerçek PCG Dosya Kabulü:** CirCor (`40058_AV`, `24160_MV`, `49568_PV`, `49627_TV`) ve Challenge 2016 (`a0001`) ile doğrulandı.<br>**3. Masaüstü Ses Kabulü:** Windows WASAPI loopback (`125.16 dB` SNR, çift filtre hatası fix `9b480a4`, `069b810`). | [`W06_C_spectrogram-recording-metadata.md`](week-06/submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md), [`WEEK6_OFFLINE_REAL_PCG_REPORT.md`](../engineering/release/WEEK6_OFFLINE_REAL_PCG_REPORT.md), [`WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md`](../engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md), [`WEEK6_AUDIO_FIX_RELEASE_VERIFICATION.md`](../engineering/release/WEEK6_AUDIO_FIX_RELEASE_VERIFICATION.md) | **PASS (Yazılım & Masaüstü)** | Gerçek mikrofon G2 canlı spektrum kaydı ve fiziksel kulaklık dinleme kabulü `PENDING`. |

---

### Ek Bölüm: Vize Sonrası Durum Notu (2–17 Kasım) ve 18 Kasım Çarşamba Fiziksel Ölçüm Alanı

#### A. 2–17 Kasım 2026 Özeti (Ana 1–6. Hafta Kapsamının Dışındadır)
- **2–15 Kasım:** Vize sınavları nedeniyle proje ve fiziksel laboratuvar çalışmalarına ara verildi. Bu aralık için yapay test veya ölçüm üretilmemiştir.
- **16–17 Kasım (Güncel Devir Hazırlığı):** Yeni Windows geliştirme ortamı kuruldu; gerçek ESP32-S3 üzerinde **G1 regresyonu (`480.000` örnek, 0 kayıp)** ve Device Center üzerinden **sentetik G1 WAV kaydı (`194.304` örnek)** tekrar doğrulandı ([`firmware/evidence/laptop_20261116_g1_and_wav_summary.json`](../../firmware/evidence/laptop_20261116_g1_and_wav_summary.json)). Kaan ve Ozan'ın 18 Kasım Çarşamba günü Git kullanmadan çalışabileceği devir paketleri ([`docs/handoff/README.md`](../handoff/README.md)) hazırlandı. Tam 1–14. hafta değerlendirmesi [`PROGRESS_ASOF_2026-11-17.md`](PROGRESS_ASOF_2026-11-17.md) içindedir.

#### B. 18 Kasım Çarşamba Fiziksel Ölçüm Tablosu (**HENÜZ DOLDURULMADI — LAB OTURUMU BEKLENİYOR**)

> [!NOTE]
> Aşağıdaki alanlar **Kaan (Modül A)** ve **Ozan (Modül B)** tarafından **18 Kasım 2026 Çarşamba** fiziksel laboratuvar oturumunda ölçülen **gerçek değerlerle** doldurulacaktır. Boş alanlar hiçbir test yapılmadığının açık kanıtıdır.

| Kapı / Ölçüm | Sorumlu | Ölçüm Cihazı / Port | Beklenen Sınır | Gerçekleşen Ölçüm / Çıktı | Kanıt Dosyası / Hash | Durum |
|---|---|---|---|---|---|---|
| **H0.1:** ESP32 & INMP441 çift taraflı fotoğraf + alt akustik port açıklığı | Kaan | Kamera | Pin yazıları okunur, lehim köprüsü yok, alt port açık | `[HENÜZ ÖLÇÜLMEDİ]` | `[foto dosya adları]` | **NOT_EXECUTED** |
| **H0.2:** Güçsüz süreklilik ve `VDD–GND` kısa devre kontrolü | Kaan | `[Multimetre ID]` | Kısa devre yok (`Open / >MΩ`), süreklilik tam | `[HENÜZ ÖLÇÜLMEDİ]` | `[ölçüm notu]` | **NOT_EXECUTED** |
| **H0.3:** ESP32 `3V3` – `GND` besleme voltajı (mikrofon ayrıyken) | Kaan | `[Multimetre ID]` | `3.15 V .. 3.45 V` (ASLA 5V değil) | `[_____ V]` | `[g2_physical_attestation.json]` | **NOT_EXECUTED** |
| **H0.4:** Gerçek doğrulanan I²S GPIO pinleri & L/R slot | Kaan & Ozan | PCB Silkscreen | Provisional: `BCLK=4, WS=5, DIN=6, L/R=GND` | `[GPIO_BCLK=?, WS=?, DIN=?, L/R=?]` | `[g2_physical_attestation.json]` | **NOT_EXECUTED** |
| **G1:** Lab PC üzerinde gerçek ESP32 USB CDC G1 testi | Ozan | `[COM_CDC]` | `PHYSICAL_G1_PASSED`, `480.000` örnek, `0` kayıp | `[HENÜZ ÇALIŞTIRILMADI]` | `[experiments/hardware/<bundle>]` | **NOT_EXECUTED** |
| **G2.1:** Yetkilendirme + Flash + G2 sonrası G1 fallback kontrolü | Ozan | `[COM_ROM -> COM_CDC]` | `source_modes: [1, 0]`, G1 hâlâ `PASS` | `[HENÜZ YAPILMADI]` | `[g2_physical_attestation.json]` | **NOT_EXECUTED** |
| **G2.2:** Sessiz oda canlı mikrofon kaydı (`source_mode=0`, 10 s) | Ozan & Kaan | Device Center | `constant_zero: false`, `48 kHz`, `0` overflow | `[session_id / RMS / Peak / DC]` | `[g2-quiet.json]` | **NOT_EXECUTED** |
| **G2.3:** Kontrollü ses uyaranı canlı kaydı (`source_mode=0`, 10 s) | Ozan & Kaan | Device Center | Stimulus RMS > Quiet RMS, `saturation == 0` | `[session_id / RMS / Peak / Saturasyon]` | `[g2-stimulus.json]` | **NOT_EXECUTED** |
| **Modül A Ek:** Breadboard ECM/op-amp kısa devre gürültüsü & kazanç | Kaan | Osiloskop / Fonksiyon Üreteci | Devre kazancı ve `-3 dB` alt/üst kesim | `[HENÜZ ÖLÇÜLMEDİ]` | `[W05_A / W06_A ölçüm dosyası]` | **NOT_EXECUTED** |
