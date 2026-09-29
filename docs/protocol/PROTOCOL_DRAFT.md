# MCU ↔ PC İletişim Protokolü Taslağı
## Smart Digital Stethoscope (EEE495 / EEE496 Bitirme Projesi)
Platform / Yazılım Kod Adı: `AuscultaForge`

Bu belge nihai wire protokolü değildir. Protokol gereksinimleri Module B (Ozan) ve Module C (Ege) arasında ortak olarak belirlenmekte olup (ayrıntılar için bkz. [`docs/sdp/week-02/bc-interface-requirements.md`](../sdp/week-02/bc-interface-requirements.md)), paket formatı bench üzerinde deneysel olarak doğrulanmadan byte-level detaylar kilitlenmeyecektir.

---

## 1. Fiziksel Katman ve Taşıma Kararı

- **MCU Platformu:** ESP32-S3-WROOM (kesinleşti).
- **Taşıma Teknolojisi:** Kablolu Native USB (kesinleşti).
- **Kapsam Dışı:** Wi-Fi ve BLE Faz 1 için kapsam dışıdır.
- **USB Sınıfı & Uç Nokta (Endpoint):** Henüz kilitlenmemiştir (CDC-ACM sanal seri port veya Vendor Bulk transfer adayıdır; benchmarking ile seçilecektir).

---

## 2. Kavramsal Paket Alanları (Draft Packet Model)

PC yazılımının güvenilir sinyal akışı ve tanılama için ihtiyaç duyduğu kavramsal paket alanları:

| Alan | Amaç | Durum |
|---|---|---|
| **Start / Sync Word** | Paket başlangıç senkronizasyonu ve çerçeve hizalama | Kavramsal taslak |
| **Sequence Number** | Paket kaybı ve sıra bozulması tespiti | Kavramsal taslak |
| **Timestamp** | Zamanlama, jitter ve gecikme analizi | Kavramsal taslak |
| **Sample Payload** | Sayısallaştırılmış PCG ses örnekleri bloğu | Kavramsal taslak (~4 kHz, 16/24-bit aday) |
| **Status / Error Flags** | DMA taşması (overflow), donanım ve tampon durum bayrakları | Kavramsal taslak |
| **CRC** | İletim hattı veri bütünlüğü ve bozulma tespiti | Kavramsal taslak |

> **Önemli Kısıtlama:** Byte genişlikleri, endianness (byte sırası), paket boyutu, CRC polinomu, framing sınırlandırma karakterleri ve USB endpoint tipi henüz uydurulmamış/kilitlenmemiştir. Bu parametreler ilk dummy stream bench testlerinde Ege tarafından deneysel olarak belirlenecektir.

---

## 3. Temel Mimari Prensipler

1. **Katman İzolasyonu:** UI ve veri görselleştirme katmanı asla USB, seri port veya donanım sürücüsü kodunu doğrudan bilmez.
2. **`SampleBlock` Dönüşümü:** Donanımdan gelen her paket, PC tarafındaki sürücü katmanında doğrulanıp (CRC kontrolü yapılarak) doğrudan `SampleBlock` nesnesine dönüştürülür.
3. **DSP Değişmezliği:** Aynı filtreleme, spektral analiz ve metrik hesaplama kodu `MockPCGSource`, `RealtimeWavSource` ve gelecekteki `NativeUsbSource` üzerinde sıfır değişiklikle çalışır.
4. **Veri Bütünlüğü:** CRC hatası veya sıra numarası atlaması `StreamQualityMonitor` tarafından yakalanarak UI ve tanılama ekranına (Diagnostics Drawer) raporlanır.
