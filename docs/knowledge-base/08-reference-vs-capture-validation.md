# 08 — Referans ve Yakalanan Sinyal Karşılaştırmalı Doğrulama (Reference-vs-Capture Signal Validation)

## Bu nedir?

Bu doküman, bilinen, temiz bir **referans PCG sinyali** (Reference Signal) ile fiziksel bir akustik hat, fantom, mikrofon/sensör ve analog-dijital çevrim aşamalarından geçerek kaydedilmiş/alınmış **yakalanan sinyali** (Captured Signal) nicel mühendislik metrikleriyle karşılaştıran AuscultaForge doğrulama metodolojisini açıklar.

Geliştirilen bu modül; donanım henüz ortada yokken sentetik bozulum simülasyonları (`simulate_distorted_capture`) ile çalışır; ileride fiziksel göğüs fantomu (acoustic phantom) ve prototip donanım hazır olduğunda ise aynı matematiksel boru hattı doğrudan gerçek kayıtları doğrulamak için kullanılacaktır.

---

## Gelecekteki Kullanım Senaryosu (Acoustic Path Pipeline)

```text
Referans PCG (WAV / Sayısal Kaynak)
          │
          ▼
Akustik Fantom / Hoparlör Transdüseri (Acoustic Path)
          │
          ▼
Mikrofon / Sensör Başlığı & Analog Ön Uç (AFE)
          │
          ▼
MCU / ADC Edinimi (Acquisition Unit)
          │
          ▼
Yakalanan PCG (Captured Signal)

                ┌──────────────────────────────────────┐
Referans PCG ──►│ Zaman Hizalama (Cross-Correlation)   │
Yakalanan PCG ─►│ & Nicel Kalite Metrikleri            │──► Doğrulama Raporu (JSON / CLI)
                └──────────────────────────────────────┘
```

---

## Neden Fantom Deneylerinde Bilinen Bir Referansa İhtiyaç Vardır?

Bir stetoskop veya akustik biyomedikal sensör geliştirirken, sensörü doğrudan bir insan göğsüne koyup "ses alınıyor mu" diye bakmak temel bir mühendislik hatasıdır:
1. **Girdi Kontrol Edilemez:** İnsan kalbi her atımda birebir aynı genlik, frekans ve zamanlama profilini üretmez (kalp hızı değişkenliği, solunum modülasyonu, hareket artefaktları).
2. **Kanalın Bozucu Etkisi Ayrıştırılamaz:** Çıkan sesteki bir zayıflama veya bozulmanın hastanın göğüs yapısından mı, sensörün rezonansından mı yoksa ADC gürültüsünden mi kaynaklandığı bilinemez.
3. **Akustik Fantom Çözümü:** İnsan dokusunun akustik empedansını taklit eden bir fantoma (silikon/jel blok) bilinen, dijital olarak kaydedilmiş bir referans sinyal verilir. Çıkışta kaydedilen sinyal girdiyle karşılaştırıldığında, donanım zincirinin sisteme kattığı **gecikme (delay), genlik zayıflaması/kazancı (gain), gürültü tabanı (SNR/SER) ve frekans cevabı bozulmaları** kesin olarak hesaplanabilir.

---

## Neden Öznel "Kulağa Hoş Geliyor" (Sounds Good) Yaklaşımı Yetersizdir?

Elektronik veya biyomedikal bir cihaz geliştirirken "kulaklıkla dinledim, gayet net geliyor" yaklaşımı kabul edilemez:
- **İnsan Kulağının Doğrusal Olmayan Cevabı:** İnsan kulağı 20–100 Hz aralığındaki düşük frekanslı PCG bileşenlerine (S1 ve S2 kalp seslerinin ana enerjisi) karşı son derece duyarsızdır (Fletcher-Munson eşit işitilebilirlik eğrileri). Kulağa "iyi" gelen bir ses, sistemin düşük frekansları tamamen yok ettiği anlamına gelebilir.
- **Faz Kaymaları ve Gecikmeler:** Kulak faz kaymalarını veya 20-50 ms seviyesindeki donanım tampon gecikmelerini ayırt edemez; ancak bu gecikmeler EKG ile eşzamanlı fonokardiyografide teşhis açısından kritiktir.
- **Tekrarlanamazlık:** Kişiden kişiye, kulaklıktan kulaklığa ve dinleme anındaki ortam gürültüsüne göre değerlendirme değişir. Akademik ve regülatif (FDA / CE) doğrulamada yalnızca matematiksel ve ölçülebilir metrikler geçerlidir.

---

## Doğrulama Hattının Çalışma Prensipleri

### 1. Örnekleme Frekansı Yönetimi ve Açık Yeniden Örnekleme (Explicit Resampling)
Referans ve yakalanan sinyaller farklı örnekleme frekanslarına sahip olabilir (örneğin 2000 Hz PhysioNet referansı, 4000 Hz CirCor verisi veya MCU'dan 16000 Hz gelen bir akış).
- Frekanslar eşitse doğrudan karşılaştırma yapılır.
- Farklı ise, `scipy.signal.resample_poly` kullanılarak yakalanan sinyal rasyonel faktörlerle (up/down) tam olarak referans frekansına yeniden örneklenir.
- **Şeffaflık İlkesi:** Yeniden örnekleme asla sessizce gizlenmez; `resampled: bool`, orijinal frekanslar ve etkin frekans raporda açıkça belirtilir.

### 2. Çapraz Korelasyon (Cross-Correlation) ve Gecikme Kestirimi (Delay Estimation)
Akustik yayılım, ADC arabelleğe alma ve USB/seri iletişim nedeniyle yakalanan sinyal referanstan bir miktar sonra gelir ($y[n] \approx x[n - D]$).
- İki ayrık zamanlı sinyalin çapraz korelasyonu hesaplanır:
  $$R_{xy}[k] = \sum_{n} x[n] y[n + k]$$
- Korelasyonu maksimize eden tepe noktasının indeksi ($k^*$), örnek (sample) cinsinden bağıl gecikmeyi (`delay_samples`) verir.
- Gecikme milisaniyeye dönüştürülür:
  $$\text{delay\_ms} = \frac{\text{delay\_samples}}{f_s} \times 1000$$
- Sinyaller bulunan gecikme kadar kaydırılarak kesişen örtüşme bölgesine (`overlap`) hizalanır (Signal Alignment).

### 3. Kazanç Oranları ve En Küçük Kareler Kazancı (Gain Ratios & Least-Squares Gain)
Donanım yükselteci (preamp/PGA), fantom kuplajı veya akustik zayıflama genlik ölçeğini değiştirir. Modül üç farklı genlik oranı hesaplar:

1. **RMS Kazanç Oranı:**
   $$\text{Gain}_{\text{RMS}} = \frac{\text{RMS}(y_{\text{aligned}})}{\text{RMS}(x_{\text{aligned}})}$$
2. **Tepe (Peak) Kazanç Oranı:**
   $$\text{Gain}_{\text{Peak}} = \frac{\max |y_{\text{aligned}}|}{\max |x_{\text{aligned}}|}$$
3. **En Küçük Kareler Kazancı (Least-Squares Gain, $g$):**
   Zaman hizalaması sonrasında $\|y_{\text{aligned}} - g \cdot x_{\text{aligned}}\|^2$ hata enerjisini minimize eden optimal doğrusal ölçekleme faktörü:
   $$g = \frac{x_{\text{aligned}} \cdot y_{\text{aligned}}}{x_{\text{aligned}} \cdot x_{\text{aligned}}} = \frac{\sum_{n} x[n] y[n]}{\sum_{n} x[n]^2}$$

#### Mühendislik Yorumu ve Gürültü Altında Davranış Farkı:
- **RMS Kazanç Oranı Gürültüden Etkilenir (Pozitif Sapmalı):** Toplamsal ilişkisiz gürültü varlığında yakalanan sinyalin RMS değeri $\text{RMS}(y) = \sqrt{g^2 \text{RMS}(x)^2 + \sigma_{\text{noise}}^2}$ olacağından, gürültü arttıkça RMS kazancı yapay olarak büyür.
- **En Küçük Kareler Kazancı Sapmasızdır (Unbiased Estimator):** Gürültü sıfır ortalamalı ve referansla ilişkisiz olduğunda ($E[x \cdot \text{noise}] = 0$), iç çarpım gürültüyü sönümlendirir ve $g$ gerçek fiziksel kazancı korur.
- **Kritik Sınır:** Ne RMS kazanç oranı ne de en küçük kareler kazancı **asla otomatik olarak "klinik kalite" şeklinde yorumlanamaz**. Yalnızca donanım genlik ölçeklemesini ve gürültü katkısını matematiksel olarak karakterize ederler.

### 4. Normalize Çapraz Korelasyon (Normalized Cross-Correlation - NCC)
Genlik farklarından bağımsız olarak sinyallerin dalga formu şekil benzerliğini (waveform shape similarity) ölçer:
$$\text{NCC} = \frac{\sum (x[n] - \bar{x})(y[n] - \bar{y})}{\sqrt{\sum (x[n] - \bar{x})^2 \sum (y[n] - \bar{y})^2}}$$
Değer aralığı $[-1.0, +1.0]$ arasındadır. $1.0$, dalga biçimlerinin gecikme düzeltildikten sonra kusursuz eşleştiğini gösterir.

### 5. RMSE ve Normalize RMSE (NRMSE)
İki sinyal arasındaki mutlak örnek-örnek sapmayı ölçer:
$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{n=1}^{N} (y_{\text{aligned}}[n] - x_{\text{aligned}}[n])^2}$$
$$\text{NRMSE} = \frac{\text{RMSE}}{\text{RMS}(x_{\text{aligned}})}$$

### 6. Sinyal-Hata Oranı (Signal-to-Error Ratio - SER)
Sinyal gücünün artık hata gücüne oranını desibel (dB) cinsinden ifade eder:
$$\text{SER}_{\text{dB}} = 10 \log_{10} \left( \frac{\sum x_{\text{aligned}}[n]^2}{\sum (y_{\text{aligned}}[n] - x_{\text{aligned}}[n])^2} \right)$$
Kusursuz eşleşmelerde sonsuza gitmeyi engellemek adına sayısal olarak 100 dB ile sınırlandırılır.

### 7. Spektral Karşılaştırmalar ve Büyüklük-Karesi Uyumu (Magnitude-Squared Coherence)
- **Baskın Frekans Farkı (Dominant Frequency Difference):** Referans ile yakalanan sinyalin tepe güç frekansları arasındaki mutlak fark ($|\Delta f_{\text{dom}}|$).
- **Bant Enerji Oranı Farkları:** PCG bantlarındaki enerji dağılımının ne kadar korunduğunu gösteren oran farkları.
- **Büyüklük-Karesi Uyumu ($C_{xy}(f)$):** Welch yöntemi ile PCG geçiş bandında (20–600 Hz) hesaplanan ortalama tutarlılık:
  $$C_{xy}(f) = \frac{|P_{xy}(f)|^2}{P_{xx}(f) P_{yy}(f)}$$
  Değer $[0, 1]$ aralığında olup donanımın frekans bazında sinyale ne kadar lineer ve gürültüsüz yanıt verdiğini gösterir.

---

## Sentetik Bozulum Simülatörü (`simulate_distorted_capture`)

Henüz donanım ve fantom üretimi sürerken doğrulama algoritmalarını test etmek için deterministik bir simülatör geliştirilmiştir:
- **Gecikme Enjeksiyonu (Delay):** İstenen milisaniyede sıfır dolgulama (zero padding) ile gecikme ekler.
- **Kazanç Çarpanı (Gain):** Sinyal genliğini doğrusal olarak ölçekler.
- **Toplamsal Gauss Gürültüsü (Additive Gaussian Noise):** İstenen standart sapmada beyaz gürültü ekler.
- **Alçak Geçiren Filtreleme (Lowpass Filter):** Akustik sönümlemeyi simüle etmek için 4. derece Butterworth filtre uygular.
- **Determinizm:** Sabit bir rastgele tohum (`seed`) ile testlerin her çalıştırmada bit seviyesinde aynı sonucu vermesi sağlanır.

---

## CLI Kullanımı

Doğrulama aracı doğrudan komut satırından çalıştırılabilir:

```powershell
# 1. Simülasyon Modu (Bench Validation)
python -m pcg_core.validate_capture --reference data/raw/a0001.wav --simulate --delay-ms 45 --gain 0.8 --noise-std 0.01 --save-report

# 2. İki Gerçek WAV Karşılaştırma Modu
python -m pcg_core.validate_capture --reference data/raw/a0001.wav --capture data/raw/phantom_capture.wav --save-report
```

Kaydedilen JSON raporu tam kaynak bilgisi (provenance) içerir:
- Referans ve yakalanan dosya SHA-256 özetleri
- Git commit SHA
- Python, NumPy, SciPy sürümleri ve işletim sistemi
- Ölçülen tüm sayısal metrikler

---

## İlgili Dosyalar

- Doğrulama Çekirdeği: [`software/pcg_core/validation.py`](../../software/pcg_core/validation.py)
- CLI Arayüzü: [`software/pcg_core/validate_capture.py`](../../software/pcg_core/validate_capture.py)
- Birim Testleri: [`software/tests/test_validation.py`](../../software/tests/test_validation.py)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Geliştirdiğimiz stetoskop donanımının sinyal doğruluğunu 'kulağa iyi geliyor' gibi subjektif hislerle değil; matematiksel bir referans-yakalama doğrulama hattıyla test ediyoruz. Akustik fantomumuza bilinen bir PCG sinyali verdiğimizde, sistemimiz çapraz korelasyonla donanım gecikmesini milisaniye hassasiyetinde tespit edip sinyalleri otomatik hizalar. Ardından dalga formu benzerliğini (NCC), genlik kazanç oranlarını, RMSE/SER değerlerini ve spektral tutarlılığı (coherence) tek bir mühendislik raporu olarak üretir. Donanımımız henüz üretimdeyken bile bu hattı sentetik gecikme ve gürültü simülasyonlarıyla doğrulayarak gelecekteki testlerimizi güvenceye aldık."*
