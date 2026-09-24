# AuscultaForge — Mühendislik ve Biyomedikal Terimler Sözlüğü (Glossary)

Bu sözlük, AuscultaForge projesinde kullanılan temel biyomedikal akustik, sayısal sinyal işleme (DSP) ve gömülü yazılım kavramlarını açıklar.

---

### A
- **Aliasing (Örtüşme):** Analog sinyal Nyquist frekansının ($f_s / 2$) altındaki bir hızla örneklendiğinde, yüksek frekans bileşenlerinin düşük frekans bölgesine katlanarak sinyali yapay olarak bozması olayı.
- **Auscultation (Oskültasyon / Dinleme):** Vücut içindeki seslerin (kalp, akciğer, bağırsak) stetoskop gibi bir dinleme aracıyla incelenmesi muayenesi.

### B
- **Bandpass Filter (Bant Geçiren Filtre):** Belirli bir alt frekans ($f_{low}$) ile üst frekans ($f_{high}$) arasındaki sinyalleri geçiren, bu aralığın dışındakileri ise zayıflatan sayısal veya analog filtre.
- **Butterworth Filter (Butterworth Filtresi):** Geçirme bandında (passband) azami düz genlik cevabına sahip (maximally flat), dalgalanma (ripple) üretmeyen frekans seçici IIR filtre türü.

### C
- **Clipping (Kırpılma / Doyum):** Sinyal genliğinin ADC'nin veya sayısal veri tipinin izin verdiği azami sınırı aşarak tepe noktalarının düz bir çizgi halinde kesilmesi ve şiddetli harmonik bozulma üretmesi.
- **Crest Factor (Tepe Faktörü):** Bir sinyalin mutlak tepe değerinin etkin değerine (RMS) oranı ($\frac{\text{Peak}}{\text{RMS}}$). Sinyalin ne kadar darbesel/patlamalı olduğunu gösterir.

### D
- **DMA (Direct Memory Access - Doğrudan Bellek Erişimi):** Mikrodenetleyici CPU'sunu meşgul etmeden ses örneklerinin I2S/ADC donanımından RAM tamponlarına donanımsal olarak aktarılması mekanizması.

### F
- **FFT (Fast Fourier Transform - Hızlı Fourier Dönüşümü):** Ayrık Fourier Dönüşümünü (DFT) $O(N^2)$ yerine $O(N \log N)$ karmaşıklığında hesaplayan temel algoritma.
- **FIFO (First-In-First-Out):** İlk giren verinin ilk çıktığı kuyruk mantığı; kayan pencere tamponlarında en eski verinin atılıp en yeninin eklenmesi prensibi.

### L
- **Latency (Gecikme Süresi):** Akustik titreşimin mikrofona çarptığı andan PC'de işlenip ekrana/hoparlöre ulaştığı ana kadar geçen toplam uçtan uca süre (blok süresi, edinim, iletim, tamponlama, DSP ve arayüz gecikmelerinin toplamıdır).
- **Loose Coupling (Gevşek Bağlılık):** Yazılım modüllerinin (örneğin veri kaynağı ile DSP filtresinin) birbirinin iç detaylarını bilmeden yalnızca standart arayüzler (`SampleBlock`) üzerinden haberleşmesi prensibi.

### M
- **Murmur (Kardiyak Üfürüm):** Kalp kapaklarındaki darlık (stenoz) veya yetmezlik (regürjitasyon) nedeniyle kanın türbülanslı akması sonucu oluşan, genellikle 150–600 Hz aralığında gözlemlenen ek patolojik hışırtı sesleri.

### N
- **Nyquist Frequency (Nyquist Frekansı):** Bir örnekleme sisteminde aliasing oluşmadan yakalanabilecek azami teorik frekans; örnekleme frekansının tam yarısıdır ($f_{Nyquist} = \frac{f_s}{2}$).

### P
- **PCG (Phonocardiogram - Fonokardiyogram):** Kalbin mekanik kasılma, gevşeme ve kapak hareketlerinin ürettiği akustik seslerin grafiksel zaman-genlik kaydı.
- **PSD (Power Spectral Density - Güç Spektral Yoğunluğu):** Sinyal gücünün frekans eksenindeki dağılımı (birim frekans başına düşen güç).

### R
- **RMS (Root Mean Square - Etkin Değer):** Bir sinyalin karelerinin ortalamasının karekökü; sinyalin taşıdığı ortalama gücün matematiksel ölçüsü.
- **Rolling Buffer (Kayan Pencere Tamponu):** Sürekli akan bir sinyalin sadece son belirli bir süresini (ör. 5 saniye) sabit boyutlu bir hafıza alanında dinamik olarak saklayan veri yapısı.

### S
- **S1 (Birinci Kalp Sesi):** Ventriküler sistol başlangıcında atriyoventriküler (Mitral ve Triküspit) kapakların kapanmasıyla çıkan temel kalp sesi ("lubb").
- **S2 (İkinci Kalp Sesi):** Ventriküler diyastol başlangıcında semilunar (Aort ve Pulmoner) kapakların kapanmasıyla oluşan temel kalp sesi ("dubb").
- **SampleBlock:** AuscultaForge'da tek bir zaman dilimine ait örnek dizisini, sıra numarasını, zaman damgasını ve örnekleme frekansını taşıyan standart nesne.
- **Second-Order Sections (SOS):** Yüksek dereceli sayısal filtrelerin ardışık 2. dereceden biquad bölümler matrisi olarak ifade edilmesi; sayısal taşma ve hassasiyet kaybını önler.
- **Spectral Leakage (Spektral Sızıntı):** Sonlu bir pencereyle kesilen sinyalin süreksiz uç noktaları nedeniyle frekans enerjisinin komşu frekans kutucuklarına (bins) yayılması hatası.
- **Spectrogram (Spektrogram):** Kısa Zamanlı Fourier Dönüşümü (STFT) kullanılarak sinyalin zaman içindeki spektral yoğunluk değişimini gösteren iki boyutlu zaman-frekans haritası.
- **Stateful Filtering (Durumsal Filtreleme):** Parça parça işlenen akışlarda, bir önceki bloğun bitişindeki filtre gecikme hattı durumunun (`zi`) bir sonraki bloğun başlangıcına aktarılması.

### W
- **Welch Method (Welch Yöntemi):** Sinyali örtüşen pencerelere bölüp her birinin periyodogramını aldıktan sonra ortalamasını alarak güç spektrum varyansını azaltan PSD hesaplama tekniği.
- **Windowing (Pencereleme):** Blok sınırlarında spektral sızıntıyı önlemek amacıyla sinyal bloklarının uç noktalarını sıfıra doğru yumuşatan ağırlık fonksiyonları (ör. Hanning, Hamming).
