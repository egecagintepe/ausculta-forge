# 02 — SampleBlock ve Kaynak Soyutlaması (Source Abstraction)

## Bu nedir?

`SampleBlock`, AuscultaForge sisteminde fiziksel donanımdan, seri haberleşmeden veya dosya biçimlerinden bağımsız olarak ses verisini taşıyan standart veri aktarım birimidir.

Kaynak soyutlaması (Source abstraction) ise ses verisinin nereden geldiğini (yapay üretim, WAV dosyası, USB seri port, Wi-Fi soketi) sinyal işleme hattından (DSP) tamamen gizleyen yazılım tasarım desenidir.

---

## Veri Modeli: `SampleBlock`

[`software/pcg_core/models.py`](../../software/pcg_core/models.py) içinde tanımlı olan yapı:

```python
@dataclass(slots=True)
class SampleBlock:
    sequence: int          # Blok sıra takip numarası (0, 1, 2, ...)
    timestamp_s: float     # Bloğun başlangıç zaman damgası (saniye)
    sample_rate_hz: int    # Örnekleme frekansı (Hz)
    samples: np.ndarray    # 1D float32, normalize edilmiş [-1.0, 1.0] dizi
    source: str = "unknown"# Veri kaynağı kimliği ("mock", "a0001.wav", vb.)
```

### Tasarım Tercihleri ve Detaylar
1. **`slots=True`:** Python nesne ek yükünü (`__dict__`) ortadan kaldırır. Saniyede onlarca blok aktarılırken bellek tahsisini (allocation) ve çöp toplayıcı (garbage collector) baskısını asgariye indirir.
2. **`float32` Normalizasyon:** Farklı ADC çözünürlükleri (12-bit, 16-bit, 24-bit) doğrudan ham tamsayı olarak değil, $[-1.0, 1.0]$ aralığına normalize edilerek taşınır. Bu sayede DSP filtre katsayıları ve RMS metrikleri donanım bit derinliğinden bağımsızlaşır.
3. **Tek Kanallı 1-D Doğrulama:** `__post_init__` içinde boyut ve pozitif frekans kontrolü yapılarak geçersiz verinin algoritmaya girmesi ilk adımda engellenir.

---

## Kaynak Türleri ve Rolleri

```text
               ┌───────────────────────┐
               │    MockPCGSource      │ ──► Sentetik S1/S2 test verisi
               └───────────────────────┘
               ┌───────────────────────┐
               │       WavSource       │ ──► Çevrimdışı toplu analiz
               └───────────────────────┘
               ┌───────────────────────┐
               │   RealtimeWavSource   │ ──► Canlı MCU akış simülatörü
               └───────────────────────┘
               ┌───────────────────────┐
               │ *Gelecek* SerialSource│ ──► Donanım Kaynağı (Aday: ESP32 / USB-UART)
               └───────────────────────┘
                           │
                           ▼  (Hepsi SampleBlock Iterator üretir)
               ┌───────────────────────┐
               │      SampleBlock      │
               └───────────────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Ortak DSP & Metrik   │
               └───────────────────────┘
```

1. **`MockPCGSource` ([`sources.py`](../../software/pcg_core/sources.py#L9-L60)):**
   - Belirtilen kalp atım hızında (BPM) sönümlü sinüs paketleriyle S1/S2 sesleri ve arka plan gürültüsü üretir.
   - Donanım veya internet bağlantısı olmaksızın DSP hattını çalıştırmayı sağlar.
2. **`WavSource` ([`sources.py`](../../software/pcg_core/sources.py#L62-L93)):**
   - Diskten mono WAV dosyası okur (16-bit tamsayıları `float32`'ye çevirir) ve bloklar halinde sunar.
   - Çevrimdışı doğrulama ve veri kümesi analizi için kullanılır.
3. **`RealtimeWavSource` ([`sources.py`](../../software/pcg_core/sources.py#L95-L137)):**
   - WAV kaydını gerçek duvar saati (wall-clock) hızında replaying yaparak canlı MCU akışını taklit eder.
   - Hızlı testler için `--fast` (unpaced) modunu destekler.
4. **Gelecekteki `SerialSource`:**
   - MCU'dan gelen seri paketleri ayrıştırıp aynı `SampleBlock` nesnesini oluşturacaktır.

---

## Neden Bu Tasarım Seçildi? Hangi Problemleri Önlüyor?

- **Protokol Kilidini Önleme:** Taşıma katmanı kablolu Native USB olarak seçilmiş olup wire paket formatı (CRC, başlık baytları, framing) henüz kilitlenmemiştir. Sinyal işleme kodunun donanım baytlarına doğrudan bağlanması engellenmiştir.
- **Tekrarlanabilir Test Edilebilirlik:** Filtreleme ve analiz kodları hiçbir zaman "gerçek porta bağlı mıyım?" kontrolü yapmaz; bu sayede birim testleri sıfır donanımla nanosaniyeler içinde koşar.

---

## İlgili Dosyalar ve Testler

- Veri yapısı: [`software/pcg_core/models.py`](../../software/pcg_core/models.py)
- Kaynak sınıfları: [`software/pcg_core/sources.py`](../../software/pcg_core/sources.py)
- Testler: [`software/tests/test_core.py`](../../software/tests/test_core.py#L8-L12), [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py#L17-L54)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Yazılım mimarimizin kalbinde `SampleBlock` arayüzü yer alır. Giriş verisinin nereden geldiği (yapay sinyal, gerçek WAV kaydı veya mikrodenetleyici UART hattı) sinyal işleme algoritmalarımız için farksızdır. Tüm kaynaklar veriyi aynı normalize float32 blokları, sıra numarası ve zaman damgasıyla iletir. Bu gevşek bağlılık (loose coupling), donanım tasarımındaki olası revizyonların PC yazılımını etkilemesini tamamen engeller."*
