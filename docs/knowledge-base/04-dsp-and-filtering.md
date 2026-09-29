# 04 â€” SayÄ±sal Sinyal Ä°ÅŸleme (DSP), Filtreleme ve Metrikler

## Bu nedir?

Bu modÃ¼l, mikrofon veya simÃ¼latÃ¶rden gelen ham kalp sesi sinyalini fizyolojik aÃ§Ä±dan anlamlÄ± akustik banda odaklayan, gÃ¼rÃ¼ltÃ¼leri sÃ¼zen ve sinyalin enerji karakteristiÄŸini Ã¶lÃ§en sayÄ±sal filtreleme ve istatistiksel metrik katmanÄ±dÄ±r.

---

## Neden Butterworth Bant GeÃ§iren Filtre?

[`software/pcg_core/dsp.py`](../../software/pcg_core/dsp.py) iÃ§inde 4. derece Butterworth IIR bant geÃ§iren filtre kullanÄ±lmaktadÄ±r.

### Filtre Tipi SeÃ§im KarÅŸÄ±laÅŸtÄ±rmasÄ±
- **Butterworth (IIR):** GeÃ§irme bandÄ±nda azami dÃ¼z genlik cevabÄ± (maximally flat magnitude response) sunar. GeÃ§irme bandÄ±nda dalgalanma (ripple) yapmaz; bu sayede spektral analizde yapay tepe veya Ã§ukurlar oluÅŸturmaz. Ancak doÄŸrusal faz cevabÄ± vermez ve grup gecikmesi frekansa gÃ¶re deÄŸiÅŸir.
- **Chebyshev / Eliptik:** GeÃ§iÅŸ bandÄ± daha diktir ancak geÃ§irme bandÄ±nda veya durdurma bandÄ±nda genlik dalgalanmalarÄ± (ripple) oluÅŸturur.
- **FIR (Sonlu DÃ¼rtÃ¼ CevaplÄ±):** MÃ¼kemmel doÄŸrusal faz saÄŸlar; ancak dÃ¼ÅŸÃ¼k frekanslÄ± (Ã¶r. 20 Hz) dar geÃ§iÅŸ bantlarÄ± elde etmek yÃ¼ksek filtre derecesi (Ã§ok sayÄ±da katsayÄ±) gerektirir. YÃ¼ksek dereceli FIR filtreler daha fazla iÅŸlem yÃ¼kÃ¼ ve filtre gecikmesi doÄŸurabileceÄŸinden, mevcut prototip aÅŸamasÄ±nda IIR Butterworth yapÄ±sÄ± tercih edilmiÅŸtir. Bu bir tasarÄ±m takasÄ±dÄ±r (trade-off); ilerleyen aÅŸamalarda donanÄ±m ve iÅŸlemci kaynaklarÄ±na gÃ¶re FIR alternatifleri deÄŸerlendirilebilir.

### Ä°kinci Dereceden BÃ¶lÃ¼mler (Second-Order Sections - SOS)
Filtre transfer fonksiyonu doÄŸrudan $b, a$ polinomlarÄ± yerine SOS (`output="sos"`) matrisi olarak tasarlanmÄ±ÅŸtÄ±r. Bu, 32-bit kayan nokta aritmetiÄŸinde kutup-sÄ±fÄ±r yakÄ±nsamalarÄ±ndan kaynaklanan sayÄ±sal kararsÄ±zlÄ±klarÄ± (numerical instability) ve yuvarlama hatalarÄ±nÄ± Ã¶nler.

---

## Durumsal Filtreleme (Stateful Filtering): `sosfilt` ve `zi`

Blok tabanlÄ± sinyal iÅŸlemede yapÄ±lan en kritik hata, her gelen bloÄŸu sÄ±fÄ±rdan (`zi=0`) filtrelemektir. Bu yapÄ±ldÄ±ÄŸÄ±nda her 256 Ã¶rnekte bir (blok sÄ±nÄ±rlarÄ±nda) filtre geÃ§ici rejim (transient response) sÄ±Ã§ramasÄ± yapar ve hoparlÃ¶rde "tÄ±kÄ±rtÄ± / klik" seslerine, spektrumda ise yapay geniÅŸ bant Ã§izgilerine yol aÃ§ar.

```text
YanlÄ±ÅŸ (Durumsuz):
Blok 0: [=== Sinyal ===]  (zi sÄ±fÄ±rlanÄ±r)
Blok 1: â•±â•²[=== Sinyal ===]  <-- SÄ±nÄ±rda yapay sÄ±Ã§rama (transient click)

DoÄŸru (AuscultaForge Stateful):
Blok 0: [=== Sinyal ===] â”€â”€zi aktarÄ±lÄ±râ”€â”€â–º Blok 1: [=== Sinyal ===] (PÃ¼rÃ¼zsÃ¼z sÃ¼reklilik)
```

[`software/pcg_core/dsp.py`](../../software/pcg_core/dsp.py#L30-L36):
```python
# BaÅŸlangÄ±Ã§ durumu (initial condition) sÄ±fÄ±rlanÄ±r
self.zi = sosfilt_zi(self.sos) * 0.0

def process(self, block: SampleBlock) -> SampleBlock:
    # Filtre Ã§alÄ±ÅŸtÄ±rÄ±lÄ±rken son durum (zi) bir sonraki blok iÃ§in saklanÄ±r
    y, self.zi = sosfilt(self.sos, block.samples, zi=self.zi)
    return ...
```

---

## GeÃ§ici (Provisional) 20â€“600 Hz BandÄ±

- **MÃ¼hendislik BaÅŸlangÄ±Ã§ NoktasÄ±:** 20â€“600 Hz aralÄ±ÄŸÄ±, literatÃ¼rde PCG temel kalp sesleri ve Ã¼fÃ¼rÃ¼mler iÃ§in yaygÄ±n kullanÄ±lan geÃ§ici bir baÅŸlangÄ±Ã§ referansÄ±dÄ±r.
- **Alt Kesim (20 Hz):** Solunum hareketleri, mekanik temas ve dÃ¼ÅŸÃ¼k frekanslÄ± temel hat kaymalarÄ±nÄ±n (baseline wander) enerjisinin yoÄŸunlaÅŸtÄ±ÄŸÄ± sub-audible bÃ¶lgeyi zayÄ±flatmak iÃ§in seÃ§ilmiÅŸ bir baÅŸlangÄ±Ã§ deÄŸeridir (tÃ¼m Ã§evresel gÃ¼rÃ¼ltÃ¼lerin tamamen 20 Hz altÄ±nda kaldÄ±ÄŸÄ± iddia edilmez).
- **Ãœst Kesim (600 Hz):** Akustik ilgimizin dÄ±ÅŸÄ±ndaki yÃ¼ksek frekanslÄ± Ã§evresel parazitleri ve sensÃ¶r gÃ¼rÃ¼ltÃ¼lerini zayÄ±flatmak iÃ§in bir Ã¶n sÄ±nÄ±rdÄ±r (tÃ¼m parazitlerin 600 Hz Ã¼stÃ¼nde olduÄŸu anlamÄ±na gelmez).
- **Neden bu kesin karar deÄŸildir?** Akustik baÅŸlÄ±ÄŸÄ±n (Ozan) mekanik rezonansÄ±, sensÃ¶r frekans cevabÄ± ve ilerleyen aÅŸamalarda yapÄ±lacak akustik fantom testleri sonucunda alt ve Ã¼st kesim frekanslarÄ± revize edilecektir. YazÄ±lÄ±m mimarisi bu kesim parametrelerini tamamen konfigÃ¼re edilebilir ve denenebilir tutar.

---

## Ä°statistiksel Sinyal Metrikleri

[`software/pcg_core/metrics.py`](../../software/pcg_core/metrics.py) dosyasÄ±nda hesaplanan Ã¼Ã§ temel bÃ¼yÃ¼klÃ¼k:

1. **RMS (Root Mean Square - Etkin DeÄŸer):**
   $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} x[i]^2}$$
   Sinyalin ortalama enerji gÃ¼cÃ¼nÃ¼ temsil eder. Filtreleme Ã¶ncesi ve sonrasÄ± RMS oranÄ±, filtrenin bastÄ±rdÄ±ÄŸÄ± bant dÄ±ÅŸÄ± enerji miktarÄ±nÄ± gÃ¶sterir.
2. **Mutlak Tepe DeÄŸeri (Peak Absolute):**
   $$\text{Peak} = \max(|x[i]|)$$
   Sinyalin doyuma (clipping) ulaÅŸÄ±p ulaÅŸmadÄ±ÄŸÄ±nÄ± denetler. $1.0$'a yaklaÅŸan deÄŸerler sensÃ¶r kazancÄ±nÄ±n fazla olduÄŸunu gÃ¶sterir.
3. **Tepe FaktÃ¶rÃ¼ (Crest Factor):**
   $$\text{Crest Factor} = \frac{\text{Peak}}{\text{RMS}}$$
   Sinyalin ne kadar "darbesel" (impulsive) olduÄŸunu gÃ¶sterir. Saf sinÃ¼s dalgasÄ±nda $\sqrt{2} \approx 1.414$ iken, S1 ve S2 gibi ani patlamalÄ± kalp seslerinde 6 ila 12 arasÄ±na yÃ¼kselir.

---

## Ä°lgili Dosyalar ve Testler

- Filtre Ã§ekirdeÄŸi: [`software/pcg_core/dsp.py`](../../software/pcg_core/dsp.py)
- Metrikler: [`software/pcg_core/metrics.py`](../../software/pcg_core/metrics.py)
- Testler: [`software/tests/test_core.py`](../../software/tests/test_core.py#L14-L20)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"Filtreleme katmanÄ±mÄ±zda 4. derece Butterworth bant geÃ§iren filtre kullanÄ±yoruz; Ã§Ã¼nkÃ¼ Butterworth geÃ§irme bandÄ±nda azami dÃ¼z genlik cevabÄ± (maximally flat magnitude response) vererek yapay dalgalanma (ripple) Ã¼retmez. En kritik mÃ¼hendislik detayÄ± filtrenin durumsal (stateful) olmasÄ±dÄ±r: SciPy'Ä±n `sosfilt` fonksiyonuyla bloklar arasÄ±ndaki iÃ§ filtre durumunu (`zi`) koruyoruz. Bu sayede blok sÄ±nÄ±rlarÄ±nda oluÅŸabilecek tÄ±klama seslerini ve geÃ§ici rejim sÃ¼reksizliklerini matematiksel olarak Ã¶nlÃ¼yoruz."*
