# 00 — Proje Genel Bakışı ve Mühendislik Stratejisi

## Bu nedir?

**AuscultaForge**, kalp seslerini güvenilir bir biçimde sayısallaştırmayı, gerçek zamanlı olarak ana bilgisayara (Host PC) aktarmayı, filtrelemeyi ve spektral metriklerle analiz etmeyi hedefleyen (yüksek sadakatli akustik üretimin deneysel olarak doğrulanacak bir mühendislik hedefi olduğu) bir akıllı dijital fonokardiyogram (PCG) stetoskop geliştirme projesidir.

---

## AuscultaForge Neden Bunu Kullanıyor?

Geleneksel stetoskoplar hekimin işitsel tecrübesine bağımlıdır; sinyali kaydedemez, spektral bileşenlerini ayrıştıramaz ve objektif metrikler (RMS, tepe değeri, tepe faktörü) üretemez. AuscultaForge, akustik sesi sayısal sinyal bloklarına dönüştürerek tekrarlanabilir bir analiz ve görselleştirme ortamı sunar.

---

## Mevcut Kilometre Taşı (Current Milestone)

Projenin ilk ve en temel mühendislik hedefi:
$$\text{Fiziksel/akustik kaynak} \longrightarrow \text{Mikrofon/Dönüştürücü} \longrightarrow \text{MCU/Edinim Birimi} \longrightarrow \text{PC} \longrightarrow \text{Gerçek Zamanlı PCG Örnek Blokları}$$

Bu aşamada henüz grafik arayüz (GUI), makine öğrenmesi (AI), tanı koyma algoritmaları veya kablosuz bağlantı (Wi-Fi/BLE) sisteme dahil edilmemiştir. Öncelikle sinyal edinim hattının deterministik, kayıpsız ve sağlam çalıştığı kanıtlanmaktadır.

---

## Ekip Sorumluluk Alanları

| Mühendis | Alan | Temel Odak Noktaları |
|---|---|---|
| **Ozan** | Akustik & Mekanik Edinim, Fiziksel Prototip | Göğüs parçası akustik kuplajı, diyafram/çan tasarımı, akustik oda geometrisi, mekanik gürültü izolasyonu, 3D ergonomik gövde. |
| **Kaan** | Gömülü Elektronik, MCU, Firmware & PCB | Sensör/mikrofon arayüzü (I2S veya analog ADC), MCU donanım seçimi (aday: ESP32 ailesi), DMA tamponlama, seri haberleşme sürücüsü, şematik ve PCB çizimi. |
| **Ege** | Sistem Mimarisi, PC Yazılımı, DSP & Entegrasyon | Katmanlı yazılım mimarisi, PCG akış ve sinyal işleme hattı (DSP), metrikler, spektral analiz, kalite izleme, test otomasyonu ve entegrasyon. |

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

Aşağıdaki unsurlar şu an için **aday/geçici (provisional)** mühendislik tercihleridir ve kesinleştirilmemiştir:
- **Mikrodenetleyici:** ESP32-S3 güçlü bir adaydır ancak değerlendirme sürecindedir.
- **Arayüz:** I2S dijital mikrofon veya harici ADC/analog katman seçimi sensör prototip testlerine bağlıdır.
- **Filtre Bandı:** 20–600 Hz bandı biyomedikal literatür başlangıç varsayımıdır; akustik gövde frekans cevabı ve danışman hekim geri bildirimleriyle revize edilecektir.

---

## İlgili Dosyalar

- Sistem Mimarisi: [`docs/architecture/README.md`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/architecture/README.md)
- Firmware Kapsamı: [`firmware/README.md`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/firmware/README.md)
- Donanım Kapsamı: [`hardware/README.md`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/hardware/README.md)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"AuscultaForge'da donanım ve yazılım geliştirme süreçlerini birbirinden tamamen ayırdık. Sinyal işleme ve analiz hattımız `SampleBlock` soyutlaması üzerinde çalışır; bu sayede donanım prototipi henüz üretim aşamasındayken tüm DSP ve akış algoritmalarını hem sentetik mock verilerle hem de PhysioNet gibi açık klinik kayıtlarla eksiksiz doğruladık. Donanım bağlandığında yalnızca bir giriş sürücüsü eklenecek, çekirdek yazılım değişmeyecektir."*
