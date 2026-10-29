# AuscultaForge — EEE 495 Bitirme Tasarım Projesi I
## Dönem İçi İlerleme Raporu Taslağı (1–6. Haftalar) — DRAFT

**Tarih:** 29 Ekim 2026  
**Kaynak Belgeler:**
- `docs/official-docs/SDP4_Digital_Stethoscope_Plan_TR.docx`
- `docs/official-docs/SDP4_Component_Requirements_EN.docx`
- `docs/official-docs/SDP_Assessment_Criteria_for_Students.docx`

**Fiilî Ekip Rol Dağılımı:**
- **Modül A (Veri Toplama Donanımı ve Karakterizasyon):** Kaan (Akustik/mekanik montaj, transdüser)
- **Modül B (Gömülü Veri Toplama ve Veri Yolu):** Ozan (Elektronik montaj, güç, ölçü aletleri)
- **Modül C (Bilgisayar Uygulaması ve Kalite Değerlendirmesi):** Ege (Firmware, I²S/USB sürücüsü, masaüstü uygulaması, DSP, testler)

> **DRAFT NOTU:** Bu belge, 2 Kasım 2026 tarihinde danışman hocaya sunulacak ilerleme raporu için iç çalışma taslağıdır. 30 Ekim 2026 Cuma günü yapılacak fiziksel G2 deneylerinin sonuç haneleri boş bırakılmıştır; tamamlanmamış veya fiziksel doğrulaması yapılmamış hiçbir çalışma başarılı sayılmamıştır.

---

### Hafta 1 (22–28 Eylül 2026)
**Kilometre Taşı:** Takım kuruldu, modüller dağıtıldı, proje anlaşıldı.

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma (Kanıtlı) | Fiilen Katkı Veren | Durum | Eksik Kanıt |
|---|---|---|---|---|---|
| **Modül A** | Öneriyi oku. Dönüştürücü adaylarını ve gereken masaüstü ekipmanı listele. | Öneri okundu; ECM ve MEMS mikrofon kategorileri ile laboratuvar masaüstü ölçüm cihazları (osiloskop, fonksiyon üreteci, multimetre) incelendi. | Kaan | **PASS** | Yok (kavramsal başlangıç tamamlandı). |
| **Modül B** | Öneriyi oku. Mikrodenetleyici seçeneklerini ve arayüz gereksinimlerini belirle. | ESP32-S3 mimarisi, donanımsal USB OTG/CDC ve I²S çevresel birim gereksinimleri belirlendi. | Ozan, Ege | **PASS** | Yok. |
| **Modül C** | Öneriyi oku. Açık veri setlerini ve kullanılacak kalite ölçütlerini belirle. | PhysioNet CirCor DigiScope ve PhysioNet/CinC 2016 veri setleri incelendi; SNR, DC ofset, RMS ve Welch PSD ölçütleri tanımlandı. | Ege | **PASS** | Yok. |

---

### Hafta 2 (29 Eylül – 5 Ekim 2026)

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma (Kanıtlı) | Fiilen Katkı Veren | Durum | Eksik Kanıt |
|---|---|---|---|---|---|
| **Modül A** | Kalp sesi özelliklerini çalış: genlik aralığı, frekans bandı ve girişim kaynakları. | `W02_A_heart-sound-characteristics.md` raporlandı: S1/S2 frekans bandı (20–150 Hz, üfürümler 500 Hz'e kadar), temas gürültüsü ve 50 Hz şebeke girişimi incelendi. | Kaan | **PASS** | Yok (literatür analizi tamamlandı). |
| **Modül B** | Mikrodenetleyicide ses toplamayı çalış: örnekleme, tamponlama ve zaman damgalama. | Çift tamponlama (DMA ping-pong), donanım zaman damgası ve 48 kHz örnekleme parametreleri teorik olarak modellendi (`W02_B_system-design-technical-spec_v01.md`). | Ozan, Ege | **PASS** | Yok. |
| **Modül C** | Veri setini indir, bir okuyucu yaz ve bir kaydı çiz. | CirCor DigiScope veri seti okuyucusu yazıldı; dalga biçimi ve ön spektrum çizimi test edildi (`software/pcg_app/circor_adapter.py`, `software/tests/test_circor_adapter.py`). | Ege | **PASS** | Yok (otomasyon testleriyle doğrulandı). |

---

### Hafta 3 (6–12 Ekim 2026)

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma (Kanıtlı) | Fiilen Katkı Veren | Durum | Eksik Kanıt |
|---|---|---|---|---|---|
| **Modül A** | Elektret kondenser ve MEMS mikrofonları çalış, karşılaştırma için iki aday seç. | `W03_A_candidate-selection-report_v01.md`: Aday 1 olarak ECM (Kingstate/CUI) ve Aday 2 olarak dijital MEMS (INMP441) belirlendi. | Kaan | **PASS** | Yok. |
| **Modül B** | Haberleşme seçeneklerini çalış ve cihaz-bilgisayar aktarımı için çerçeve biçimini taslak hâline getir. | USB CDC-ACM üzerinden binary çerçeve taslağı (Profile B, 24-bit PCM, S32 kap, CRC-32) hazırlandı (`W03_B_device-to-host-frame-draft_v01.md`). | Ozan, Ege | **PASS** | Yok. |
| **Modül C** | Kalite ölçütlerini gerçekle ve etiketi bilinen kayıtlar üzerinde doğrula. | Welch PSD, SNR, clipping fraksiyonu ve enerji oranı algoritmaları kodlandı ve birim testleriyle doğrulandı (`software/pcg_core/scientific/`, `software/tests/test_scientific_signal_quality.py`). | Ege | **PASS** | Yok. |

---

### Hafta 4 (13–19 Ekim 2026)
**Kilometre Taşı:** Gereksinim şartnamesi donduruldu, bileşenler seçildi ve sipariş edildi, araçlar kuruldu.

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma (Kanıtlı) | Fiilen Katkı Veren | Durum | Eksik Kanıt |
|---|---|---|---|---|---|
| **Modül A** | Veri toplama zinciri için gereksinimleri yaz: kazanç, bant genişliği, gürültü tabanı ve kırpılma payı. | `W04_A_acquisition-requirements-spec_v01.md` hazırlandı. Bileşen sipariş listesi (stetoskop göğüs parçası, INMP441, pasif bileşenler) oluşturuldu. | Kaan | **PASS** | Fiziksel parça teslimatı bu haftada henüz gerçekleşmedi (sipariş aşaması). |
| **Modül B** | Gömülü katman için gereksinimleri yaz: örnekleme hızı, tampon derinliği, zaman damgası sürekliliği ve verim. | `W04_B_embedded-requirements-freeze_v01.md` ve sipariş listesi donduruldu. ESP32-S3-DevKitC-1 N16R8 siparişi verildi (`W04_B_actual-orders_2026-10-16_v01.csv`). | Ozan, Ege | **PASS** | Yok. |
| **Modül C** | Bilgisayar uygulaması için gereksinimleri yaz: gösterim, kayıt, meta veri ve kalite geri bildirimi. | `W04_C_application-requirements-freeze_v01.md`: REST API, WebSocket streaming, 25 Hz ekran desimasyonu ve yan dosya (sidecar JSON) gereksinimleri donduruldu. | Ege | **PASS** | Yok. |

---

### Hafta 5 (20–26 Ekim 2026)
**Kilometre Taşı:** Masaüstü düzeneği çalışıyor, bilinen bir test işareti baştan sona yakalandı.

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma (Kanıtlı) | Fiilen Katkı Veren | Durum | Eksik Kanıt |
|---|---|---|---|---|---|
| **Modül A** | İlk breadboard ön ucunu kur. Girişi kısa devre ederek gürültü tabanını ölç. | Kaan malzeme envanterini teslim aldı (`W05_A_material-inventory_v01.md`), mekanik kuplaj taslağını çizdi (`W05_A_mechanical-design_v01.md`). 27 Ekim PR #35 ile teslim edildi. | Kaan | **PARTIAL** | **Fiziksel gürültü tabanı ve kısa devre ölçümü YAPILMADI (PENDING).** Fiziksel bench deneyi eksik. |
| **Modül B** | Geliştirme kartını çalıştır. Sentetik bir dalga biçimini bilgisayara akıt ve örnek kaybı olmadığını doğrula. | ESP32-S3 kartı teslim alındı. Ege tarafından firmware (G1 deterministik sentetik rampa) geliştirildi; 26 Ekim 2026'da fiziksel USB CDC üzerinden 480.000 örnek / 1875 çerçeve sıfır kayıpla aktarıldı (`PHYSICAL_G1_PASSED`). | Ege (kod, USB CDC, test), Ozan (hazırlık) | **PASS (G1)** | Modül B'nin bağımsız donanım ölçüm kayıtları (Ozan imzalı) bekleniyor. |
| **Modül C** | Canlı gösterimi ve kayıt işlevini kur. Modül B'den gelen sentetik akışla doğrula. | WebAudio + Canvas tabanlı canlı dalga biçimi ve Welch şelalesi kuruldu. Sentetik ve gerçek PCG akışları test edildi. 587 Python testi ve frontend testleri PASS verdi (`W05_C_live-display-recording-verification.md`). | Ege | **PASS** | Yok (yazılım ve USB CDC entegrasyonu tam kanıtlı). |

---

### Hafta 6 (27 Ekim – 2 Kasım 2026 — Devam Eden Hafta)

| Modül | Hocanın Beklediği Görev (Resmî Plan) | Yapılan Çalışma (Kanıtlı) | Fiilen Katkı Veren | Durum | Eksik Kanıt |
|---|---|---|---|---|---|
| **Modül A** | İlk dönüştürücüyü bağla. Fonksiyon üreteciyle kazancı ve bant genişliğini ölç. | Hafta 6 test kontrol listesi hazırlandı (`W05_A_week06-test-readiness_v01.md`, W6-A01..W6-A08). 30 Ekim Cuma laboratuvar deneyi planlandı. | Kaan | **PENDING** | **30 Ekim Cuma laboratuvar ölçümü bekleniyor.** Dönüştürücü kazanç/bant genişliği verisi henüz yok. |
| **Modül B** | Sentetik kaynağı gerçek çevirici girişiyle değiştir. Zaman damgası sürekliliğini doğrula. | I²S sürücüsü (`i2s_source.c`) yazıldı (48 kHz, 32-bit slot, Philips formatı, DMA). Yazılım simülasyon ve köprü testleri tamamlandı (`test_g1.py` 16/16 PASS). Gerçek INMP441 kaynağı (Source 0) firmware'de hazırlandı. | Ege (sürücü/yazılım) | **PARTIAL** | **Fiziksel INMP441 bağlantısı ve zaman damgası sürekliliği doğrulaması 30 Ekim Cuma deneyiyle yapılacak (PENDING).** |
| **Modül C** | Spektrogram görünümünü ve meta veri alanlarıyla kayıt kütüphanesini ekle. | Canlı Welch spektrogramı, 15 sn zaman ekseni, oturum sıfırlama, WAV+JSON kayıt ve SHA-256 bütünlüğü tamamlandı. WASAPI loopback ses testi ve masaüstü UX kararlılığı doğrulandı (`W06_C_spectrogram-recording-metadata.md`). | Ege | **PASS** | Yok (yazılım tam hazır; fiziksel mikrofon akışı bekleniyor). |

---

### 30 Ekim 2026 Cuma Fiziksel G2 Deneyi Öncesi Durum Özeti

1. **Yazılım & Ana Bilgisayar Altyapısı (Modül C + Firmware Sürücüsü):** %100 HAZIR. Tüm regresyon testleri, I²S dönüştürme rutinleri, USB aktarımı, kayıt motoru ve doğrulama araçları (`bringup.py qualify`) eksiksiz çalışmaktadır.
2. **Akustik ve Donanım Hazırlığı (Modül A):** Malzemeler teslim alınmış, mekanik planlar çizilmiştir; ancak fiziksel devre ölçümleri yapılmamıştır (Cuma laboratuvarda ölçülecek).
3. **Elektronik ve Gömülü Entegrasyon (Modül B):** G1 sentetik doğrulaması geçmiş, G2 I²S sürücüsü derlenmiş ve simülasyonda doğrulanmıştır; ancak fiziksel pin bağlantısı, 3.3V ray ölçümü ve ilk gerçek mikrofon akışı Cuma günkü kapı onaylarına bağlıdır.

> **Sonuç:** 1–5. haftaların teorik, şartname, simülasyon ve G1 USB CDC aktarım hedefleri tam başarıyla (**PASS**) tamamlanmıştır. Hafta 5 fiziksel gürültü ölçümü ile Hafta 6 fiziksel dönüştürücü entegrasyonu 30 Ekim 2026 Cuma laboratuvar seansında icra edilecek ve 2 Kasım resmî teslimine ölçüm kanıtlarıyla birlikte eklenecektir.
