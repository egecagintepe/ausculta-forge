# 05 — Spektral Analiz: FFT, Welch PSD ve Spektrogram

## Bu nedir?

Spektral analiz, zaman domeni dalga formundaki (genlik-zaman) PCG sinyalini frekans domenine (güç-frekans veya zaman-frekans) dönüştürerek kalbin akustik titreşimlerinin hangi frekanslarda yoğunlaştığını ortaya çıkaran matematiksel yöntemler bütünüdür.

---

## Üç Temel Spektral Araç ve Farkları

AuscultaForge içinde kullanılan üç spektral temsil biçimi:

| Yöntem | Ne Yapar? | Avantajı | Sınırlılığı | AuscultaForge'da Nerede Kullanılır? |
|---|---|---|---|---|
| **Standart FFT (Fast Fourier Transform)** | Bloğun veya sinyalin tamamına doğrudan Fourier dönüşümü uygular. | Matematiksel olarak en hızlı ve yalın yöntemdir. | Rastgele gürültüde varyansı çok yüksektir; sinyal periyodik değilse spektral sızıntı yapar. | Ham spektrum incelemelerinde. |
| **Welch PSD (Güç Spektral Yoğunluğu)** | Sinyali örtüşen pencerelere böler, her parçayı pencereleyip FFT alır ve ortalamasını çıkarır. | Varyansı düşürür, gürültüyü pürüzsüzleştirir; stabil bir güç spektrumu verir. | Zaman bilgisini kaybeder; tüm pencere için tek bir ortalama eğri verir. | Canlı akışta [`SpectralFrame`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/streaming.py#L90-L100) (anlık spektrum göstergesi). |
| **Spektrogram (STFT Tabanlı)** | Kayan pencereler boyunca zaman-frekans matrisi ($S_{xx}(f, t)$) üretir. | Zaman ve frekans bilgisini bir arada sunar; S1, S2 ve üfürümlerin zamanlamasını gösterir. | Zaman ve frekans çözünürlüğü arasında Heisenberg-Gabor belirsizlik ödünü vardır. | Çevrimdışı raporda [`SpectrogramData`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/analysis.py#L38-L53) ve kayan tampon görselleştirmesinde. |

---

## Spektral Sızıntı (Spectral Leakage) ve Pencereleme (Windowing)

Sonsuz bir sinyalin sonlu bir blokla (ör. 256 örnek) kesilmesi, sinyalin dikdörtgen bir pencereyle çarpılması anlamına gelir. Frekans domeninde dikdörtgen pencere bir `sinc` fonksiyonudur ve yan kulakçıkları (side lobes) çok yüksektir; bu durum gerçekte olmayan yapay frekansların spektrumda belirmesine (spectral leakage) yol açar.

AuscultaForge'da SciPy'ın `welch` ve `spectrogram` fonksiyonları kullanılarak Hanning/Hann pencerelemesi uygulanır. Bu pencereler sinyalin uç noktalarını yumuşatarak yan kulakçıkları bastırır ve frekans doğruluğunu garanti eder.

---

## AuscultaForge Spektral Veri Yapıları

### 1. Canlı Çerçeve: `SpectralFrame`
[`software/pcg_core/streaming.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/streaming.py#L90-L100):
Canlı akış esnasında UI frekans barlarına hafif bir veri sağlamak için tasarlanmıştır:
- `frequencies_hz`: Frekans ekseni (Hz).
- `power_db`: Desibel (dB) ölçekli güç değerleri ($10 \log_{10}(P)$).
- `peak_frequency_hz`: En yüksek enerjili baskın tepe frekansı.
- `dominant_band`: Fizyolojik bant sınıfı (`sub_audible`, `fundamental_pcg`, `extended_pcg`).

### 2. Çevrimdışı Analiz: `SpectrogramData`
[`software/pcg_core/analysis.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/analysis.py#L38-L53):
Bir kaydın tamamının 2B spektral haritasını ve enerji dağılım oranlarını özetler:
- `sub_audible_0_20hz`: 20 Hz altındaki düşük frekanslı göğüs/solunum enerjisi oranı.
- `fundamental_pcg_20_150hz`: S1 ve S2 kalp seslerinin temel enerjisinin toplam enerjiye oranı.
- `extended_pcg_150_600hz`: Üfürüm ve kapak titreşim enerjisi oranı.
- `high_freq_above_600hz`: Filtrelenmiş yüksek frekans kalıntısı.

---

## İlgili Dosyalar ve Testler

- Spektrogram hesaplama: [`software/pcg_core/analysis.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/analysis.py#L67-L140)
- Canlı spektral çerçeve: [`software/pcg_core/streaming.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/pcg_core/streaming.py#L102-L167)
- Testler: [`software/tests/test_analysis.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_analysis.py#L29-L60), [`software/tests/test_streaming.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_streaming.py#L162-L177)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Kardiyak akustikte yalnızca zaman dalga formuna bakarak üfürümleri ve kapak patolojilerini ayırt etmek zordur. AuscultaForge iki düzeyde spektral analiz sunar: Canlı akışta gürültü varyansını azaltan Welch PSD yöntemiyle anlık frekans tepe değerini ve baskın fizyolojik bandı takip ediyoruz; çevrimdışı raporda ise STFT tabanlı 2B spektrogram üreterek enerjinin temel kalp sesleri (20–150 Hz) ile üfürüm bölgeleri (150–600 Hz) arasındaki dağılımını makinece okunabilir yüzdelerle raporluyoruz."*
