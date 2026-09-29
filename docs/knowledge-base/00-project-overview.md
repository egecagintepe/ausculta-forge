# 00 — Proje Genel Bakışı ve Mühendislik Stratejisi
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Bitirme Projesi (Platform / Yazılım Kod Adı: `AuscultaForge`)

---

## Bu nedir?

Bu proje, EEE495/EEE496 bitirme projesi kapsamında geliştirilen **"Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment"** çalışmasıdır.

Temel mühendislik hedefi; kalp seslerini (PCG) göğüs parçası ve mikrofon dönüştürücü üzerinden güvenilir biçimde edinmek, gömülü mikrodenetleyici (ESP32-S3) ile 48 kHz hızında sayısallaştırıp USB üzerinden ana bilgisayara (Host PC) kayıpsız aktarmak, sayısal bant geçiren filtreleme uygulamak ve tekrarlanabilir akustik fantom testleriyle sistemin frekans cevabını, gürültü tabanını ve sinyal kalitesini karakterize etmektir.

Platformun ve yazılım omurgasının dahili kod adı **AuscultaForge**'dur.

---

## Neden Bu Mimari Seçildi?

Geleneksel akustik stetoskoplar kullanıcının anlık işitsel algısına bağımlıdır; sinyali kaydedemez, spektral bileşenlerini ayrıştıramaz ve objektif metrikler (RMS, tepe değeri, tepe faktörü, frekans cevabı) üretemez. Sistemimiz, akustik titreşimi sayısal sinyal bloklarına (`SampleBlock`) dönüştürerek tekrarlanabilir bir analiz ve laboratuvar doğrulama ortamı sunar.

---

## Mevcut Kilometre Taşı (Current Milestone)

Projenin temel sinyal edinim omurgası:
$$\text{Fiziksel/akustik kaynak} \longrightarrow \text{Mikrofon/Dönüştürücü} \longrightarrow \text{MCU/Edinim Birimi} \longrightarrow \text{PC} \longrightarrow \text{Gerçek Zamanlı PCG Örnek Blokları}$$

Sistem bir medikal tanı cihazı değil, mühendislik araştırma ve karakterizasyon platformudur. İnsan deneyi içermez; tüm akustik ölçümler laboratuvar fantomu üzerinde yürütülür.

---

## Ekip Modül Sorumlulukları

Danışman yönergelerine göre üç kişilik bir ekipte her modülün (Modül A, B, C) bireysel değerlendirme, Git katkı geçmişi ve sözlü savunma için bir birincil öğrenci sorumlusu bulunur. Aşağıdaki tablo mevcut ekip çalışma dağılımını (danışman onayına tabi) yansıtmaktadır:

| Modül | Kapsam | Ekip Çalışma Dağılımı (Danışman Onayına Tabi) | Temel Odak Noktaları |
|---|---|---|---|
| **Modül A** | Edinim Donanımı & Karakterizasyon | **Kaan** | Mikrofon/dönüştürücü seçimi (Elektret vs MEMS), göğüs parçası akustik kuplajı, analog ön yüz, akustik fantom test düzeneği (uyarıcı/hoparlör mekanik kuplajı, silikon katman, rijit iskelet) ve fiziksel karakterizasyon testleri. |
| **Modül B** | Gömülü Edinim & Veri Yolu | **Ozan** | Mikrodenetleyici (ESP32-S3) donanım entegrasyonu, I2S/ADC edinimi, DMA çift tamponlama, monotonik örnek süreklilik sayacı, Native USB veri aktarımı, telemetri bayrakları ve yerel Türkiye komponent temini (BOM). |
| **Modül C** | Bilgisayar Uygulaması & Kalite Değerlendirmesi | **Ege** | Host PC masaüstü uygulaması (React/TypeScript), yerel FastAPI köprü servisi, durumsal DSP filtreleme, JSON yan metadata ile oturum kaydı, sinyal kalite telemetrisi ve otomatik test paketi. |

*Ekip üyeleri entegrasyon safhalarında birbirlerine destek verir; ancak her modülün bireysel savunmadan sorumlu tek bir birincil sahibi vardır.*

---

## Donanımdan Bağımsız Geliştirme Stratejisi (Hardware-Independent Development)

### Neden bu tasarım seçildi?
Gömülü sistem projelerinde en sık karşılaşılan hata, PC yazılımının donanım prototipine doğrudan bağımlı geliştirilmesidir. Bu durumda PCB üretimi, sensör temini veya mikrodenetleyici kodundaki bir gecikme yazılım ekibini tamamen kilitler.

AuscultaForge şu prensiple tasarlanmıştır:
1. Donanım fiziksel bir `SampleBlock` üreticisi olarak kabul edilir.
2. PCG algoritmaları, filtreler, metrikler ve görselleştirme araçları `MockPCGSource` ve `RealtimeWavSource` ile donanım henüz masada yokken eksiksiz geliştirilir ve test edilir.
3. Donanım hazır olduğunda tek yapılması gereken, USB portundan gelen baytları ayrıştırıp bir `SampleBlock` nesnesine sarmalayan küçük bir sürücü yazmaktır. Downstream DSP hattının tek bir satırı dahi değişmez.

### Hangi problemleri önlüyor?
- **Erken donanım kilidi (Premature hardware lock-in):** Sensör seçimi (analog elektret veya dijital MEMS) değişse bile PC analiz çekirdeği etkilenmez.
- **Entegrasyon şoku:** Donanım ile yazılım ilk kez birleştiğinde algoritma hataları ile donanım hataları birbirine karışmaz; yazılım hattının önceden doğrulandığı bilinir.

---

## Kararlar ve Açık Tasarım Maddeleri

- **Mikrodenetleyici:** ESP32-S3 olarak kesinleşti (kablolu Native USB). Wi-Fi ve BLE Faz 1 için kapsam dışıdır.
- **Transdüser Değerlendirmesi:** Elektret kondansatör mikrofon ve I2S MEMS mikrofonlar akustik fantom üzerinde Week 3–5 arasında deneysel olarak karşılaştırılacaktır.
- **Protokol:** Monotonik süreklilik sayacı, zaman damgası, ham örnek yükü, hata bayrakları ve CRC gereksinimleri belirlendi; tel seviyesi paket formatı Week 3'te netleştirilecektir.
- **Filtreleme:** 20–500 Hz bant geçiren filtreleme nominal PCG aralığıdır.

---

## İlgili Dokümanlar

- Sistem Mimarisi: [`docs/architecture/README.md`](../architecture/README.md)
- Hafta 2 Planlama Paketi: [`docs/sdp/week-02/`](../sdp/week-02/)
- Protokol Taslağı: [`docs/protocol/PROTOCOL_DRAFT.md`](../protocol/PROTOCOL_DRAFT.md)
- Firmware Kapsamı: [`firmware/README.md`](../../firmware/README.md)
- Donanım Kapsamı: [`hardware/README.md`](../../hardware/README.md)
