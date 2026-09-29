# 05 â€” Spektral Analiz: FFT, Welch PSD ve Spektrogram

## Bu nedir?

Spektral analiz, zaman domeni dalga formundaki (genlik-zaman) PCG sinyalini frekans domenine (gÃ¼Ã§-frekans veya zaman-frekans) dÃ¶nÃ¼ÅŸtÃ¼rerek kalbin akustik titreÅŸimlerinin hangi frekanslarda yoÄŸunlaÅŸtÄ±ÄŸÄ±nÄ± ortaya Ã§Ä±karan matematiksel yÃ¶ntemler bÃ¼tÃ¼nÃ¼dÃ¼r.

---

## ÃœÃ§ Temel Spektral AraÃ§ ve FarklarÄ±

AuscultaForge iÃ§inde kullanÄ±lan Ã¼Ã§ spektral temsil biÃ§imi:

| YÃ¶ntem | Ne Yapar? | AvantajÄ± | SÄ±nÄ±rlÄ±lÄ±ÄŸÄ± | AuscultaForge'da Nerede KullanÄ±lÄ±r? |
|---|---|---|---|---|
| **Standart FFT (Fast Fourier Transform)** | BloÄŸun veya sinyalin tamamÄ±na doÄŸrudan Fourier dÃ¶nÃ¼ÅŸÃ¼mÃ¼ uygular. | Matematiksel olarak en hÄ±zlÄ± ve yalÄ±n yÃ¶ntemdir. | Rastgele gÃ¼rÃ¼ltÃ¼de varyansÄ± Ã§ok yÃ¼ksektir; sinyal periyodik deÄŸilse spektral sÄ±zÄ±ntÄ± yapar. | Ham spektrum incelemelerinde. |
| **Welch PSD (GÃ¼Ã§ Spektral YoÄŸunluÄŸu)** | Sinyali Ã¶rtÃ¼ÅŸen pencerelere bÃ¶ler, her parÃ§ayÄ± pencereleyip FFT alÄ±r ve ortalamasÄ±nÄ± Ã§Ä±karÄ±r. | VaryansÄ± dÃ¼ÅŸÃ¼rÃ¼r, gÃ¼rÃ¼ltÃ¼yÃ¼ pÃ¼rÃ¼zsÃ¼zleÅŸtirir; stabil bir gÃ¼Ã§ spektrumu verir. | Zaman bilgisini kaybeder; tÃ¼m pencere iÃ§in tek bir ortalama eÄŸri verir. | CanlÄ± akÄ±ÅŸta [`SpectralFrame`](../../software/pcg_core/streaming.py#L90-L100) (anlÄ±k spektrum gÃ¶stergesi). |
| **Spektrogram (STFT TabanlÄ±)** | Kayan pencereler boyunca zaman-frekans matrisi ($S_{xx}(f, t)$) Ã¼retir. | Zaman ve frekans bilgisini bir arada sunar; S1, S2 ve Ã¼fÃ¼rÃ¼mlerin zamanlamasÄ±nÄ± gÃ¶sterir. | Zaman ve frekans Ã§Ã¶zÃ¼nÃ¼rlÃ¼ÄŸÃ¼ arasÄ±nda Heisenberg-Gabor belirsizlik Ã¶dÃ¼nÃ¼ vardÄ±r. | Ã‡evrimdÄ±ÅŸÄ± raporda [`SpectrogramData`](../../software/pcg_core/analysis.py#L38-L53) ve kayan tampon gÃ¶rselleÅŸtirmesinde. |

---

## Spektral SÄ±zÄ±ntÄ± (Spectral Leakage) ve Pencereleme (Windowing)

Sonsuz bir sinyalin sonlu bir blokla (Ã¶r. 256 Ã¶rnek) kesilmesi, sinyalin dikdÃ¶rtgen bir pencereyle Ã§arpÄ±lmasÄ± anlamÄ±na gelir. Frekans domeninde dikdÃ¶rtgen pencere bir `sinc` fonksiyonudur ve yan kulakÃ§Ä±klarÄ± (side lobes) Ã§ok yÃ¼ksektir; bu durum gerÃ§ekte olmayan yapay frekanslarÄ±n spektrumda belirmesine (spectral leakage) yol aÃ§ar.

AuscultaForge'da SciPy'Ä±n `welch` ve `spectrogram` fonksiyonlarÄ± kullanÄ±larak Hanning/Hann pencerelemesi uygulanÄ±r. Bu pencereler sinyalin uÃ§ noktalarÄ±nÄ± yumuÅŸatarak yan kulakÃ§Ä±klarÄ± bastÄ±rÄ±r ve frekans doÄŸruluÄŸunu garanti eder.

---

## AuscultaForge Spektral Veri YapÄ±larÄ±

### 1. CanlÄ± Ã‡erÃ§eve: `SpectralFrame`
[`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L90-L100):
CanlÄ± akÄ±ÅŸ esnasÄ±nda UI frekans barlarÄ±na hafif bir veri saÄŸlamak iÃ§in tasarlanmÄ±ÅŸtÄ±r:
- `frequencies_hz`: Frekans ekseni (Hz).
- `power_db`: Desibel (dB) Ã¶lÃ§ekli gÃ¼Ã§ deÄŸerleri ($10 \log_{10}(P)$).
- `peak_frequency_hz`: En yÃ¼ksek enerjili baskÄ±n tepe frekansÄ±.
- `dominant_band`: Fizyolojik bant sÄ±nÄ±fÄ± (`sub_audible`, `fundamental_pcg`, `extended_pcg`).

### 2. Ã‡evrimdÄ±ÅŸÄ± Analiz: `SpectrogramData`
[`software/pcg_core/analysis.py`](../../software/pcg_core/analysis.py#L38-L53):
Bir kaydÄ±n tamamÄ±nÄ±n 2B spektral haritasÄ±nÄ± ve enerji daÄŸÄ±lÄ±m oranlarÄ±nÄ± Ã¶zetler:
- `sub_audible_0_20hz`: 20 Hz altÄ±ndaki dÃ¼ÅŸÃ¼k frekanslÄ± gÃ¶ÄŸÃ¼s/solunum enerjisi oranÄ±.
- `fundamental_pcg_20_150hz`: S1 ve S2 kalp seslerinin temel enerjisinin toplam enerjiye oranÄ±.
- `extended_pcg_150_600hz`: ÃœfÃ¼rÃ¼m ve kapak titreÅŸim enerjisi oranÄ±.
- `high_freq_above_600hz`: FiltrelenmiÅŸ yÃ¼ksek frekans kalÄ±ntÄ±sÄ±.

---

## Ä°lgili Dosyalar ve Testler

- Spektrogram hesaplama: [`software/pcg_core/analysis.py`](../../software/pcg_core/analysis.py#L67-L140)
- CanlÄ± spektral Ã§erÃ§eve: [`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L102-L167)
- Testler: [`software/tests/test_analysis.py`](../../software/tests/test_analysis.py#L29-L60), [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py#L162-L177)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"Kardiyak akustikte yalnÄ±zca zaman dalga formuna bakarak Ã¼fÃ¼rÃ¼mleri ve kapak patolojilerini ayÄ±rt etmek zordur. AuscultaForge iki dÃ¼zeyde spektral analiz sunar: CanlÄ± akÄ±ÅŸta gÃ¼rÃ¼ltÃ¼ varyansÄ±nÄ± azaltan Welch PSD yÃ¶ntemiyle anlÄ±k frekans tepe deÄŸerini ve baskÄ±n fizyolojik bandÄ± takip ediyoruz; Ã§evrimdÄ±ÅŸÄ± raporda ise STFT tabanlÄ± 2B spektrogram Ã¼reterek enerjinin temel kalp sesleri (20â€“150 Hz) ile Ã¼fÃ¼rÃ¼m bÃ¶lgeleri (150â€“600 Hz) arasÄ±ndaki daÄŸÄ±lÄ±mÄ±nÄ± makinece okunabilir yÃ¼zdelerle raporluyoruz."*
