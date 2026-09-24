# 04 — Sayısal Sinyal İşleme (DSP), Filtreleme ve Metrikler

## Bu nedir?

Bu modül, mikrofon veya simülatörden gelen ham kalp sesi sinyalini fizyolojik açıdan anlamlı akustik banda odaklayan, gürültüleri süzen ve sinyalin enerji karakteristiğini ölçen sayısal filtreleme ve istatistiksel metrik katmanıdır.

---

## Neden Butterworth Bant Geçiren Filtre?

[`software/pcg_core/dsp.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/dsp.py) içinde 4. derece Butterworth IIR bant geçiren filtre kullanılmaktadır.

### Filtre Tipi Seçim Karşılaştırması
- **Butterworth:** Geçirme bandında azami düz genlik cevabı (maximally flat magnitude response) sunar. Dalgalanma (ripple) yapmaz; kalp seslerinin ve üfürümlerin göreceli harmonik oranlarını yapay olarak bozmaz.
- **Chebyshev / Eliptik:** Geçiş bandı daha diktir ancak geçirme bandında genlik dalgalanmaları (ripple) oluşturarak akustik doğruluğu saptırır.
- **FIR (Sonlu Dürtü Cevaplı):** Mükemmel doğrusal faz sağlar ancak düşük frekanslı (20 Hz) keskin kesimler için yüzlerce katsayı gerektirir; bu da gömülü veya canlı akışta kabul edilemez gecikme (latency) ve işlem yükü yaratır.

### İkinci Dereceden Bölümler (Second-Order Sections - SOS)
Filtre transfer fonksiyonu doğrudan $b, a$ polinomları yerine SOS (`output="sos"`) matrisi olarak tasarlanmıştır. Bu, 32-bit kayan nokta aritmetiğinde kutup-sıfır yakınsamalarından kaynaklanan sayısal kararsızlıkları (numerical instability) ve yuvarlama hatalarını önler.

---

## Durumsal Filtreleme (Stateful Filtering): `sosfilt` ve `zi`

Blok tabanlı sinyal işlemede yapılan en kritik hata, her gelen bloğu sıfırdan (`zi=0`) filtrelemektir. Bu yapıldığında her 256 örnekte bir (blok sınırlarında) filtre geçici rejim (transient response) sıçraması yapar ve hoparlörde "tıkırtı / klik" seslerine, spektrumda ise yapay geniş bant çizgilerine yol açar.

```text
Yanlış (Durumsuz):
Blok 0: [=== Sinyal ===]  (zi sıfırlanır)
Blok 1: ╱╲[=== Sinyal ===]  <-- Sınırda yapay sıçrama (transient click)

Doğru (AuscultaForge Stateful):
Blok 0: [=== Sinyal ===] ──zi aktarılır──► Blok 1: [=== Sinyal ===] (Pürüzsüz süreklilik)
```

[`software/pcg_core/dsp.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/dsp.py#L30-L36):
```python
# Başlangıç durumu (initial condition) sıfırlanır
self.zi = sosfilt_zi(self.sos) * 0.0

def process(self, block: SampleBlock) -> SampleBlock:
    # Filtre çalıştırılırken son durum (zi) bir sonraki blok için saklanır
    y, self.zi = sosfilt(self.sos, block.samples, zi=self.zi)
    return ...
```

---

## Geçici (Provisional) 20–600 Hz Bandı

- **Neden 20 Hz altı kesiliyor?** Solunum göğüs hareketleri, stetoskop çanının tene sürtünmesi (friction noise) ve bağırsak peristaltik hareketleri genellikle 0–20 Hz arasındadır.
- **Neden 600 Hz üstü kesiliyor?** İskelet kası elektriksel aktivitesi (EMG gürültüsü), ortamdaki insan konuşmaları ve mikrofon RF parazitleri çoğunlukla bu bandın üzerindedir.
- **Neden bu kesin karar değildir?** Akustik başlığın (Ozan) mekanik rezonansı ve danışman hekimlerin stetoskop tını tercihleri fiziksel prototip üzerinde test edildikten sonra alt ve üst kesim frekansları güncellenecektir. Mimari bu parametreleri tamamen konfigüre edilebilir tutar.

---

## İstatistiksel Sinyal Metrikleri

[`software/pcg_core/metrics.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/metrics.py) dosyasında hesaplanan üç temel büyüklük:

1. **RMS (Root Mean Square - Etkin Değer):**
   $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} x[i]^2}$$
   Sinyalin ortalama enerji gücünü temsil eder. Filtreleme öncesi ve sonrası RMS oranı, filtrenin bastırdığı gürültü miktarını gösterir.
2. **Mutlak Tepe Değeri (Peak Absolute):**
   $$\text{Peak} = \max(|x[i]|)$$
   Sinyalin doyuma (clipping) ulaşıp ulaşmadığını denetler. $1.0$'a yaklaşan değerler sensör kazancının fazla olduğunu gösterir.
3. **Tepe Faktörü (Crest Factor):**
   $$\text{Crest Factor} = \frac{\text{Peak}}{\text{RMS}}$$
   Sinyalin ne kadar "darbesel" (impulsive) olduğunu gösterir. Saf sinüs dalgasında $\sqrt{2} \approx 1.414$ iken, S1 ve S2 gibi ani patlamalı kalp seslerinde 6 ila 12 arasına yükselir.

---

## İlgili Dosyalar ve Testler

- Filtre çekirdeği: [`software/pcg_core/dsp.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/dsp.py)
- Metrikler: [`software/pcg_core/metrics.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/metrics.py)
- Testler: [`software/tests/test_core.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_core.py#L14-L20)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Filtreleme katmanımızda 4. derece Butterworth bant geçiren filtre kullanıyoruz; çünkü Butterworth geçirme bandında tamamen düz bir genlik cevabı vererek kalp seslerinin harmonik dengesini bozmaz. En kritik mühendislik detayı filtrenin durumsal (stateful) olmasıdır: SciPy'ın `sosfilt` fonksiyonuyla bloklar arasındaki iç filtre durumunu (`zi`) koruyoruz. Bu sayede blok sınırlarında oluşabilecek tıklama seslerini ve geçici rejim süreksizliklerini matematiksel olarak önlüyoruz."*
