# 08 â€” Referans ve Yakalanan Sinyal KarÅŸÄ±laÅŸtÄ±rmalÄ± DoÄŸrulama (Reference-vs-Capture Signal Validation)

## Bu nedir?

Bu dokÃ¼man, bilinen, temiz bir **referans PCG sinyali** (Reference Signal) ile fiziksel bir akustik hat, fantom, mikrofon/sensÃ¶r ve analog-dijital Ã§evrim aÅŸamalarÄ±ndan geÃ§erek kaydedilmiÅŸ/alÄ±nmÄ±ÅŸ **yakalanan sinyali** (Captured Signal) nicel mÃ¼hendislik metrikleriyle karÅŸÄ±laÅŸtÄ±ran AuscultaForge doÄŸrulama metodolojisini aÃ§Ä±klar.

GeliÅŸtirilen bu modÃ¼l; donanÄ±m henÃ¼z ortada yokken sentetik bozulum simÃ¼lasyonlarÄ± (`simulate_distorted_capture`) ile Ã§alÄ±ÅŸÄ±r; ileride fiziksel gÃ¶ÄŸÃ¼s fantomu (acoustic phantom) ve prototip donanÄ±m hazÄ±r olduÄŸunda ise aynÄ± matematiksel boru hattÄ± doÄŸrudan gerÃ§ek kayÄ±tlarÄ± doÄŸrulamak iÃ§in kullanÄ±lacaktÄ±r.

---

## Gelecekteki KullanÄ±m Senaryosu (Acoustic Path Pipeline)

```text
Referans PCG (WAV / SayÄ±sal Kaynak)
          â”‚
          â–¼
Akustik Fantom / HoparlÃ¶r TransdÃ¼seri (Acoustic Path)
          â”‚
          â–¼
Mikrofon / SensÃ¶r BaÅŸlÄ±ÄŸÄ± & Analog Ã–n UÃ§ (AFE)
          â”‚
          â–¼
MCU / ADC Edinimi (Acquisition Unit)
          â”‚
          â–¼
Yakalanan PCG (Captured Signal)

                â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
Referans PCG â”€â”€â–ºâ”‚ Zaman Hizalama (Cross-Correlation)   â”‚
Yakalanan PCG â”€â–ºâ”‚ & Nicel Kalite Metrikleri            â”‚â”€â”€â–º DoÄŸrulama Raporu (JSON / CLI)
                â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Neden Fantom Deneylerinde Bilinen Bir Referansa Ä°htiyaÃ§ VardÄ±r?

Bir stetoskop veya akustik biyomedikal sensÃ¶r geliÅŸtirirken, sensÃ¶rÃ¼ doÄŸrudan bir insan gÃ¶ÄŸsÃ¼ne koyup "ses alÄ±nÄ±yor mu" diye bakmak temel bir mÃ¼hendislik hatasÄ±dÄ±r:
1. **Girdi Kontrol Edilemez:** Ä°nsan kalbi her atÄ±mda birebir aynÄ± genlik, frekans ve zamanlama profilini Ã¼retmez (kalp hÄ±zÄ± deÄŸiÅŸkenliÄŸi, solunum modÃ¼lasyonu, hareket artefaktlarÄ±).
2. **KanalÄ±n Bozucu Etkisi AyrÄ±ÅŸtÄ±rÄ±lamaz:** Ã‡Ä±kan sesteki bir zayÄ±flama veya bozulmanÄ±n hastanÄ±n gÃ¶ÄŸÃ¼s yapÄ±sÄ±ndan mÄ±, sensÃ¶rÃ¼n rezonansÄ±ndan mÄ± yoksa ADC gÃ¼rÃ¼ltÃ¼sÃ¼nden mi kaynaklandÄ±ÄŸÄ± bilinemez.
3. **Akustik Fantom Ã‡Ã¶zÃ¼mÃ¼:** Ä°nsan dokusunun akustik empedansÄ±nÄ± taklit eden bir fantoma (silikon/jel blok) bilinen, dijital olarak kaydedilmiÅŸ bir referans sinyal verilir. Ã‡Ä±kÄ±ÅŸta kaydedilen sinyal girdiyle karÅŸÄ±laÅŸtÄ±rÄ±ldÄ±ÄŸÄ±nda, donanÄ±m zincirinin sisteme kattÄ±ÄŸÄ± **gecikme (delay), genlik zayÄ±flamasÄ±/kazancÄ± (gain), gÃ¼rÃ¼ltÃ¼ tabanÄ± (SNR/SER) ve frekans cevabÄ± bozulmalarÄ±** kesin olarak hesaplanabilir.

---

## Neden Ã–znel "KulaÄŸa HoÅŸ Geliyor" (Sounds Good) YaklaÅŸÄ±mÄ± Yetersizdir?

Elektronik veya biyomedikal bir cihaz geliÅŸtirirken "kulaklÄ±kla dinledim, gayet net geliyor" yaklaÅŸÄ±mÄ± kabul edilemez:
- **Ä°nsan KulaÄŸÄ±nÄ±n DoÄŸrusal Olmayan CevabÄ±:** Ä°nsan kulaÄŸÄ± 20â€“100 Hz aralÄ±ÄŸÄ±ndaki dÃ¼ÅŸÃ¼k frekanslÄ± PCG bileÅŸenlerine (S1 ve S2 kalp seslerinin ana enerjisi) karÅŸÄ± son derece duyarsÄ±zdÄ±r (Fletcher-Munson eÅŸit iÅŸitilebilirlik eÄŸrileri). KulaÄŸa "iyi" gelen bir ses, sistemin dÃ¼ÅŸÃ¼k frekanslarÄ± tamamen yok ettiÄŸi anlamÄ±na gelebilir.
- **Faz KaymalarÄ± ve Gecikmeler:** Kulak faz kaymalarÄ±nÄ± veya 20-50 ms seviyesindeki donanÄ±m tampon gecikmelerini ayÄ±rt edemez; ancak bu gecikmeler EKG ile eÅŸzamanlÄ± fonokardiyografide teÅŸhis aÃ§Ä±sÄ±ndan kritiktir.
- **TekrarlanamazlÄ±k:** KiÅŸiden kiÅŸiye, kulaklÄ±ktan kulaklÄ±ÄŸa ve dinleme anÄ±ndaki ortam gÃ¼rÃ¼ltÃ¼sÃ¼ne gÃ¶re deÄŸerlendirme deÄŸiÅŸir. Akademik ve regÃ¼latif (FDA / CE) doÄŸrulamada yalnÄ±zca matematiksel ve Ã¶lÃ§Ã¼lebilir metrikler geÃ§erlidir.

---

## DoÄŸrulama HattÄ±nÄ±n Ã‡alÄ±ÅŸma Prensipleri

### 1. Ã–rnekleme FrekansÄ± YÃ¶netimi ve AÃ§Ä±k Yeniden Ã–rnekleme (Explicit Resampling)
Referans ve yakalanan sinyaller farklÄ± Ã¶rnekleme frekanslarÄ±na sahip olabilir (Ã¶rneÄŸin 2000 Hz PhysioNet referansÄ±, 4000 Hz CirCor verisi veya MCU'dan 16000 Hz gelen bir akÄ±ÅŸ).
- Frekanslar eÅŸitse doÄŸrudan karÅŸÄ±laÅŸtÄ±rma yapÄ±lÄ±r.
- FarklÄ± ise, `scipy.signal.resample_poly` kullanÄ±larak yakalanan sinyal rasyonel faktÃ¶rlerle (up/down) tam olarak referans frekansÄ±na yeniden Ã¶rneklenir.
- **ÅeffaflÄ±k Ä°lkesi:** Yeniden Ã¶rnekleme asla sessizce gizlenmez; `resampled: bool`, orijinal frekanslar ve etkin frekans raporda aÃ§Ä±kÃ§a belirtilir.

### 2. Ã‡apraz Korelasyon (Cross-Correlation) ve Gecikme Kestirimi (Delay Estimation)
Akustik yayÄ±lÄ±m, ADC arabelleÄŸe alma ve USB/seri iletiÅŸim nedeniyle yakalanan sinyal referanstan bir miktar sonra gelir ($y[n] \approx x[n - D]$).
- Ä°ki ayrÄ±k zamanlÄ± sinyalin Ã§apraz korelasyonu hesaplanÄ±r:
  $$R_{xy}[k] = \sum_{n} x[n] y[n + k]$$
- Korelasyonu maksimize eden tepe noktasÄ±nÄ±n indeksi ($k^*$), Ã¶rnek (sample) cinsinden baÄŸÄ±l gecikmeyi (`delay_samples`) verir.
- Gecikme milisaniyeye dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lÃ¼r:
  $$\text{delay\_ms} = \frac{\text{delay\_samples}}{f_s} \times 1000$$
- Sinyaller bulunan gecikme kadar kaydÄ±rÄ±larak kesiÅŸen Ã¶rtÃ¼ÅŸme bÃ¶lgesine (`overlap`) hizalanÄ±r (Signal Alignment).

### 3. KazanÃ§ OranlarÄ± ve En KÃ¼Ã§Ã¼k Kareler KazancÄ± (Gain Ratios & Least-Squares Gain)
DonanÄ±m yÃ¼kselteci (preamp/PGA), fantom kuplajÄ± veya akustik zayÄ±flama genlik Ã¶lÃ§eÄŸini deÄŸiÅŸtirir. ModÃ¼l Ã¼Ã§ farklÄ± genlik oranÄ± hesaplar:

1. **RMS KazanÃ§ OranÄ±:**
   $$\text{Gain}_{\text{RMS}} = \frac{\text{RMS}(y_{\text{aligned}})}{\text{RMS}(x_{\text{aligned}})}$$
2. **Tepe (Peak) KazanÃ§ OranÄ±:**
   $$\text{Gain}_{\text{Peak}} = \frac{\max |y_{\text{aligned}}|}{\max |x_{\text{aligned}}|}$$
3. **En KÃ¼Ã§Ã¼k Kareler KazancÄ± (Least-Squares Gain, $g$):**
   Zaman hizalamasÄ± sonrasÄ±nda $\|y_{\text{aligned}} - g \cdot x_{\text{aligned}}\|^2$ hata enerjisini minimize eden optimal doÄŸrusal Ã¶lÃ§ekleme faktÃ¶rÃ¼:
   $$g = \frac{x_{\text{aligned}} \cdot y_{\text{aligned}}}{x_{\text{aligned}} \cdot x_{\text{aligned}}} = \frac{\sum_{n} x[n] y[n]}{\sum_{n} x[n]^2}$$

#### MÃ¼hendislik Yorumu ve GÃ¼rÃ¼ltÃ¼ AltÄ±nda DavranÄ±ÅŸ FarkÄ±:
- **RMS KazanÃ§ OranÄ± GÃ¼rÃ¼ltÃ¼den Etkilenir (Pozitif SapmalÄ±):** Toplamsal iliÅŸkisiz gÃ¼rÃ¼ltÃ¼ varlÄ±ÄŸÄ±nda yakalanan sinyalin RMS deÄŸeri $\text{RMS}(y) = \sqrt{g^2 \text{RMS}(x)^2 + \sigma_{\text{noise}}^2}$ olacaÄŸÄ±ndan, gÃ¼rÃ¼ltÃ¼ arttÄ±kÃ§a RMS kazancÄ± yapay olarak bÃ¼yÃ¼r.
- **En KÃ¼Ã§Ã¼k Kareler KazancÄ± SapmasÄ±zdÄ±r (Unbiased Estimator):** GÃ¼rÃ¼ltÃ¼ sÄ±fÄ±r ortalamalÄ± ve referansla iliÅŸkisiz olduÄŸunda ($E[x \cdot \text{noise}] = 0$), iÃ§ Ã§arpÄ±m gÃ¼rÃ¼ltÃ¼yÃ¼ sÃ¶nÃ¼mlendirir ve $g$ gerÃ§ek fiziksel kazancÄ± korur.
- **Kritik SÄ±nÄ±r:** Ne RMS kazanÃ§ oranÄ± ne de en kÃ¼Ã§Ã¼k kareler kazancÄ± **asla otomatik olarak "klinik kalite" ÅŸeklinde yorumlanamaz**. YalnÄ±zca donanÄ±m genlik Ã¶lÃ§eklemesini ve gÃ¼rÃ¼ltÃ¼ katkÄ±sÄ±nÄ± matematiksel olarak karakterize ederler.

### 4. Normalize Ã‡apraz Korelasyon (Normalized Cross-Correlation - NCC)
Genlik farklarÄ±ndan baÄŸÄ±msÄ±z olarak sinyallerin dalga formu ÅŸekil benzerliÄŸini (waveform shape similarity) Ã¶lÃ§er:
$$\text{NCC} = \frac{\sum (x[n] - \bar{x})(y[n] - \bar{y})}{\sqrt{\sum (x[n] - \bar{x})^2 \sum (y[n] - \bar{y})^2}}$$
DeÄŸer aralÄ±ÄŸÄ± $[-1.0, +1.0]$ arasÄ±ndadÄ±r. $1.0$, dalga biÃ§imlerinin gecikme dÃ¼zeltildikten sonra kusursuz eÅŸleÅŸtiÄŸini gÃ¶sterir.

### 5. RMSE ve Normalize RMSE (NRMSE)
Ä°ki sinyal arasÄ±ndaki mutlak Ã¶rnek-Ã¶rnek sapmayÄ± Ã¶lÃ§er:
$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{n=1}^{N} (y_{\text{aligned}}[n] - x_{\text{aligned}}[n])^2}$$
$$\text{NRMSE} = \frac{\text{RMSE}}{\text{RMS}(x_{\text{aligned}})}$$

### 6. Sinyal-Hata OranÄ± (Signal-to-Error Ratio - SER)
Sinyal gÃ¼cÃ¼nÃ¼n artÄ±k hata gÃ¼cÃ¼ne oranÄ±nÄ± desibel (dB) cinsinden ifade eder:
$$\text{SER}_{\text{dB}} = 10 \log_{10} \left( \frac{\sum x_{\text{aligned}}[n]^2}{\sum (y_{\text{aligned}}[n] - x_{\text{aligned}}[n])^2} \right)$$
Kusursuz eÅŸleÅŸmelerde sonsuza gitmeyi engellemek adÄ±na sayÄ±sal olarak 100 dB ile sÄ±nÄ±rlandÄ±rÄ±lÄ±r.

### 7. Spektral KarÅŸÄ±laÅŸtÄ±rmalar ve BÃ¼yÃ¼klÃ¼k-Karesi Uyumu (Magnitude-Squared Coherence)
- **BaskÄ±n Frekans FarkÄ± (Dominant Frequency Difference):** Referans ile yakalanan sinyalin tepe gÃ¼Ã§ frekanslarÄ± arasÄ±ndaki mutlak fark ($|\Delta f_{\text{dom}}|$).
- **Bant Enerji OranÄ± FarklarÄ±:** PCG bantlarÄ±ndaki enerji daÄŸÄ±lÄ±mÄ±nÄ±n ne kadar korunduÄŸunu gÃ¶steren oran farklarÄ±.
- **BÃ¼yÃ¼klÃ¼k-Karesi Uyumu ($C_{xy}(f)$):** Welch yÃ¶ntemi ile PCG geÃ§iÅŸ bandÄ±nda (20â€“600 Hz) hesaplanan ortalama tutarlÄ±lÄ±k:
  $$C_{xy}(f) = \frac{|P_{xy}(f)|^2}{P_{xx}(f) P_{yy}(f)}$$
  DeÄŸer $[0, 1]$ aralÄ±ÄŸÄ±nda olup donanÄ±mÄ±n frekans bazÄ±nda sinyale ne kadar lineer ve gÃ¼rÃ¼ltÃ¼sÃ¼z yanÄ±t verdiÄŸini gÃ¶sterir.

---

## Sentetik Bozulum SimÃ¼latÃ¶rÃ¼ (`simulate_distorted_capture`)

HenÃ¼z donanÄ±m ve fantom Ã¼retimi sÃ¼rerken doÄŸrulama algoritmalarÄ±nÄ± test etmek iÃ§in deterministik bir simÃ¼latÃ¶r geliÅŸtirilmiÅŸtir:
- **Gecikme Enjeksiyonu (Delay):** Ä°stenen milisaniyede sÄ±fÄ±r dolgulama (zero padding) ile gecikme ekler.
- **KazanÃ§ Ã‡arpanÄ± (Gain):** Sinyal genliÄŸini doÄŸrusal olarak Ã¶lÃ§ekler.
- **Toplamsal Gauss GÃ¼rÃ¼ltÃ¼sÃ¼ (Additive Gaussian Noise):** Ä°stenen standart sapmada beyaz gÃ¼rÃ¼ltÃ¼ ekler.
- **AlÃ§ak GeÃ§iren Filtreleme (Lowpass Filter):** Akustik sÃ¶nÃ¼mlemeyi simÃ¼le etmek iÃ§in 4. derece Butterworth filtre uygular.
- **Determinizm:** Sabit bir rastgele tohum (`seed`) ile testlerin her Ã§alÄ±ÅŸtÄ±rmada bit seviyesinde aynÄ± sonucu vermesi saÄŸlanÄ±r.

---

## CLI KullanÄ±mÄ±

DoÄŸrulama aracÄ± doÄŸrudan komut satÄ±rÄ±ndan Ã§alÄ±ÅŸtÄ±rÄ±labilir:

```powershell
# 1. SimÃ¼lasyon Modu (Bench Validation)
python -m pcg_core.validate_capture --reference data/raw/a0001.wav --simulate --delay-ms 45 --gain 0.8 --noise-std 0.01 --save-report

# 2. Ä°ki GerÃ§ek WAV KarÅŸÄ±laÅŸtÄ±rma Modu
python -m pcg_core.validate_capture --reference data/raw/a0001.wav --capture data/raw/phantom_capture.wav --save-report
```

Kaydedilen JSON raporu tam kaynak bilgisi (provenance) iÃ§erir:
- Referans ve yakalanan dosya SHA-256 Ã¶zetleri
- Git commit SHA
- Python, NumPy, SciPy sÃ¼rÃ¼mleri ve iÅŸletim sistemi
- Ã–lÃ§Ã¼len tÃ¼m sayÄ±sal metrikler

---

## Ä°lgili Dosyalar

- DoÄŸrulama Ã‡ekirdeÄŸi: [`software/pcg_core/validation.py`](../../software/pcg_core/validation.py)
- CLI ArayÃ¼zÃ¼: [`software/pcg_core/validate_capture.py`](../../software/pcg_core/validate_capture.py)
- Birim Testleri: [`software/tests/test_validation.py`](../../software/tests/test_validation.py)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"GeliÅŸtirdiÄŸimiz stetoskop donanÄ±mÄ±nÄ±n sinyal doÄŸruluÄŸunu 'kulaÄŸa iyi geliyor' gibi subjektif hislerle deÄŸil; matematiksel bir referans-yakalama doÄŸrulama hattÄ±yla test ediyoruz. Akustik fantomumuza bilinen bir PCG sinyali verdiÄŸimizde, sistemimiz Ã§apraz korelasyonla donanÄ±m gecikmesini milisaniye hassasiyetinde tespit edip sinyalleri otomatik hizalar. ArdÄ±ndan dalga formu benzerliÄŸini (NCC), genlik kazanÃ§ oranlarÄ±nÄ±, RMSE/SER deÄŸerlerini ve spektral tutarlÄ±lÄ±ÄŸÄ± (coherence) tek bir mÃ¼hendislik raporu olarak Ã¼retir. DonanÄ±mÄ±mÄ±z henÃ¼z Ã¼retimdeyken bile bu hattÄ± sentetik gecikme ve gÃ¼rÃ¼ltÃ¼ simÃ¼lasyonlarÄ±yla doÄŸrulayarak gelecekteki testlerimizi gÃ¼venceye aldÄ±k."*
