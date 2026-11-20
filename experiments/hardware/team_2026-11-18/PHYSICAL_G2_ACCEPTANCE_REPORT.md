# AuscultaForge — 18 Kasım 2026 Fiziksel G2 Donanım Kabul Raporu

**Tarih:** 18 Kasım 2026  
**Değerlendirilen Donanım:** ESP32-S3-WROOM-1 (N16R8, QFN56 v0.2) + INMP441 MEMS Mikrofon  
**Operatörler:** Kaan (Mekanik & Akustik Montaj), Ozan (Elektronik Ölçüm & Laboratuvar Entegrasyonu)  
**Yazılım & Firmware Mimarı:** Ege Çağın Tepe (ESP-IDF Firmware, USB CDC Protokolü, Sinyal Kalite Boru Hattı, Host Entegrasyonu)  
**Genel Kabul Kararı:** **ŞARTLI KABUL (CONDITIONAL PASS)**  
- **Fiziksel I²S Veri İletimi:** **KABUL (PASS)** — USB CDC üzerinden 48 kHz / 24-bit I²S veri aktarımı 0 akış-içi kayıp ile doğrulandı.
- **G1 Firmware Çift-Mod / Geri Dönüş Güvenliği:** **KABUL (PASS)** — Flash öncesi ve sonrası G1 sentetik rampa doğrulaması eksiksiz geçti.
- **Akustik Kalibrasyon & Klinik Doğrulama:** **BEKLEMEDE (PENDING)** — Fonksiyonel ses tepkisi kanıtlandı (23,2 dB SNR); mutlak dB SPL kalibrasyonu, fantom frekans cevabı ve klinik PCG teşhis uygunluğu henüz tamamlanmadı.

---

## 1. Yönetici Özeti ve Karar Gerekçesi

18 Kasım 2026 tarihinde laboratuvarda gerçekleştirilen fiziksel entegrasyon çalışmasında, ESP32-S3 mikrokontrolcüsü ile INMP441 omnidirectional MEMS mikrofonu breadboard üzerinde birleştirilmiş, `g2_candidate_20261117` firmware sürümü karta yüklenmiş ve USB CDC üzerinden host bilgisayara canlı veri aktarımı gerçekleştirilmiştir.

Teslim edilen bağımsız kanıt paketi (`AuscultaForge_Lab_Return_Kaan_Ozan_20261118_093859Z.zip` ve `100114Z.zip`) üzerinde yapılan deterministik inceleme sonucunda:
1. Donanım seviyesinde I²S saat (SCK/GPIO4), kelime seçimi (WS/GPIO5) ve veri hattı (SD/GPIO6) üzerinden 48 kHz, 24-bit ses verisi başarıyla yakalanmış ve USB CDC paketleri halinde host'a aktarılmıştır.
2. Tüm 10 saniyelik test oturumlarında (480.000 örnek / 1.875 blok) **akış-içi örnek kaybı sıfırdır (`in_stream_dropped_samples=0`)**, dizi sıra numarası süreksizliği ve zaman damgası anomalisi saptanmamıştır.
3. Sessiz ortam kaydı ile yapay ses uyaranı kaydı arasında 20–500 Hz kalp sesi bandında **23,2 dB güç oranı** ölçülerek mikrofonun fiziksel akustik uyarana tepki verdiği doğrulanmıştır.
4. G2 firmware'i karta yüklendikten sonra dahi G1 sentetik doğrulama modunun sorunsuz çalıştığı test edilerek geriye dönük uyumluluk ve rollback güvenliği kanıtlanmıştır.

Bu teknik bulgular doğrultusunda, **G2 Fiziksel I²S Veri Yakalama** aşaması mühendislik açısından şartlı kabul edilmiştir.

---

## 2. Donanım ve Laboratuvar Kurulumu

### 2.1 Cihaz Kimliği ve Çip Özellikleri
- **Mikrokontrolcü:** ESP32-S3 (QFN56) (revision v0.2), Dual Core 240 MHz, 8 MB Embedded PSRAM (AP_3v3), 16 MB Flash.
- **MAC Adresi:** `7c:e8:b1:aa:7c:c4`
- **Cihaz UID:** Low `0xb1aa7cc4`
- **USB VID:PID:** `303A:4001` (Espressif USB CDC)
- **Port Dağılımı:**
  - `COM3`: Native USB CDC (Canlı telemetri, HELLO el sıkışması ve ses akışı)
  - `COM4`: USB-Serial/JTAG (Firmware flash ve ROM bootloader)

### 2.2 INMP441 Pin Bağlantıları
Fiziksel breadboard üzerinde uygulanan ve doğrulaması yapılan pin eşleşmesi:

| Sinyal | INMP441 Pini | ESP32-S3 Pini | Fonksiyon / Durum |
| :--- | :--- | :--- | :--- |
| **BCLK** | SCK | **GPIO 4** | I²S Seri Bit Saati |
| **LRCLK**| WS  | **GPIO 5** | I²S Kelime Seçimi (Word Select) |
| **SD**   | SD  | **GPIO 6** | I²S Seri Veri Çıkışı |
| **L/R**  | L/R | **GND** | Sol Kanal Seçimi (Left Channel) |
| **VDD**  | VDD | **3.3V Rail** | 3,3 V Besleme Hattı (Ölçülen: 3,28 V) |
| **GND**  | GND | **GND Rail** | Ortak Toprak Hattı |

### 2.3 Görsel ve Mekanik Kanıtlar
Laboratuvar operasyonuna ait fotoğraflar incelenmiştir:
1. `lab_photo_esp32_top.jpg` (SHA256: `BD5E0C4A...`): ESP32-S3 modülü breadboard üzerine yerleştirilmiş, kırmızı durum LED'i aktif, yerel USB portu üzerinden USB-C kablosu takılı.
2. `lab_photo_inmp441_esp32_wiring_top.jpg` (SHA256: `408B16B6...`): Dairesel INMP441 breakout kartının breadboard üzerindeki konumu ve VDD, GND, SD, L/R, WS, SCK pinlerinden ESP32-S3'e giden jumper bağlantıları net biçimde görülmektedir.
3. `lab_photo_breadboard_angle.jpg` (SHA256: `AEBE1C8B...`): Sistemin açılı perspektiften breadboard rayları ve kablolama düzenini göstermektedir.

> [!NOTE]
> **Belgelendirme Sınırı (Açık Madde):** Mevcut fotoğraflar üst ve açılı kablolama düzenini doğrulamaktadır; ancak INMP441'in alt yüzündeki akustik ses giriş deliğinin (acoustic port) yakın çekim makro fotoğrafı ile multimetre ekranının anlık fotoğrafı çekilmemiştir. Bu durum aşağıda açık risk olarak kayıt altına alınmıştır.

---

## 3. Elektriksel Ölçümler ve Besleme Güvenliği

- **Ölçü Aleti:** Agilent U1232A Dijital Multimetre
- **Ölçülen VDD Gerilimi:** **3,28 V**
- **Nominal Aralık:** 3,0 V – 3,6 V (INMP441 veri sayfası sınırları: 1,62 V – 3,63 V)
- **Tolerans Sapması:** $\Delta = -0,02\text{ V}$ (%-0,61 nominal sapma, güvenli çalışma bölgesinde).
- **Süreklilik ve Kısa Devre Denetimi:** VDD-GND ve komşu GPIO hatları arasında flash öncesinde direnç ve süreklilik ölçümü yapılmış, kısa devre saptanmamıştır.
- **Dayanak Durumu:** 3,28 V değeri `g2_physical_attestation.json` dosyasında operatörler Kaan ve Ozan'ın yazılı beyanı olarak mevcuttur; multimetre ekran görüntüsü bulunmamaktadır.

---

## 4. Deterministik G1 Rollback ve Çift-Mod Güvenliği

G2 firmware'inin yüklenmesi öncesinde ve sonrasında G1 sentetik referans akışı çalıştırılarak firmware'in stabilitesi test edilmiştir:

1. **Flash Öncesi G1 Testi (`20261118T090212Z_5e7113d0`):**
   - Sonuç: `PHYSICAL_G1_PASSED`
   - Örnekleme: 48.000 Hz, 480.000 örnek (tam 10,0 s), 1.875 blok
   - Hata: 0 sıra hatası, 0 değer atlaması, 0 paket kaybı.
2. **Flash Sonrası G1 Doğrulaması (`20261118T091801Z_750cfd3e`):**
   - Sonuç: `PHYSICAL_G1_PASSED`
   - Örnekleme: 48.000 Hz, 480.000 örnek (tam 10,0 s), 1.875 blok
   - Hata: 0 sıra hatası, 0 değer atlaması, 0 paket kaybı.

Bu sonuç, yeni firmware sürümünün ESP32-S3 üzerinde G1 referans modunu bozmadığını, host tarafındaki doğrulama protokolünün eksiksiz çalıştığını ve donanımın geriye dönük uyumluluğunu kanıtlamaktadır.

---

## 5. G2 Fiziksel I²S Oturumları ve Akustik İnceleme

### 5.1 Oturum Metrikleri Karşılaştırma Tablosu

| Oturum ID | Tür / Senaryo | Tepe Genlik (Peak FS) | Tam Oturum RMS | Kararlı RMS (1–5 s) | Yakın-Kırpılma (>0.98 FS) | Doyum (>=0.9999 FS) | Akış-İçi Kayıp |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `091909_9e6baa63` | Sessiz Ortam (Quiet) | 0,6375 | 0,0828 | 0,0156 | %0,0000 (0 örnek) | %0,0000 | 0 |
| `093225_19cde788` | Akustik Uyaran (Stimulus 1) | 0,999982 | 0,2397 | 0,2224 | %0,2775 (1.332 örnek) | %0,0013 (6 örnek) | 0 |
| `094939_4888e670` | Akustik Uyaran (Stimulus 2) | 0,9978 | 0,0143 | 0,0219 | %0,0006 (3 örnek) | %0,0000 | 0 |
| `100102_4e58ac08` | Akustik Uyaran (Stimulus 3) | 0,999967 | 0,1053 | 0,0209 | %0,0575 (276 örnek) | %0,0002 (1 örnek) | 0 |

### 5.2 Sessiz Kayıtta Başlangıç Geçici Sinyali (Startup Transient) Analizi
Sessiz kayıtta (`session_20261118_091909_9e6baa63`), 10 saniyelik toplam RMS 0,0828 iken, ilk 100 ms'lik dilimde RMS **0,4982** olarak hesaplanmıştır.
- **Kök Neden:** I²S çevre biriminin ilk başlatılması sırasında DMA FIFO tamponunun dolması, donanımsal DC bloke edici yüksek geçiren filtrenin şarj olma süresi ve analog ön ucun çalışma noktasına oturmasıdır.
- **Sonuç:** Sinyal 1. saniyeden itibaren kararlı taban gürültü seviyesi olan **0,0156 RMS** değerine inmektedir. Raporlarda tüm oturum RMS'i yerine **kararlı durum RMS'i (steady RMS)** esas alınmalıdır.

### 5.3 Akustik Uyaran ve Kırpılma (Clipping vs Saturation) Analizi
Uyaran kaydında (`session_20261118_093225_19cde788`), tepe değer **0,999982 FS** seviyesine ulaşmıştır.
- Laboratuvar kalite aracında `clipping_detected=true` bayrağı verilmiş, ancak `saturation_fraction=0.0` çıkmıştır.
- **Farkın Nedeni:** `saturation_fraction` metriği yalnızca örneklerin kesin olarak tepeye yapıştığı (`|x| >= 0.9999`) durumları ölçerken, `clipping_detected` eşiği `|x| > 0.98` olan tepeye yakın bölgedeki örnekleri (%0,2775 / 1.332 örnek) tespit etmiştir.
- **Mühendislik Yorumu:** Akustik hoparlörden verilen test tonu seviyesi mikrofona çok yakın tutulmuş ve INMP441'in dinamik aralığının sınırına dayanılmıştır. Bu durum dijital bir bozulma veya yazılım hatası değil, aşırı akustik ses basıncı uyarımıdır. Sonraki deneylerde hoparlör ses seviyesinin düşürülmesi veya mesafenin artırılması gerekmektedir.

### 5.4 Spektral Güç Oranı (23,2 dB ve 8,0 dB Ayrımı)
- **Uyaran Oturumu 1 (`093225_19cde788`):** Yüksek hoparlör ses şiddeti altında 20–500 Hz bandında sessiz oturuma kıyasla **23,2 dB güç oranı** ölçülmüştür (%0,2775 tepe-yakın kırpılma, bağımsız 4. derece Butterworth filtresiyle ~24,7 dB).
- **Uyaran Oturumu 3 (`100102_4e58ac08`):** İkinci laboratuvar teslim paketinde (`100114Z.zip`) yer alan bu oturumda, ses şiddetinin düşürülmesi veya uyarım mesafesinin değişmesi sonucunda 20–500 Hz güç oranı **8,0 dB** olarak hesaplanmıştır (%0,0575 tepe-yakın kırpılma).
- **Mühendislik Sonucu:** 23,2 dB ve 8,0 dB değerleri **farklı iki fiziksel uyaran oturumuna** aittir. Her iki ölçüm de sistemin uyarana tepki verdiğini doğrulamakta, ancak uyaran seviyesine bağlı olarak dinamik aralığın değiştiğini göstermektedir. Bu veriler birbirinin üzerine yazılmadan ayrı kanıtlar olarak korunmuştur ([`wednesday_g2_comparison.md`](wednesday_g2_comparison.md) ve [`wednesday_g2_comparison_run3_8db.md`](wednesday_g2_comparison_run3_8db.md)).

### 5.5 Ham WAV SHA-256 Özet Düzeltmesi (REV04 Denetimi)
İkinci teslim paketi (`AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`) bağımsız SHA-256 denetiminden geçirilmiş ve 148/148 dosya bütünlüğü doğrulanmıştır. Yapılan incelemede, GitHub özet tablosunda (`RETURN_EVIDENCE_SUMMARY.json`) son iki oturumun WAV hash değerlerinde kopyalama hatası saptanmış ve kanıt dosyalarıyla eşitlenerek düzeltilmiştir:
- `session_20261118_091909_9e6baa63/raw.wav`: `eb4f218c3a22158430993b2180cc28618b5e426d7588b1d3da1ca59fcdf3d903` (Doğrulandı)
- `session_20261118_093225_19cde788/raw.wav`: `76698e92fea31bed8ec27836e8f04e66d20639c79dbcf665df90f4ea09b7c5d9` (Doğrulandı)
- `session_20261118_094939_4888e670/raw.wav`: `733de8fdd1f722a7a6be9e17d354261561da53852d9aa5a6c691cd9503c3c857` (Düzeltildi; eski hatalı özet: `6662e7...`)
- `session_20261118_100102_4e58ac08/raw.wav`: `26c78582df26bcd209c1f051f09aca19c8462b9fc7067cd30a0a59eba57faa33` (Düzeltildi; eski hatalı özet: `1381dc...`)

---

## 6. Firmware Telemetri ve Örnek Sayımı Açıklaması

Firmware loglarında iki oturumda da şu telemetri değerleri üretilmiştir:
```json
{
  "generated_samples": 480256,
  "fully_queued_samples": 480000,
  "dropped_samples": 256,
  "post_target_drained_samples": 256,
  "in_stream_dropped_samples": 0
}
```

> [!IMPORTANT]
> **256 Örnek Drenajı Hakkında Teknik Açıklama:**
> Firmware I²S DMA tampon blok boyutu **256 örnektir**. Host tarafından talep edilen hedef örnek sayısı (480.000 örnek = 1.875 blok × 256) tamamlandığında STOP komutu işlenir. Bu sırada DMA donanımının doldurmuş olduğu son 1 blok (256 örnek) akış tamamlandığı için tahliye edilmiştir (`post_target_drained_samples = 256`).
> **Aktif veri aktarımı sırasında hiçbir örnek kaybolmamıştır (`in_stream_dropped_samples = 0`).** Bu durum bir veri kaybı hatası değil, blok tabanlı DMA sonlandırma davranışıdır.

---

## 7. Kaynak Commit ve Sürüm İzlenebilirliği

- **Laboratuvar Çalıştırma Ortamı:** `319fcc59b85c13e4334354f5950a7c41eb4ea87f` commit'i tabanlı dizin üzerinden çalıştırılmıştır.
- **Karta Yüklenen Firmware:** `firmware/releases/g2_candidate_20261117/` dizinindeki önceden derlenmiş binary paketidir.
- **Hash Doğrulaması:** Flash logunda (`first-flash.txt`) yer alan `bootloader.bin` (`28e9a0...`), `auscultaforge_g1.bin` (`22af47...`) ve `partition-table.bin` (`73c0b5...`) SHA-256 değerleri, depodaki resmi release manifestosu ile birebir uyuşmaktadır.

---

## 8. Sorumluluk ve Katkı Matrisi

Fiziksel entegrasyon çalışmasındaki katkı dağılımı aşağıdaki gibidir:
- **Ege Çağın Tepe:** ESP32-S3 I²S ve USB CDC firmware geliştirmesi, çift-mod mimarisi, host veri toplama CLI/uygulaması, test protokolleri, sinyal analiz boru hatları ve geriye dönük uyumluluk doğrulaması.
- **Kaan:** INMP441 mikrofonunun breadboard üzerine montajı, kablolama güzergahı, akustik uyarım kaynağının fiziksel konumlandırılması ve transdüser mekanik yerleşimi.
- **Ozan:** Besleme geriliminin multimetre ile ölçümü (3,28 V), pin süreklilik ve elektriksel güvenlik kontrolleri, laboratuvar test betiklerinin sahada koşturulması ve veri paketinin arşivlenmesi.

---

## 9. Açık Kalan Riskler ve Sonraki Adımlar

| Madde | Durum | Gerekli Eylem |
| :--- | :--- | :--- |
| **Multimetre Ekran Fotoğrafı** | EKSİK | Gelecek ölçümlerde multimetre ekranı tarih ve kartla birlikte fotoğraflanacak. |
| **Akustik Port Makro Fotoğrafı** | EKSİK | INMP441 alt yüzündeki akustik delik ve lehimlerin yakın çekim fotoğrafı eklenecek. |
| **Akustik Kalibrasyon & dB SPL** | BEKLEMEDE | Kalibre edilmiş yapay akustik fantom ve ses seviyesi ölçer (SPL meter) ile frekans yanıt eğrisi çıkarılacak. |
| **Uyaran Ses Seviyesi Kontrolü** | DÜZELTİLECEK | Sonraki testlerde hoparlör gücü düşürülerek %0 kırpılma ile doğrusal bölgede ölçüm alınacak. |
| **Klinik Stetoskop Doğrulaması** | BEKLEMEDE | Gerçek göğüs parçası ve kardiyak dinleme testleri akademik takvimin ilerleyen aşamalarında planlanacak. |
