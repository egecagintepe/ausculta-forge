# AuscultaForge — EEE 495 Bitirme Tasarım Projesi I
## Dönem İçi İlerleme Raporu Taslağı (1–6. Haftalar) — DRAFT

**Tarih:** 29 Ekim 2026  
**Akademik Takvim Aralığı:** 21 Eylül 2026 – 1 Kasım 2026 (Güz Yarıyılı 1–6. Haftalar)  
**Resmî Dayanak Belgeleri:**
- Proje Planı: [`docs/official-docs/SDP4_Digital_Stethoscope_Plan_TR.docx`](../official-docs/SDP4_Digital_Stethoscope_Plan_TR.docx)
- Bileşen Şartnamesi: [`docs/official-docs/SDP4_Component_Requirements_EN.docx`](../official-docs/SDP4_Component_Requirements_EN.docx)
- Değerlendirme Kriterleri: [`docs/official-docs/SDP_Assessment_Criteria_for_Students.docx`](../official-docs/SDP_Assessment_Criteria_for_Students.docx)

---

### Resmî Modül Dağılımı ve Fiilî Katkı Durumu

| Modül | Resmî Başlık ve Sorumluluk (Resmî Plan Tablo 6) | Resmî Görevli | Fiilen Yapılan Çalışma ve Doğrulanabilir Katkı |
|---|---|---|---|
| **Modül A** | Veri toplama donanımı ve karakterizasyon: Dönüştürücü karşılaştırması, analog ön uç, mekanik kuplaj ve göğüs başlığı, akustik fantom, masaüstü ölçümleri. | **Kaan** | Literatür araştırması, ECM/MEMS aday seçimi, malzeme teslim envanteri, mekanik 3D konsept çizimleri ve Hafta 6 test kontrol listesi hazırlandı. Fiziksel gürültü/kazanç ölçümleri henüz yapılmadı (PENDING). |
| **Modül B** | Gömülü veri toplama ve veri yolu: Mikrodenetleyicide örnekleme, tamponlama ve zaman damgalama, cihaz-bilgisayar protokolü, kendi kendine test, gecikme/verim ölçümü. | **Ozan** | Ön gereksinim ve şartname taslakları çalışıldı. *Fiilî C/FreeRTOS firmware geliştirme, USB CDC binary protokol motoru, I²S sürücüsü ve donanım test altyapısı fiilen Ege tarafından gerçekleştirilmiştir.* Ozan imzalı fiziksel ölçüm kaydı henüz depoda mevcut değildir; yapılmamış çalışma atfedilmemiştir. |
| **Modül C** | Bilgisayar uygulaması ve kalite değerlendirmesi: Canlı dalga biçimi ve spektrogram gösterimi, kayıt kütüphanesi, sinyal işleme zinciri, kalite kontrolü ve otomatik değerlendirme. | **Ege** | FastAPI/WebSocket arka ucu, Tauri/React masaüstü uygulaması, Welch PSD şelalesi, çoklu filtre transfer fonksiyonları, WASAPI loopback ses testi, deterministik doğrulama testleri ve G1/G2 entegrasyon testlerinin tamamı Ege tarafından geliştirildi ve doğrulandı. |

> [!IMPORTANT]
> **DRAFT METODOLOJİ NOTU:** Bu taslak, 2 Kasım 2026 tarihindeki resmî teslim öncesinde durum tespiti amacıyla üretilmiştir.
> - Fiziksel laboratuvar doğrulaması yapılmamış hiçbir maddeye `PASS` verilmemiştir.
> - 26 Ekim 2026 tarihinde icra edilen fiziksel ESP32-S3 USB CDC G1 testi, gerçekleştiği takvim haftası olan **Hafta 6 (26 Ekim – 1 Kasım)** içine yerleştirilmiştir; Hafta 5'e geriye tarihleme yapılmamıştır.
> - Satın alınmamış stetoskop göğüs parçası ve fantom malzemeleri sipariş edilmiş gibi gösterilmemiştir.
> - Cuma günü (30 Ekim) yapılacak fiziksel deneylerin sonuçları boş/PENDING bırakılmıştır.

---

### Hafta 1 (21–27 Eylül 2026)
**Kilometre Taşı (1. Hafta):** Takım kuruldu, modüller dağıtıldı, proje anlaşıldı.

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma ve Kanıt | Sorumlu / Katkı | Durum | Eksik Kanıt / Açık Kalan |
|---|---|---|---|---|---|
| **Modül A** | Öneriyi oku. Dönüştürücü adaylarını ve gereken masaüstü ekipmanı listele. | Proje önerisi ve bileşen listesi incelendi. ECM ve MEMS aday kategorileri belirlendi; laboratuvar osiloskop/fonksiyon üreteci gereksinimleri çıkarıldı. | Kaan | **PASS** | Yok (kavramsal başlangıç tamamlandı). |
| **Modül B** | Öneriyi oku. Mikrodenetleyici seçeneklerini ve arayüz gereksinimlerini belirle. | ESP32-S3 mimarisi, donanımsal USB OTG/CDC ve I²S çevresel birim gereksinimleri incelendi. | Ozan, Ege | **PASS** | Yok. |
| **Modül C** | Öneriyi oku. Açık veri setlerini ve kullanılacak kalite ölçütlerini belirle. | CirCor DigiScope ve PhysioNet/CinC 2016 veri setleri incelendi. SNR, DC ofset, RMS ve Welch PSD temel kalite parametreleri olarak belirlendi. | Ege | **PASS** | Yok. |

---

### Hafta 2 (28 Eylül – 4 Ekim 2026)

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma ve Kanıt | Sorumlu / Katkı | Durum | Eksik Kanıt / Açık Kalan |
|---|---|---|---|---|---|
| **Modül A** | Kalp sesi özelliklerini çalış: genlik aralığı, frekans bandı ve girişim kaynakları. | Kalp sesi frekans bantları (S1/S2 20–150 Hz, üfürümler 500 Hz'e kadar) ve temas/şebeke gürültüsü raporlandı.<br>Kanıt: [`W02_A_heart-sound-characteristics_v01.pdf`](week-02/submissions/module-a-kaan/W02_A_heart-sound-characteristics_v01.pdf), [`W02_A_technical-selection-criteria_v01.pdf`](week-02/submissions/module-a-kaan/W02_A_technical-selection-criteria_v01.pdf) | Kaan | **PASS** | Yok (literatür analizi tamamlandı). |
| **Modül B** | Mikrodenetleyicide ses toplamayı çalış: örnekleme, tamponlama ve zaman damgalama. | Çift tamponlama (DMA ping-pong), donanım zaman damgası ve 48 kHz örnekleme parametreleri teorik olarak modellendi.<br>Kanıt: [`W02_B_system-design-technical-specification_REV01.docx`](week-02/submissions/module-b-ozan/W02_B_system-design-technical-specification_REV01.docx), [`W02_B_procurement-bom-test_REV01.xlsx`](week-02/submissions/module-b-ozan/W02_B_procurement-bom-test_REV01.xlsx) | Ozan (teorik), Ege (tasarım desteği) | **PASS** | Yok (teorik modelleme). |
| **Modül C** | Veri setini indir, bir okuyucu yaz ve bir kaydı çiz. | CirCor veri okuyucusu yazıldı; dalga biçimi ve ön spektrum çizimi doğrulandı.<br>Kanıt: [`week-02/submissions/module-c-ege/README.md`](week-02/submissions/module-c-ege/README.md), [`week-02/module-c-status.md`](week-02/module-c-status.md) | Ege | **PASS** | Yok (otomasyon testleriyle doğrulandı). |

---

### Hafta 3 (5–11 Ekim 2026)

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma ve Kanıt | Sorumlu / Katkı | Durum | Eksik Kanıt / Açık Kalan |
|---|---|---|---|---|---|
| **Modül A** | Elektret kondenser ve mikroelektromekanik mikrofonları çalış, karşılaştırma için iki aday seç. | Aday 1 olarak ECM (Kingstate KECG2740PBJ) ve Aday 2 olarak dijital MEMS (INMP441) seçildi.<br>Kanıt: [`W03_A_candidate-selection-report_v01.pdf`](week-03/submissions/module-a-kaan/W03_A_candidate-selection-report_v01.pdf), [`W03_A_transducer-candidate-selection.md`](week-03/submissions/module-a-kaan/W03_A_transducer-candidate-selection.md) | Kaan | **PASS** | Yok. |
| **Modül B** | Haberleşme seçeneklerini çalış ve cihaz-bilgisayar aktarımı için çerçeve biçimini taslak hâline getir. | USB CDC-ACM üzerinden binary çerçeve taslağı (Profile B, 24-bit PCM, S32 kap, CRC-32) hazırlandı.<br>Kanıt: [`W03_B_device-to-host-frame-draft.md`](week-03/submissions/module-b-ozan/W03_B_device-to-host-frame-draft.md), [`W03_B_task-closeout.md`](week-03/submissions/module-b-ozan/W03_B_task-closeout.md), [`W03_B_procurement-bom-test_v02.xlsx`](week-03/submissions/module-b-ozan/W03_B_procurement-bom-test_v02.xlsx) | Ozan, Ege | **PASS** | Yok. |
| **Modül C** | Kalite ölçütlerini gerçekle ve etiketi bilinen kayıtlar üzerinde doğrula. | Welch PSD, SNR, clipping fraksiyonu ve pencereleme algoritmaları kodlandı ve doğrulandı.<br>Kanıt: [`W03_C_quality-metrics-validation.md`](week-03/submissions/module-c-ege/W03_C_quality-metrics-validation.md) | Ege | **PASS** | Yok. |

---

### Hafta 4 (12–18 Ekim 2026)
**Kilometre Taşı (4. Hafta):** Gereksinim şartnamesi donduruldu, bileşenler seçildi ve sipariş edildi, araçlar kuruldu.

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma ve Kanıt | Sorumlu / Katkı | Durum | Eksik Kanıt / Açık Kalan |
|---|---|---|---|---|---|
| **Modül A** | Veri toplama zinciri için gereksinimleri yaz: kazanç, bant genişliği, gürültü tabanı ve kırpılma payı. | Kazanç, filtre kesim frekansları ve dinamik aralık şartnamesi donduruldu.<br>Kanıt: [`W04_A_acquisition-requirements-freeze.md`](week-04/submissions/module-a-kaan/W04_A_acquisition-requirements-freeze.md), [`W04_A_acquisition-requirements-report_v01.pdf`](week-04/submissions/module-a-kaan/W04_A_acquisition-requirements-report_v01.pdf), [`W04_A_illustrative-highpass_v01.csv`](week-04/submissions/module-a-kaan/W04_A_illustrative-highpass_v01.csv), [`W04_A_requirements-calculations_v01.py`](week-04/submissions/module-a-kaan/W04_A_requirements-calculations_v01.py) | Kaan | **PASS** | Fiziksel parça siparişleri bu haftada verildi, teslimat bekleniyor. |
| **Modül B** | Gömülü katman için gereksinimleri yaz: örnekleme hızı, tampon derinliği, zaman damgası sürekliliği ve verim. | Gömülü mimari donduruldu; 16 Ekim 2026 tarihinde resmî sipariş listesi verildi.<br>Kanıt: [`W04_B_embedded-requirements-freeze.md`](week-04/submissions/module-b-ozan/W04_B_embedded-requirements-freeze.md), [`W04_B_actual-orders_2026-10-16_v01.csv`](week-04/W04_B_actual-orders_2026-10-16_v01.csv), [`procurement-closeout.md`](week-04/procurement-closeout.md), [`W04_B_procurement-bom-test_REV03.xlsx`](week-04/submissions/module-b-ozan/W04_B_procurement-bom-test_REV03.xlsx) | Ozan, Ege | **PARTIAL** | **Tedarik Açıklığı:** 16 Ekim siparişinde ESP32-S3 (2), INMP441 (3), MCP6022 (5), breadboard/jumper, pasif R/C, exciter ve PAM8403 sipariş edildi. **Stetoskop göğüs parçası ve akustik fantom malzemeleri sipariş edilmemiştir; açık tedarik kalemidir.** |
| **Modül C** | Bilgisayar uygulaması için gereksinimleri yaz: gösterim, kayıt, meta veri ve kalite geri bildirimi. | REST API, WebSocket streaming, 25 Hz ekran desimasyonu ve yan dosya (sidecar JSON) şartnamesi donduruldu.<br>Kanıt: [`W04_C_application-requirements-freeze.md`](week-04/submissions/module-c-ege/W04_C_application-requirements-freeze.md) | Ege | **PASS** | Yok. |

---

### Hafta 5 (19–25 Ekim 2026)
**Kilometre Taşı (5. Hafta):** Masaüstü düzeneği çalışıyor, bilinen bir test işareti baştan sona yakalandı.

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma ve Kanıt | Sorumlu / Katkı | Durum | Eksik Kanıt / Açık Kalan |
|---|---|---|---|---|---|
| **Modül A** | İlk breadboard ön ucunu kur. Girişi kısa devre ederek gürültü tabanını ölç. | Kaan sipariş edilen parçaları teslim aldı (ESP32-S3, INMP441, pasifler, MCP6022, exciter, PAM8403; Kingstate teslimatı bekleniyor). Mekanik göğüs parçası adaptör taslağı hazırlandı.<br>Kanıt: [`W05_A_material-inventory_v01.md`](week-05/submissions/module-a-kaan/W05_A_material-inventory_v01.md), [`W05_A_mechanical-design_v01.md`](week-05/submissions/module-a-kaan/W05_A_mechanical-design_v01.md), [`W05_A_acoustic-hardware-preparation-report_v01.pdf`](week-05/submissions/module-a-kaan/W05_A_acoustic-hardware-preparation-report_v01.pdf), [`W05_A_breadboard-front-end-bench-test.md`](week-05/submissions/module-a-kaan/W05_A_breadboard-front-end-bench-test.md) | Kaan | **PARTIAL** | **Fiziksel gürültü tabanı ve kısa devre ölçümü YAPILMADI (PENDING).** Rapor hazırlık aşamasında kaldı; masaüstü osiloskop/multimetre ölçümü eksiktir. |
| **Modül B** | Geliştirme kartını çalıştır. Sentetik bir dalga biçimini bilgisayara akıt ve örnek kaybı olmadığını doğrula. | ESP32-S3 kartı teslim alındı. Ege tarafından C firmware çekirdeği geliştirildi; sentetik rampa algoritması kodlandı; yazılım köprü ve simülasyon testleriyle (16/16) doğrulandı.<br>Kanıt: [`W05_B_synthetic-stream-test.md`](week-05/submissions/module-b-ozan/W05_B_synthetic-stream-test.md), [`W05_B_g1-bringup-plan_v01.md`](week-05/submissions/module-b-ozan/W05_B_g1-bringup-plan_v01.md) | Ege (firmware/test), Ozan (hazırlık) | **PARTIAL (Simülasyon PASS)** | **Tarihsel Ayrım:** Hafta 5 içinde yazılım simülasyonu başarıyla geçti. Fiziksel donanım üzerindeki ilk USB CDC akış testi ise 26 Ekim Pazartesi günü (Hafta 6) icra edilmiştir. Geriye tarihleme yapılmamıştır. |
| **Modül C** | Canlı gösterimi ve kayıt işlevini kur. Modül B'den gelen sentetik akışla doğrula. | Canlı dalga biçimi, 25 Hz desimasyon, kayıt motoru, float32 WAV yazımı ve oturum meta verisi kuruldu. Sentetik akışlarla doğrulandı.<br>Kanıt: [`W05_C_live-display-recording-verification.md`](week-05/submissions/module-c-ege/W05_C_live-display-recording-verification.md), [`W05_C_host-integration-preflight_v01.md`](week-05/submissions/module-c-ege/W05_C_host-integration-preflight_v01.md), [`W05_C_host-transport-readiness_v01.md`](week-05/submissions/module-c-ege/W05_C_host-transport-readiness_v01.md) | Ege | **PASS** | Yok (yazılım entegrasyonu tam kanıtlı). |

---

### Hafta 6 (26 Ekim – 1 Kasım 2026 — Devam Eden Hafta)

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma ve Kanıt | Sorumlu / Katkı | Durum | Eksik Kanıt / Açık Kalan |
|---|---|---|---|---|---|
| **Modül A** | İlk dönüştürücüyü bağla. Fonksiyon üreteciyle kazancı ve bant genişliğini ölç. | Hafta 6 test kontrol listesi (W6-A01..W6-A08) hazırlandı. 30 Ekim Cuma laboratuvar seansı için fiziksel kontrol hazırlığı yapıldı.<br>Kanıt: [`W05_A_week06-test-readiness_v01.md`](week-05/submissions/module-a-kaan/W05_A_week06-test-readiness_v01.md), [`W06_A_first-transducer-gain-bandwidth.md`](week-06/submissions/module-a-kaan/W06_A_first-transducer-gain-bandwidth.md) | Kaan | **PENDING** | **Fiziksel dönüştürücü kazanç/bant genişliği ölçümü henüz yapılmadı.** 30 Ekim Cuma laboratuvar seansı beklenmektedir. |
| **Modül B** | Sentetik kaynağı gerçek çevirici girişiyle değiştir. Zaman damgası sürekliliğini doğrula. | **1. Fiziksel G1 Başarısı (26 Ekim):** Fiziksel ESP32-S3 USB CDC üzerinden 480.000 örnek / 1875 çerçeve sıfır kayıpla aktarıldı (`PHYSICAL_G1_PASSED`).<br>Kanıt: `experiments/hardware/week6_20261026_sprint/cli-g1/20261026T075048Z_f26df565/acceptance_report.md`<br>**2. G2 I²S Sürücüsü:** Gerçek INMP441 kaynağı (Source 0) firmware'de yazıldı; 48 kHz, 32-bit slot, işaret genişletme ve DMA kuyruğu birim testlerinde (16/16) doğrulandı.<br>**3. G1 İmmutable Rollback:** Çalışan G1 firmware'i `firmware/g1_rollback_backup/` altına yedeklendi ve doğrulandı.<br>Kanıt: [`W06_B_real-input-timestamp-continuity.md`](week-06/submissions/module-b-ozan/W06_B_real-input-timestamp-continuity.md) | Ege (firmware, USB, testler) | **G1: PASS**<br>**G2: PARTIAL (Sürücü hazır, fiziksel mikrofon akışı PENDING)** | Fiziksel INMP441 bağlantısı, 3.3V ölçümü ve gerçek akustik zaman damgası sürekliliği 30 Ekim Cuma seansında test edilecektir. |
| **Modül C** | Spektrogram görünümünü ve meta veri alanlarıyla kayıt kütüphanesini ekle. | **1. Canlı Spektrogram & Meta Veri:** Welch PSD şelalesi, 15 sn zaman ekseni, oturum sıfırlama, float32 WAV ve SHA-256 doğrulandı.<br>**2. Çevrimdışı Gerçek PCG Kabulü:** CirCor (C1–C4) ve Challenge 2016 (P1) kayıtları üzerinden filtre tutarlılığı doğrulandı.<br>**3. Otonom Masaüstü Ses Kabulü:** Windows WASAPI loopback üzerinden sürekli PCM ses akışı (125.16 dB loopback SNR, 0.5s kesilme hatası giderildi) kanıtlandı.<br>Kanıt: [`W06_C_spectrogram-recording-metadata.md`](week-06/submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md), [`WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md`](../engineering/release/WEEK6_AUTONOMOUS_NATIVE_AUDIO_ACCEPTANCE.md), [`WEEK6_AUDIO_FIX_RELEASE_VERIFICATION.md`](../engineering/release/WEEK6_AUDIO_FIX_RELEASE_VERIFICATION.md) | Ege | **PASS (Yazılım, masaüstü ve ses)** | Fiziksel insan kulağı dinleme kabulü ve G2 mikrofon entegrasyonu PENDING. |

---

### Durum Özeti ve Açık Riskler (29 Ekim 2026 İtibarıyla)

1. **Yazılım, Masaüstü ve Gömülü Sürücü Durumu:** Yazılım ve derleme testleri hazır, fiziksel G2 bekleniyor. 587 Python testi, 16 firmware testi, 9 frontend test paketi ve 6 Rust testi eksiksiz geçmiştir.
2. **Fiziksel G1 Durumu:** 26 Ekim 2026 tarihinde fiziksel ESP32-S3 kartı üzerinde USB CDC deterministik aktarım testi başarıyla tamamlanmış (`PHYSICAL_G1_PASSED`) ve kanıtları arşivlenmiştir.
3. **Fiziksel G2 ve Akustik Durumu (PENDING):** INMP441 fiziksel bağlantısı, 3.3V ray ölçümü, osiloskop saat doğrulaması ve ilk gerçek mikrofon akışı **30 Ekim 2026 Cuma laboratuvar seansında** gerçekleştirilecektir.
4. **Tedarik ve Donanım Eksikleri:**
   - Stetoskop göğüs parçası ve akustik fantom malzemeleri henüz satın alınmamıştır; bu durum Hafta 7–8 fantom takvimini etkilememesi için ivedilikle çözülmelidir.
   - Kingstate elektret mikrofonun kargo teslimatı beklenmektedir.
   - Modül A ve Modül B'nin bağımsız laboratuvar cihazı ölçüm kayıtları Cuma günkü seansla birlikte oluşturulacaktır.
