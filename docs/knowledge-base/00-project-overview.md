# 00 â€” Proje Genel BakÄ±ÅŸÄ± ve MÃ¼hendislik Stratejisi
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Bitirme Projesi (Platform / YazÄ±lÄ±m Kod AdÄ±: `AuscultaForge`)

---

## Bu nedir?

Bu proje, EEE495/EEE496 bitirme projesi kapsamÄ±nda geliÅŸtirilen **"Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment"** Ã§alÄ±ÅŸmasÄ±dÄ±r.

Temel mÃ¼hendislik hedefi; kalp seslerini (PCG) gÃ¶ÄŸÃ¼s parÃ§asÄ± ve mikrofon dÃ¶nÃ¼ÅŸtÃ¼rÃ¼cÃ¼ Ã¼zerinden gÃ¼venilir biÃ§imde edinmek, gÃ¶mÃ¼lÃ¼ mikrodenetleyici (ESP32-S3) ile 48 kHz hÄ±zÄ±nda sayÄ±sallaÅŸtÄ±rÄ±p USB Ã¼zerinden ana bilgisayara (Host PC) kayÄ±psÄ±z aktarmak, sayÄ±sal bant geÃ§iren filtreleme uygulamak ve tekrarlanabilir akustik fantom testleriyle sistemin frekans cevabÄ±nÄ±, gÃ¼rÃ¼ltÃ¼ tabanÄ±nÄ± ve sinyal kalitesini karakterize etmektir.

Platformun ve yazÄ±lÄ±m omurgasÄ±nÄ±n dahili kod adÄ± **AuscultaForge**'dur.

---

## Neden Bu Mimari SeÃ§ildi?

Geleneksel akustik stetoskoplar kullanÄ±cÄ±nÄ±n anlÄ±k iÅŸitsel algÄ±sÄ±na baÄŸÄ±mlÄ±dÄ±r; sinyali kaydedemez, spektral bileÅŸenlerini ayrÄ±ÅŸtÄ±ramaz ve objektif metrikler (RMS, tepe deÄŸeri, tepe faktÃ¶rÃ¼, frekans cevabÄ±) Ã¼retemez. Sistemimiz, akustik titreÅŸimi sayÄ±sal sinyal bloklarÄ±na (`SampleBlock`) dÃ¶nÃ¼ÅŸtÃ¼rerek tekrarlanabilir bir analiz ve laboratuvar doÄŸrulama ortamÄ± sunar.

---

## Mevcut Kilometre TaÅŸÄ± (Current Milestone)

Projenin temel sinyal edinim omurgasÄ±:
$$\text{Fiziksel/akustik kaynak} \longrightarrow \text{Mikrofon/DÃ¶nÃ¼ÅŸtÃ¼rÃ¼cÃ¼} \longrightarrow \text{MCU/Edinim Birimi} \longrightarrow \text{PC} \longrightarrow \text{GerÃ§ek ZamanlÄ± PCG Ã–rnek BloklarÄ±}$$

Sistem bir medikal tanÄ± cihazÄ± deÄŸil, mÃ¼hendislik araÅŸtÄ±rma ve karakterizasyon platformudur. Ä°nsan deneyi iÃ§ermez; tÃ¼m akustik Ã¶lÃ§Ã¼mler laboratuvar fantomu Ã¼zerinde yÃ¼rÃ¼tÃ¼lÃ¼r.

---

## Ekip ModÃ¼l SorumluluklarÄ±

Danışman yönergelerine göre üç kişilik bir ekipte her modülün (Modül A, B, C) bireysel değerlendirme, Git katkı geçmişi ve sözlü savunma için bir birincil öğrenci sorumlusu bulunur. Aşağıdaki tablo mevcut ekip çalışma dağılımını (danışman onayına tabi) yansıtmaktadır:

| Modül | Kapsam | Ekip Çalışma Dağılımı (Danışman Onayına Tabi) | Temel Odak Noktaları |
|---|---|---|---|
| **ModÃ¼l A** | Edinim DonanÄ±mÄ± & Karakterizasyon | **Kaan** | Mikrofon/dÃ¶nÃ¼ÅŸtÃ¼rÃ¼cÃ¼ seÃ§imi (Elektret vs MEMS), gÃ¶ÄŸÃ¼s parÃ§asÄ± akustik kuplajÄ±, analog Ã¶n yÃ¼z, akustik fantom test dÃ¼zeneÄŸi (uyarÄ±cÄ±/hoparlÃ¶r mekanik kuplajÄ±, silikon katman, rijit iskelet) ve fiziksel karakterizasyon testleri. |
| **ModÃ¼l B** | GÃ¶mÃ¼lÃ¼ Edinim & Veri Yolu | **Ozan** | Mikrodenetleyici (ESP32-S3) donanÄ±m entegrasyonu, I2S/ADC edinimi, DMA Ã§ift tamponlama, monotonik Ã¶rnek sÃ¼reklilik sayacÄ±, Native USB veri aktarÄ±mÄ±, telemetri bayraklarÄ± ve yerel TÃ¼rkiye komponent temini (BOM). |
| **ModÃ¼l C** | Bilgisayar UygulamasÄ± & Kalite DeÄŸerlendirmesi | **Ege** | Host PC masaÃ¼stÃ¼ uygulamasÄ± (React/TypeScript), yerel FastAPI kÃ¶prÃ¼ servisi, durumsal DSP filtreleme, JSON yan metadata ile oturum kaydÄ±, sinyal kalite telemetrisi ve otomatik test paketi. |

*Ekip Ã¼yeleri entegrasyon safhalarÄ±nda birbirlerine destek verir; ancak her modÃ¼lÃ¼n bireysel savunmadan sorumlu tek bir birincil sahibi vardÄ±r.*

---

## DonanÄ±mdan BaÄŸÄ±msÄ±z GeliÅŸtirme Stratejisi (Hardware-Independent Development)

### Neden bu tasarÄ±m seÃ§ildi?
GÃ¶mÃ¼lÃ¼ sistem projelerinde en sÄ±k karÅŸÄ±laÅŸÄ±lan hata, PC yazÄ±lÄ±mÄ±nÄ±n donanÄ±m prototipine doÄŸrudan baÄŸÄ±mlÄ± geliÅŸtirilmesidir. Bu durumda PCB Ã¼retimi, sensÃ¶r temini veya mikrodenetleyici kodundaki bir gecikme yazÄ±lÄ±m ekibini tamamen kilitler.

AuscultaForge ÅŸu prensiple tasarlanmÄ±ÅŸtÄ±r:
1. DonanÄ±m fiziksel bir `SampleBlock` Ã¼reticisi olarak kabul edilir.
2. PCG algoritmalarÄ±, filtreler, metrikler ve gÃ¶rselleÅŸtirme araÃ§larÄ± `MockPCGSource` ve `RealtimeWavSource` ile donanÄ±m henÃ¼z masada yokken eksiksiz geliÅŸtirilir ve test edilir.
3. DonanÄ±m hazÄ±r olduÄŸunda tek yapÄ±lmasÄ± gereken, USB portundan gelen baytlarÄ± ayrÄ±ÅŸtÄ±rÄ±p bir `SampleBlock` nesnesine sarmalayan kÃ¼Ã§Ã¼k bir sÃ¼rÃ¼cÃ¼ yazmaktÄ±r. Downstream DSP hattÄ±nÄ±n tek bir satÄ±rÄ± dahi deÄŸiÅŸmez.

### Hangi problemleri Ã¶nlÃ¼yor?
- **Erken donanÄ±m kilidi (Premature hardware lock-in):** SensÃ¶r seÃ§imi (analog elektret veya dijital MEMS) deÄŸiÅŸse bile PC analiz Ã§ekirdeÄŸi etkilenmez.
- **Entegrasyon ÅŸoku:** DonanÄ±m ile yazÄ±lÄ±m ilk kez birleÅŸtiÄŸinde algoritma hatalarÄ± ile donanÄ±m hatalarÄ± birbirine karÄ±ÅŸmaz; yazÄ±lÄ±m hattÄ±nÄ±n Ã¶nceden doÄŸrulandÄ±ÄŸÄ± bilinir.

---

## Kararlar ve AÃ§Ä±k TasarÄ±m Maddeleri

- **Mikrodenetleyici:** ESP32-S3 olarak kesinleÅŸti (kablolu Native USB). Wi-Fi ve BLE Faz 1 iÃ§in kapsam dÄ±ÅŸÄ±dÄ±r.
- **TransdÃ¼ser DeÄŸerlendirmesi:** Elektret kondansatÃ¶r mikrofon ve I2S MEMS mikrofonlar akustik fantom Ã¼zerinde Week 3â€“5 arasÄ±nda deneysel olarak karÅŸÄ±laÅŸtÄ±rÄ±lacaktÄ±r.
- **Protokol:** Monotonik sÃ¼reklilik sayacÄ±, zaman damgasÄ±, ham Ã¶rnek yÃ¼kÃ¼, hata bayraklarÄ± ve CRC gereksinimleri belirlendi; tel seviyesi paket formatÄ± Week 3'te netleÅŸtirilecektir.
- **Filtreleme:** 20â€“500 Hz bant geÃ§iren filtreleme nominal PCG aralÄ±ÄŸÄ±dÄ±r.

---

## Ä°lgili DokÃ¼manlar

- Sistem Mimarisi: [`docs/architecture/README.md`](../architecture/README.md)
- Hafta 2 Planlama Paketi: [`docs/sdp/week-02/`](../sdp/week-02/)
- Protokol TaslaÄŸÄ±: [`docs/protocol/PROTOCOL_DRAFT.md`](../protocol/PROTOCOL_DRAFT.md)
- Firmware KapsamÄ±: [`firmware/README.md`](../../firmware/README.md)
- DonanÄ±m KapsamÄ±: [`hardware/README.md`](../../hardware/README.md)
