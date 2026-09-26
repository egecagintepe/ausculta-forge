# 11 — Host İşlem Kapasitesi, Ekran Desimasyonu ve Geri Basınç İzolasyonu

## Bu nedir?

Bu doküman, AuscultaForge projesinde **Hardware Rev-A (48 kHz mono, 24-bit PCM, ~512 örnekli bloklar)** ediniminde ana bilgisayar yazılımının sürdürülebilir işlem mimarisini, görselleştirme katmanındaki **ekran desimasyonunu (peak-preserving decimation)** ve yavaş/donmuş istemcilere karşı uygulanan **geri basınç izolasyonunu (backpressure isolation)** açıklar.

Mimari temel kuralı şudur:
> **"Tam hızlı edinim (48 kHz), DSP filtreleme ve oturum kaydı (SessionRecorder), kullanıcı arayüzünün (UI) çizim hızından kesinlikle bağımsız olmak zorundadır. Yavaş veya takılan bir tarayıcı/WebSocket istemcisi, asla donanım edinim verisinin kayıttan atılmasına veya donanım paket kaybı (sequence gap) sayacının artmasına yol açamaz."**

---

## 1. Neden 48 kHz Acquisition = 48,000 UI Point/s Demek Değildir?

Fiziksel donanım, akustik kardiyak sinyali ve fısıltıları Nyquist kriterine ve donanım Rev-A I2S PUI DMM-4026-B-I2S-R mikrofon standardına göre **48.000 örnek/saniye** hızında sayısallaştırır. 512 örnekli paketler halinde aktarıldığında bu, ana bilgisayara saniyede **93,75 paket/saniye** (~10,67 ms blok süresi) gelmesi anlamına gelir.

Ancak bir ekranda dalga biçimi çizmek için saniyede 48.000 ayrı piksel/nokta göndermek:
1. **İnsan Gözünün Algı Sınırının Çok Ötesindedir:** Monitörler tipik olarak 60 Hz yenilenir. İnsan gözü 20–30 Hz üzerindeki dalga formu güncellemelerini akıcı bir hareket olarak algılar.
2. **Ekran Çözünürlüğüyle Uyumsuzdur:** Bir monitördeki dalga formu alanı genellikle 800–1200 piksel genişliğindedir. 5 saniyelik bir pencerede 240.000 örneği 1000 piksele çizmeye çalışmak, her piksel sütununa 240 noktanın üst üste binmesi demektir.
3. **Tarayıcı ve Ağ Yükü:** Saniyede 94 adet JSON WebSocket mesajı göndermek, tarayıcıda JSON parse ve React durum güncellemelerini boğar (render lag).

Bu nedenle **Edinim Hızı (Acquisition Cadence)** ile **Görselleştirme Hızı (Display Cadence)** birbirinden tamamen ayrılmıştır:
- **Edinim:** 48.000 Hz (kesintisiz, kayıpsız, tam çözünürlük)
- **Ekran Güncellemesi:** 20–30 Hz (varsayılan: 25 Hz, merkezi `DisplayPipelineConfig` ile yapılandırılabilir; tıbbi/klinik optimizasyon iddiası taşımayan mühendislik varsayılanı).

---

## 2. Mimari Akış ve Sorumluluk Ayrımı

```
48 kHz Fiziksel Donanım Edinimi
             ↓
     DeviceSamplePacket (~512 örnek / 10.67 ms)
             ↓
   StreamManager.ingest_device_packet()
             ↓
   Bütünlük Doğrulama (CRC, sıra, taşma kontrolü)
             ↓
    SampleBlock (48 kHz normalize float32)
             ↓
   ┌────────────────────────────────────────────────────────┐
   │ 1. FULL-RATE DSP (StreamingBandpass Filtresi)          │
   ├────────────────────────────────────────────────────────┤
   │ 2. FULL-RATE SessionRecorder (WAV Kaydı - %100 Örnek)   │
   └────────────────────────────────────────────────────────┘
             │
             └───────────────► DisplayAggregator (DisplayPipeline)
                                     ↓
                           Min/Max Tepe Koruyucu Desimasyon
                                     ↓
                           Sınırlı/En Son Değer Kuyruğu (Bounded Queue)
                                     ↓
                           Düşük Hızlı WebSocket UI (display_frame @ 25 Hz)
                                     ↓
                           React Desktop / LiveWorkspace
```

---

## 3. Min/Max Tepe Koruyucu Desimasyon (Peak-Preserving Decimation)

Ham 48 kHz sinyali ekrana basmak için doğrudan her $N$'inci örneği almak (naive subsampling, `samples[::N]`) **kabul edilemez bir hatadır**. Çünkü dar fizyolojik geçişler (S1/S2 kapak kapanma tıkları, ejeksiyon klikleri veya yüksek frekanslı üfürüm tepecikleri) örnekler arasına düşüp ekranda tamamen kaybolabilir.

AuscultaForge, `decimate_min_max` fonksiyonunu kullanır:
- Verilen zaman dilimi $K = M / 2$ eşit kovaya (bin/bucket) bölünür ($M$ hedef nokta sayısı, örn. 128 nokta).
- Her kova içerisindeki **minimum** ve **maksimum** değer bulunur.
- Bu iki tepe noktası, orijinal sinyalde oluştukları **kronolojik sıra korunarak** çıktı dizisine yazılır.
- Bu sayede kova içi yerel uç değerler (minimum ve maksimum) korunarak naive periyodik örneklemeye kıyasla tepe noktalarının görsel tespiti ve dalga formu zarfı çok daha başarılı korunur (fakat her sıfır geçişi veya tüm morfolojik detayların kusursuz korunması gibi matematiksel bir aşırı iddiada bulunulmaz).

---

## 4. Geri Basınç İzolasyonu (Backpressure Isolation) ve Bounded Queues

Çoklu istemcili bir ortamda veya tarayıcının sekme değiştirmesi/yoğun JavaScript işlemesi nedeniyle bir istemci yavaşlayabilir ya da soketi tıkanabilir.

### Uygulanan Çözüm (`ClientSession` Bounded Queue)
- Her WebSocket istemcisi için `asyncio.Queue(maxsize=2)` boyutunda sınırlı bir kuyruk ve bağımsız bir `_sender_loop` arka plan görevi tahsis edilir.
- `publish_display_frame` çağrıldığında, kuyruk doluysa **en eski ekran karesi atılır (drop-oldest)** ve yerine en güncel ekran karesi yazılır.
- İstemci başına `dropped_display_frames` ve genel `total_display_frames_dropped` telemetri sayaçları artırılır.
- Donanım edinim döngüsü (`ingest_device_packet`) **asla ağ G/Ç'sini beklemez (non-blocking)**; mikro-saniyeler içinde tamamlanır.

### Çoklu İstemci İzolasyonu
- Hızlı İstemci (Client A): Kuyruğu boş kalır, tüm ekran karelerini akıcı biçimde alır, drop = 0.
- Yavaş İstemci (Client B): Soketi bloklandığında sadece kendi kuyruğundaki eski ekran kareleri atılır; Client A'yı ve ana edinim boru hattını kesinlikle yavaşlatamaz.

---

## 5. Neden Eski Display Frame'i Atmak, Acquisition Sample Atmaktan Farklıdır?

Bu ayrım, stetoskop mimarisinin en kritik akademik/mühendislik savunma noktalarından biridir:

| Kavram | Acquisition Sample Loss (Donanım Kaybı) | Display Frame Drop (Ekran Karesi Atma) |
|---|---|---|
| **Konum** | ESP32-S3 ile PC arasındaki donanım/transport hattı | PC içi WebSocket ile React UI arasındaki sunum hattı |
| **Etki** | Sinyal sürekliliği bozulur; kayıt edilen WAV dosyasında delikler/klikler oluşur; DSP filtre durumunda sıçramalar meydana gelir. | Ses kaydı %100 eksiksiz korunur; DSP kesintisiz tam hızda sürer; yalnızca ekranda gösterilecek geçici bir piksel karesi atlanmış olur. |
| **Metrik Sayacı** | `DeviceIntegrityStats.sequence_gaps` | `DisplayTelemetry.frames_dropped` |
| **Kabul Edilebilirlik** | KABUL EDİLEMEZ (Donanım/Bant genişliği hatası). | KABUL EDİLEBİLİR (Kullanıcı arayüzü hız uyarlaması). |

> [!IMPORTANT]
> Bir tarayıcı ekran karesi atlandı diye `sequence_gaps` sayacı **ASLA artırılmaz**. Donanım edinim bütünlüğü telemetrisi, UI ekran düşüşlerinden tamamen yalıtılmıştır.

---

## 6. Spektrogram Güncelleme Ayrıştırması

`pcg_core.streaming` modülü Welch güç spektral yoğunluğunu (PSD) hesaplayan `compute_spectral_frame` fonksiyonuna sahiptir.
Önceki mimaride her 512 örnekli blokta bir spektrogram çalıştırılıyordu (~94 kez/saniye).

Yeni mimaride:
- Tam hızlı 48 kHz sinyal DSP filtreleme ve RollingBuffer'a beslenir.
- Spektral hesaplama, `DisplayAggregator` içinde yapılandırılabilir düşük bir kadansta (`spectral_update_hz = 5.0 Hz`) gerçekleştirilir.
- Spektral hesaplama için son 4096 filtrelenmiş örnek kullanılır; bu sayede host CPU yükü %90'ın üzerinde azaltılırken frekans çözünürlüğü tam korunur.
- TypeScript / React tarafında kesinlikle duplike DSP hesaplaması yapılmaz.

---

## 7. Metrik Semantiği: İşlem Hacmi (Throughput) vs Uçtan Uca Gecikme (Latency)

AuscultaForge'da aşağıdaki 6 metrik kavramı birbirinden kesin çizgilerle ayrılmıştır:

1. **Acquisition Sample Rate (Edinim Örnekleme Frekansı):** Sensörün nominal donanım frekansı (Rev-A için 48.000 Hz).
2. **Acquisition Block Duration (Edinim Blok Süresi):** Bir donanım paketinin temsil ettiği fiziksel süre (512 / 48.000 = 10,67 ms).
3. **Host Processing Runtime (Ana Bilgisayar İşlem Süresi):** 512 örneğin normalize edilmesi, DSP'den geçirilmesi, diske yazılması ve ekran için desime edilmesinde CPU'nun harcadığı gerçek duvar saati süresi (~1,5–2,5 ms/blok).
4. **Display Update Rate (Ekran Güncelleme Frekansı):** Ekran karelerinin üretilip WebSocket'e verildiği frekans (varsayılan: 25 Hz).
5. **Browser Render Rate (Tarayıcı Çizim Hızı):** Tarayıcının `requestAnimationFrame` ile monitöre bastığı kare hızı (60 Hz).
6. **End-to-End Latency (Uçtan Uca Gecikme):** Diyaframdaki fiziksel ses dalgasından ekrandaki piksele / hoparlöre kadar geçen toplam gecikme.

> [!WARNING]
> **Uçtan Uca Gecikme Şu Anda ÖLÇÜLEMEZ.** Fiziksel Rev-A donanımı (akustik sensör, I2S DMA, USB CDC) masada olmadan uçtan uca gecikme veya USB gecikmesi iddia etmek mühendislik etiğine aykırıdır. Şu anda ölçülen ve doğrulanan değer **HOST İŞLEM KAPASİTESİ (Host Processing Capacity)** ve **GERÇEK ZAMAN FAKTÖRÜDÜR (Real-Time Factor, RTF > 5x)**.

---

## 8. 30 Saniyelik Jüri / Savunma Açıklaması

> *"Hardware Rev-A donanımımız 48 kHz mono kalitesinde yüksek frekanslı kalp ve akciğer seslerini yakalar. Ancak 48.000 örneği doğrudan tarayıcıya göndermek arayüzü kilitler ve anlamsızdır. Biz tam-çözünürlüklü edinimi, DSP filtrelemeyi ve WAV oturum kaydını ekran çizim hızından mimari olarak ayırdık.*
>
> *Ham verinin her bir örneği 48 kHz'de doğrudan diske kaydedilirken, ekran katmanı min/max tepe-koruyucu desimasyonla 25 Hz hızında güncellenir. Arayüzün yavaşlaması durumunda sınırlı kuyruk yapımız eski ekran karelerini güvenle atar; ancak ses kaydından tek bir örnek bile kaybolmaz ve donanım bütünlüğü sayaçları etkilenmez. Host işlem kapasitemiz gerçek zamanın 5 katından hızlıdır."*
