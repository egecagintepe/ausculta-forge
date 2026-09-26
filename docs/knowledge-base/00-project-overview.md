# 00 — Proje Genel Bakışı ve Mühendislik Stratejisi

## Bu nedir?

**AuscultaForge**, kalp seslerini güvenilir bir biçimde sayısallaştırmayı, gerçek zamanlı olarak ana bilgisayara (Host PC) aktarmayı, filtrelemeyi ve spektral metriklerle analiz etmeyi hedefleyen (yüksek sadakatli akustik üretimin deneysel olarak doğrulanacak bir mühendislik hedefi olduğu) bir akıllı dijital fonokardiyogram (PCG) stetoskop geliştirme projesidir.

---

## AuscultaForge Neden Bunu Kullanıyor?

Geleneksel stetoskoplar kullanıcının anlık işitsel algısına bağımlıdır; sinyali kaydedemez, spektral bileşenlerini ayrıştıramaz ve objektif metrikler (RMS, tepe değeri, tepe faktörü) üretemez. AuscultaForge, akustik sesi sayısal sinyal bloklarına dönüştürerek tekrarlanabilir bir analiz ve görselleştirme ortamı sunar.

---

## Mevcut Kilometre Taşı (Current Milestone)

Projenin ilk ve en temel mühendislik hedefi:
$$\text{Fiziksel/akustik kaynak} \longrightarrow \text{Mikrofon/Dönüştürücü} \longrightarrow \text{MCU/Edinim Birimi} \longrightarrow \text{PC} \longrightarrow \text{Gerçek Zamanlı PCG Örnek Blokları}$$

Bu aşamada henüz grafik arayüz (GUI), makine öğrenmesi (AI), tanı koyma algoritmaları veya kablosuz bağlantı (Wi-Fi/BLE) sisteme dahil edilmemiştir. Öncelikle sinyal edinim hattının deterministik, kayıpsız ve sağlam çalıştığı kanıtlanmaktadır.

---

## Ekip Sorumluluk Alanları

| Mühendis | Alan | Temel Odak Noktaları |
|---|---|---|
| **Ozan** | Donanım Bileşen Seçimi, Şematik & PCB | Altium şematik/iskelet tasarımı, Native USB donanım hatları, yapılandırılabilir ~6-pin I2S mikrofon başlığı, LDO regülasyonu, PCB yerleşimi, dev-board entegrasyonu. |
| **Kaan** | Güç Mimarisi & Akustik Fantom Sistemi | MCP73831 + PFET + Schottky güç yolu referans tasarımı, akustik fantom test düzeneği, uyarıcı (exciter) / hoparlör mekanik kuplajı, referans PCG yürütme ve test prosedürü. |
| **Ege** | ESP32 Firmware, Taşıma Protokolü, PC DSP & Entegrasyon | ESP32-S3 firmware, I2S + DMA edinim, Native USB veri aktarımı, MCU-PC paket/protokol tasarımı, PC yazılım backend ve DSP, UI entegrasyonu, CRC doğrulama, repo yönetimi. |

---

## Donanımdan Bağımsız Geliştirme Stratejisi (Hardware-Independent Development)

### Neden bu tasarım seçildi?
Gömülü sistem projelerinde en sık karşılaşılan hata, PC yazılımının donanım prototipine doğrudan bağımlı geliştirilmesidir. Bu durumda PCB üretimi, sensör temini veya mikrodenetleyici kodundaki bir gecikme yazılım ekibini tamamen kilitler.

AuscultaForge şu prensiple tasarlanmıştır:
1. Donanım fiziksel bir `SampleBlock` üreticisi olarak kabul edilir.
2. PCG algoritmaları, filtreler, metrikler ve görselleştirme araçları `MockPCGSource` ve `RealtimeWavSource` ile donanım henüz masada yokken eksiksiz geliştirilir ve test edilir.
3. Donanım hazır olduğunda tek yapılması gereken, USB-UART veya seri porttan gelen baytları ayrıştırıp bir `SampleBlock` nesnesine sarmalayan küçük bir sürücü (`SerialSource`) yazmaktır. Downstream DSP hattının tek bir satırı dahi değişmez.

### Hangi problemleri önlüyor?
- **Erken donanım kilidi (Premature hardware lock-in):** Sensör seçimi (örn. INMP441, analog elektret veya piezoelektrik disk) değişse bile PC analiz çekirdeği etkilenmez.
- **Entegrasyon şoku:** Donanım ile yazılım ilk kez birleştiğinde algoritma hataları ile donanım hataları birbirine karışmaz; yazılım hattının önceden doğrulandığı bilinir.

---

## Geçici (Provisional) Varsayımlar

Takım kararlarıyla netleşen ve açıkta kalan mühendislik tercihleri:
- **Mikrodenetleyici:** ESP32-S3-WROOM olarak kesinleşti (Faz 1 kablolu Native USB). Wi-Fi ve BLE Faz 1 için kapsam dışıdır.
- **Arayüz & Mikrofon:** I2S MEMS mikrofonlar (INMP441 ve ICS-43434/43432 adayları) fantom testinde karşılaştırılacaktır. Özel PCB, mikrofon modelini kilitlememek için yapılandırılabilir ~6-pin başlık içerecektir.
- **Protokol:** Start, Sequence, Timestamp, Payload, Flags, CRC kavramsal alanları belirlendi; byte genişlikleri ve USB sınıfı Ege tarafından deneysel bench testleriyle kilitlenecektir.
- **Filtre Bandı:** 20–600 Hz bandı biyomedikal literatür başlangıç varsayımıdır; fantom doğrulama testleriyle optimize edilecektir.


---

## İlgili Dosyalar

- Sistem Mimarisi: [`docs/architecture/README.md`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/architecture/README.md)
- Firmware Kapsamı: [`firmware/README.md`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/firmware/README.md)
- Donanım Kapsamı: [`hardware/README.md`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/hardware/README.md)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"AuscultaForge'da donanım ve yazılım geliştirme süreçlerini birbirinden tamamen ayırdık. Sinyal işleme ve analiz hattımız `SampleBlock` soyutlaması üzerinde çalışır; bu sayede donanım prototipi henüz üretim aşamasındayken tüm DSP ve akış algoritmalarını hem sentetik mock verilerle hem de PhysioNet gibi açık klinik kayıtlarla eksiksiz doğruladık. Donanım bağlandığında yalnızca bir giriş sürücüsü eklenecek, çekirdek yazılım değişmeyecektir."*
