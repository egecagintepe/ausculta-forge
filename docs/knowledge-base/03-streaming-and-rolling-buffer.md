# 03 — Canlı Akış Mimarisi ve Kayan Pencere Tamponu (Rolling Buffer)

## Bu nedir?

Canlı akış mimarisi, sürekli gelen ses verisinin parça parça (bloklar halinde) sisteme kabul edilmesi ve son $N$ saniyelik geçmişin (ör. son 5 saniye) analiz ve görselleştirme için bellekte kayan bir pencere (rolling buffer) içinde canlı tutulmasıdır.

---

## Blok Tabanlı Akış (Block/Chunk-Based Streaming)

### Neden Tek Tek Örnek (Sample-by-Sample) Değil?
Dijital ses işlemede iki uç yaklaşım vardır:
1. **Tek Örnek (Sample-by-sample):** Her örnek için bir kesme veya Python fonksiyon çağrısı yapılır. Saniyede 2000 kez çağrı yapmak CPU bağlam değiştirme (context-switch) ve yorumlayıcı (interpreter) ek yükü doğurur.
2. **Toplu Veri (Batch):** Kaydın tamamı (ör. 30 saniye) bittikten sonra işlenir. Canlı izleme ve eşzamanlı görselleştirme yapılamaz.

**AuscultaForge Çözümü:** Veriler 256 örneklik sabit bloklar halinde akar.
- $f_s = 2000\text{ Hz}$ için blok süresi: $\frac{256}{2000} = 128\text{ ms}$.
- $f_s = 4000\text{ Hz}$ için blok süresi: $\frac{256}{4000} = 64\text{ ms}$.

> [!NOTE]
> **Gecikme (Latency) Analizi:** 128 ms'lik blok süresi uçtan uca gecikmenin tek belirleyicisi değildir; gecikmeye doğrudan katkı sağlayan temel bileşenlerden biridir. Toplam uçtan uca gecikme; sensör edinimi, iletim (transport/UART), tamponlama, DSP filtreleme hesaplama süresi ve kullanıcı arayüzü (UI) çizim gecikmelerinin toplamından oluşur. 256 örneklik bloklama, Python ve NumPy vektörel işlemlerine yüksek hesaplama verimliliği sunarken gecikmeyi kabul edilebilir sınırlar içinde tutmak için seçilmiş bir mühendislik takasıdır (trade-off).

---

## Sıra Numaraları ve Zaman Damgaları

Her `SampleBlock` iki kritik metaveri taşır:
1. **`sequence` (Sıra Numarası):** $0, 1, 2, \dots$ şeklinde artan tamsayıdır. Projemizde akış sırasında kaybolan, yinelenen veya sırası bozulan blokları tespit etmek için kullanılan birincil açık (explicit) denetim mekanizmasıdır.
2. **`timestamp_s` (Zaman Damgası):** Bloğun başlangıç zamanıdır. Zaman damgaları saat kaymasını (drift) tek başına engellemez; ancak zamanlama analizi yapmayı, donanım-yazılım saat kaymalarını tespit etmeyi (drift detection), zamansal hizalamayı ve çoklu modalite (ör. ileride olası EKG entegrasyonu) için senkronizasyonu mümkün kılar.

---

## Kayan Pencere Tamponu: `RollingBuffer`

[`software/pcg_core/buffers.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/buffers.py) sınıfı sabit süreli bir FIFO (First-In-First-Out) bellek alanı yönetir.

```text
Kapasite: 5.0 saniye (fs=2000 Hz => 10,000 örnek)

[──────────────── Eski Örnekler ────────────────]
                       │
                       │ Yeni blok gelir (+256 örnek)
                       ▼
[── En Eski 256 Atılır ──][── Kaydırılır ──][── Yeni 256 Eklenir ──]
```

### Algoritmik Özellikler
- **Bitişik Bellek ve Kaydırma (Contiguous In-Place Shift):** RollingBuffer, klasik bir dairesel/halka tampon (ring buffer) olarak DEĞİL, yeni bloklar geldikçe veriyi dizi içinde sola kaydıran (in-place shift) bitişik bir tampon olarak uygulanmıştır. Tüketiciler (get_samples() veya get_view()) daima kronolojik sırada tek parça bir 1D NumPy dizisi alır; halka tamponlardaki gibi indeks sarma (wrap-around) veya iki parçalı dilimleme hesaplamalarına gerek kalmaz.
- **Dinamik Kapasite Başlatma:** Tampon yaratılırken $f_s$ bilinmiyorsa, gelen ilk `SampleBlock`'un frekansına göre $N = \text{int}(\text{capacity\_seconds} \times f_s)$ olarak boyutlandırılır.
- **Frekans Değişimi Uyarlaması:** Akış ortasında mikrodenetleyici örnekleme frekansını değiştirirse `reset_sample_rate()` ile tampon güvenle yeniden ölçeklendirilir.

---

## Neden Bu Tasarım Seçildi? Hangi Problemleri Önlüyor?

- **Bellek Şişmesini (Memory Leak) Önler:** Sürekli çalışan bir canlı sinyal edinim sisteminde ses dizisi sınırsız büyüyemez; `RollingBuffer` bellek kullanımını sabit (birkaç yüz kilobayt) tutar.
- **Canlı Metrik Tutarlılığı:** RMS, tepe genlik ve frekans dağılımı tüm kaydın ortalaması yerine, incelenen test sinyalinin *son birkaç saniyelik* anlık akustik davranışını yansıtır.

---

## İlgili Dosyalar ve Testler

- Tampon uygulaması: [`software/pcg_core/buffers.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/buffers.py)
- Akış motoru: [`software/pcg_core/streaming.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/streaming.py#L208-L270)
- Canlı CLI gösterimi: [`software/pcg_core/stream_demo.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/stream_demo.py)
- Testler: [`software/tests/test_streaming.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_streaming.py#L56-L95)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Gerçek zamanlı kalp sesi simülasyonunda veriyi 256 örneklik bloklar halinde işliyoruz; bu blok süresi (2000 Hz'de 128 ms), uçtan uca gecikmeyi düşük tutarken NumPy işlemlerinde yüksek hesaplama verimliliği sağlar. `RollingBuffer` yapımız ise bellekte sinyalin son 5 saniyelik geçmişini kayan bir pencere içinde tutar. Yeni bloklar geldikçe en eskiler atılır; böylece bellek sabit kalırken sisteme ve gelecekteki kullanıcı arayüzüne anlık güncellenen RMS ve spektrum bilgisi sunulur."*
