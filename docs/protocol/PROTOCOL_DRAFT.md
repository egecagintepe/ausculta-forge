# MCU â†” PC Ä°letiÅŸim ProtokolÃ¼ TaslaÄŸÄ±
## Smart Digital Stethoscope (EEE495 / EEE496 Bitirme Projesi)
Platform / YazÄ±lÄ±m Kod AdÄ±: `AuscultaForge`

Bu belge nihai wire protokolÃ¼ deÄŸildir. Protokol gereksinimleri Module B (Ozan) ve Module C (Ege) arasÄ±nda ortak olarak belirlenmekte olup (ayrÄ±ntÄ±lar iÃ§in bkz. [`docs/sdp/week-02/bc-interface-requirements.md`](../sdp/week-02/bc-interface-requirements.md)), paket formatÄ± bench Ã¼zerinde deneysel olarak doÄŸrulanmadan byte-level detaylar kilitlenmeyecektir.

---

## 1. Fiziksel Katman ve TaÅŸÄ±ma KararÄ±

- **MCU Platformu:** ESP32-S3-WROOM (kesinleÅŸti).
- **TaÅŸÄ±ma Teknolojisi:** Kablolu Native USB (kesinleÅŸti).
- **Kapsam DÄ±ÅŸÄ±:** Wi-Fi ve BLE Faz 1 iÃ§in kapsam dÄ±ÅŸÄ±dÄ±r.
- **USB SÄ±nÄ±fÄ± & UÃ§ Nokta (Endpoint):** HenÃ¼z kilitlenmemiÅŸtir (CDC-ACM sanal seri port veya Vendor Bulk transfer adayÄ±dÄ±r; benchmarking ile seÃ§ilecektir).

---

## 2. Kavramsal Paket AlanlarÄ± (Draft Packet Model)

PC yazÄ±lÄ±mÄ±nÄ±n gÃ¼venilir sinyal akÄ±ÅŸÄ± ve tanÄ±lama iÃ§in ihtiyaÃ§ duyduÄŸu kavramsal paket alanlarÄ±:

| Alan | AmaÃ§ | Durum |
|---|---|---|
| **Start / Sync Word** | Paket baÅŸlangÄ±Ã§ senkronizasyonu ve Ã§erÃ§eve hizalama | Kavramsal taslak |
| **Sequence Number** | Paket kaybÄ± ve sÄ±ra bozulmasÄ± tespiti | Kavramsal taslak |
| **Timestamp** | Zamanlama, jitter ve gecikme analizi | Kavramsal taslak |
| **Sample Payload** | SayÄ±sallaÅŸtÄ±rÄ±lmÄ±ÅŸ PCG ses Ã¶rnekleri bloÄŸu | Kavramsal taslak (~4 kHz, 16/24-bit aday) |
| **Status / Error Flags** | DMA taÅŸmasÄ± (overflow), donanÄ±m ve tampon durum bayraklarÄ± | Kavramsal taslak |
| **CRC** | Ä°letim hattÄ± veri bÃ¼tÃ¼nlÃ¼ÄŸÃ¼ ve bozulma tespiti | Kavramsal taslak |

> **Ã–nemli KÄ±sÄ±tlama:** Byte geniÅŸlikleri, endianness (byte sÄ±rasÄ±), paket boyutu, CRC polinomu, framing sÄ±nÄ±rlandÄ±rma karakterleri ve USB endpoint tipi henÃ¼z uydurulmamÄ±ÅŸ/kilitlenmemiÅŸtir. Bu parametreler ilk dummy stream bench testlerinde Ege tarafÄ±ndan deneysel olarak belirlenecektir.

---

## 3. Temel Mimari Prensipler

1. **Katman Ä°zolasyonu:** UI ve veri gÃ¶rselleÅŸtirme katmanÄ± asla USB, seri port veya donanÄ±m sÃ¼rÃ¼cÃ¼sÃ¼ kodunu doÄŸrudan bilmez.
2. **`SampleBlock` DÃ¶nÃ¼ÅŸÃ¼mÃ¼:** DonanÄ±mdan gelen her paket, PC tarafÄ±ndaki sÃ¼rÃ¼cÃ¼ katmanÄ±nda doÄŸrulanÄ±p (CRC kontrolÃ¼ yapÄ±larak) doÄŸrudan `SampleBlock` nesnesine dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lÃ¼r.
3. **DSP DeÄŸiÅŸmezliÄŸi:** AynÄ± filtreleme, spektral analiz ve metrik hesaplama kodu `MockPCGSource`, `RealtimeWavSource` ve gelecekteki `NativeUsbSource` Ã¼zerinde sÄ±fÄ±r deÄŸiÅŸiklikle Ã§alÄ±ÅŸÄ±r.
4. **Veri BÃ¼tÃ¼nlÃ¼ÄŸÃ¼:** CRC hatasÄ± veya sÄ±ra numarasÄ± atlamasÄ± `StreamQualityMonitor` tarafÄ±ndan yakalanarak UI ve tanÄ±lama ekranÄ±na (Diagnostics Drawer) raporlanÄ±r.
