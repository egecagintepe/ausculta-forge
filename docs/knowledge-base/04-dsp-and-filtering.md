# 04 — Sayısal Sinyal İşleme (DSP), Filtreleme ve Metrikler

## Bu nedir?

Bu modül, mikrofon veya simülatörden gelen ham kalp sesi sinyalini fizyolojik açıdan anlamlı akustik banda odaklayan, gürültüleri süzen ve sinyalin enerji karakteristiğini ölçen sayısal filtreleme ve istatistiksel metrik katmanıdır.

---

## Neden Butterworth Bant Geçiren Filtre?

[`software/pcg_core/dsp.py`](../../software/pcg_core/dsp.py) içinde 4. derece Butterworth IIR bant geçiren filtre kullanılmaktadır.

### Filtre Tipi Seçim Karşılaştırması
- **Butterworth (IIR):** Geçirme bandında azami düz genlik cevabı (maximally flat magnitude response) sunar. Geçirme bandında dalgalanma (ripple) yapmaz; bu sayede spektral analizde yapay tepe veya çukurlar oluşturmaz. Ancak doğrusal faz cevabı vermez ve grup gecikmesi frekansa göre değişir.
- **Chebyshev / Eliptik:** Geçiş bandı daha diktir ancak geçirme bandında veya durdurma bandında genlik dalgalanmaları (ripple) oluşturur.
- **FIR (Sonlu Dürtü Cevaplı):** Mükemmel doğrusal faz sağlar; ancak düşük frekanslı (ör. 20 Hz) dar geçiş bantları elde etmek yüksek filtre derecesi (çok sayıda katsayı) gerektirir. Yüksek dereceli FIR filtreler daha fazla işlem yükü ve filtre gecikmesi doğurabileceğinden, mevcut prototip aşamasında IIR Butterworth yapısı tercih edilmiştir. Bu bir tasarım takasıdır (trade-off); ilerleyen aşamalarda donanım ve işlemci kaynaklarına göre FIR alternatifleri değerlendirilebilir.

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

[`software/pcg_core/dsp.py`](../../software/pcg_core/dsp.py#L30-L36):
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

- **Mühendislik Başlangıç Noktası:** 20–600 Hz aralığı, literatürde PCG temel kalp sesleri ve üfürümler için yaygın kullanılan geçici bir başlangıç referansıdır.
- **Alt Kesim (20 Hz):** Solunum hareketleri, mekanik temas ve düşük frekanslı temel hat kaymalarının (baseline wander) enerjisinin yoğunlaştığı sub-audible bölgeyi zayıflatmak için seçilmiş bir başlangıç değeridir (tüm çevresel gürültülerin tamamen 20 Hz altında kaldığı iddia edilmez).
- **Üst Kesim (600 Hz):** Akustik ilgimizin dışındaki yüksek frekanslı çevresel parazitleri ve sensör gürültülerini zayıflatmak için bir ön sınırdır (tüm parazitlerin 600 Hz üstünde olduğu anlamına gelmez).
- **Neden bu kesin karar değildir?** Akustik başlığın (Ozan) mekanik rezonansı, sensör frekans cevabı ve ilerleyen aşamalarda yapılacak akustik fantom testleri sonucunda alt ve üst kesim frekansları revize edilecektir. Yazılım mimarisi bu kesim parametrelerini tamamen konfigüre edilebilir ve denenebilir tutar.

---

## İstatistiksel Sinyal Metrikleri

[`software/pcg_core/metrics.py`](../../software/pcg_core/metrics.py) dosyasında hesaplanan üç temel büyüklük:

1. **RMS (Root Mean Square - Etkin Değer):**
   $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} x[i]^2}$$
   Sinyalin ortalama enerji gücünü temsil eder. Filtreleme öncesi ve sonrası RMS oranı, filtrenin bastırdığı bant dışı enerji miktarını gösterir.
2. **Mutlak Tepe Değeri (Peak Absolute):**
   $$\text{Peak} = \max(|x[i]|)$$
   Sinyalin doyuma (clipping) ulaşıp ulaşmadığını denetler. $1.0$'a yaklaşan değerler sensör kazancının fazla olduğunu gösterir.
3. **Tepe Faktörü (Crest Factor):**
   $$\text{Crest Factor} = \frac{\text{Peak}}{\text{RMS}}$$
   Sinyalin ne kadar "darbesel" (impulsive) olduğunu gösterir. Saf sinüs dalgasında $\sqrt{2} \approx 1.414$ iken, S1 ve S2 gibi ani patlamalı kalp seslerinde 6 ila 12 arasına yükselir.

---

## İlgili Dosyalar ve Testler

- Filtre çekirdeği: [`software/pcg_core/dsp.py`](../../software/pcg_core/dsp.py)
- Metrikler: [`software/pcg_core/metrics.py`](../../software/pcg_core/metrics.py)
- Testler: [`software/tests/test_core.py`](../../software/tests/test_core.py#L14-L20)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Filtreleme katmanımızda 4. derece Butterworth bant geçiren filtre kullanıyoruz; çünkü Butterworth geçirme bandında azami düz genlik cevabı (maximally flat magnitude response) vererek yapay dalgalanma (ripple) üretmez. En kritik mühendislik detayı filtrenin durumsal (stateful) olmasıdır: SciPy'ın `sosfilt` fonksiyonuyla bloklar arasındaki iç filtre durumunu (`zi`) koruyoruz. Bu sayede blok sınırlarında oluşabilecek tıklama seslerini ve geçici rejim süreksizliklerini matematiksel olarak önlüyoruz."*
