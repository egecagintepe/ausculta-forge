# 12 — Oturum Analizi ve Referans-Kayıt Doğrulama Laboratuvarı (Session Analysis & Reference-vs-Capture Workbench)

## 1. Bu Dokümanın Amacı

Bu doküman, AuscultaForge sistemine eklenen **Oturum Analizi ve Referans-Kayıt Doğrulama Laboratuvarı**'nın (*Session Analysis & Reference-vs-Capture Workbench*) çalışma prensiplerini, arka plandaki mühendislik matematiğini, arayüz mimarisini ve gelecekteki fiziksel fantom deneylerindeki rolünü açıklar.

Bu laboratuvar; kaydedilmiş stetoskop edinim oturumlarını incelemek, bilinen dijital referans uyaranını (*known reference input / reference PCG stimulus*) yüklemek, donanım edinimini referansla nicel olarak karşılaştırmak ve makine tarafından okunabilir (JSON) mühendislik raporları üretmek için geliştirilmiştir.

---

## 2. Neden Reference vs Capture (Referans ve Yakalanan Sinyal) Karşılaştırması Yapıyoruz?

Elektronik bir stetoskop veya akustik biyomedikal transdüser geliştirilirken, sensörü doğrudan bir insan göğsüne yerleştirip "ses geliyor mu" veya "ses kulağa güzel geliyor mu" demek akademik ve regülatif açıdan geçersizdir:

1. **İnsan Girdisi Kontrol Edilemez ve Tekrarlanamaz:** İnsan kalbi her atımda birebir aynı akustik genlik, frekans dağılımı ve zamanlamayı üretmez. Solunum modülasyonu, kalp hızı değişkenliği (HRV) ve hasta hareketleri ölçümü sürekli bozar.
2. **Kanalın Bozucu Etkisi Ayrıştırılamaz:** Kaydedilen sesteki bir bozulmanın hastanın göğüs duvarı kalınlığından mı, mikrofonun rezonans tepkisinden mi, analog ön yüz (AFE) kazancından mı yoksa ADC gürültüsünden mi kaynaklandığı bilinemez.
3. **Akustik Fantom Çözümü:** İnsan dokusunun akustik empedansını taklit eden bir fantom bloğuna (silikon/balistik jel/akustik kuplaj) dijital olarak bilinen, bozulmamış bir **Referans PCG WAV** sinyali verilir (örneğin hoparlör veya aktüatör ile). Prototip stetoskop başlığı bu sesi algılar, sayısallaştırır ve AuscultaForge oturumu olarak kaydeder.
4. **Mühendislik Çıkarımı:** Referans ile yakalanan sinyal karşılaştırıldığında donanımın sisteme kattığı **gecikme (delay), doğrusal kazanç (least-squares gain), sinyal-hata oranı (SER), frekans bozulmaları (PSD & Band Energy) ve frekans tutarlılığı (coherence)** kesin olarak sayısallaştırılır.

---

## 3. Gelecekteki Fiziksel Fantom İş Akışı (Phantom Laboratory Workflow)

Laboratuvar arayüzü ve arkasındaki servis katmanı, ekibin gelecekteki fiziksel deney akışını doğrudan destekleyecek şekilde tasarlanmıştır:

```text
┌─────────────────────────┐
│ Bilinen Referans PCG    │ (Örn: PhysioNet / Doğrulanmış WAV)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Fantom Çalma Ünitesi    │ (Ses Kartı + Kalibre Aktüatör / Hoparlör)
└────────────┬────────────┘
             │ Akustik Yayılım & Doku Kuplajı
             ▼
┌─────────────────────────┐
│ Göğüs Parçası / Sensör  │ (PUI DMM-4026-B-I2S-R / Akustik Başlık)
└────────────┬────────────┘
             │ I2S Sayısal Akustik Veri (48 kHz, 24/32-bit)
             ▼
┌─────────────────────────┐
│ ESP32-S3 Sayısal Veri   │ (Semantic Hardware Packets)
└────────────┬────────────┘
             │ USB CDC / Seri Taşıma
             ▼
┌─────────────────────────┐
│ AuscultaForge Kaydedici │ (Full-rate SessionRecorder & Provenance JSON)
└────────────┬────────────┘
             │ Oturum WAV + Metaveri
             ▼
┌────────────────────────────────────────────────────────┐
│ Referans-Kayıt Doğrulama Laboratuvarı (Workbench)      │
│  - Zaman Hizalama (Delay & Cross-Correlation)          │
│  - Kazanç ve Hata Metrikleri (LS Gain, RMSE, NRMSE)    │
│  - Spektral Karşılaştırma & Tutarlılık (PSD, Coherence)│
│  - Makine Tarafından Okunabilir Rapor (JSON Export)    │
└────────────────────────────────────────────────────────┘
```

> **Mühendislik Bildirimi:** Yazılım laboratuvarı fiziksel donanım testlerinin halihazırda yapıldığını iddia etmez; donanım prototipi hazır olduğunda bu fiziksel deneyleri gerçekleştirecek analitik altyapıyı eksiksiz olarak sunar.

---

## 4. Doğrulama Matematiği ve Metrik Anlambilimi

AuscultaForge'un analiz katmanı, daha önce `pcg_core` kütüphanesinde geliştirilen ve matematiksel doğruluğu birim testlerle kanıtlanmış fonksiyonları (`pcg_core.validation`, `pcg_core.analysis`, `pcg_core.metrics`) yeniden kullanır. Matematiksel hesaplamalar asla React/TypeScript katmanında yinelenmez.

### 4.1. Açık Yeniden Örnekleme (Explicit Rational Resampling)
Referans dosya (örneğin 4000 Hz) ile yakalanan oturum (örneğin 48000 Hz) farklı örnekleme frekanslarına sahipse:
- `scipy.signal.resample_poly` kullanılarak yakalanan sinyal rasyonel faktörlerle referans frekansına yeniden örneklenir.
- Sistem bu durumu asla gizlemez; `alignment.resampled = true` ve etkin hedef frekans açıkça belgelenir.

### 4.2. Çapraz Korelasyon ve Gecikme Kestirimi (Time Alignment & Delay)
Akustik yayılım süresi, ADC dönüşüm gecikmesi ve işletim sistemi tamponları nedeniyle yakalanan sinyal gecikmeli gelir ($y[n] \approx g \cdot x[n - D] + w[n]$).
- Ayrık zamanlı çapraz korelasyon dizisi hesaplanır:
  $$R_{xy}[k] = \sum_{n} x[n] y[n + k]$$
- Tepe noktası ($k^* = \arg\max R_{xy}[k]$) gecikmeyi örnek (`delay_samples`) olarak verir.
- Milisaniye cinsinden gecikme:
  $$\text{delay\_ms} = \frac{\text{delay\_samples}}{f_s} \times 1000$$
- Sinyaller gecikme kadar kaydırılarak ortak örtüşme penceresine (`overlap`) kesilir.

### 4.3. Normalleştirilmiş Çapraz Korelasyon (NCC — Normalized Cross-Correlation)
Hizalanmış iki sinyalin dalga biçimi şekil benzerliğidir:
$$\text{NCC} = \frac{\sum x[n] y[n]}{\sqrt{\sum x[n]^2 \cdot \sum y[n]^2}}$$
Değer $0.0$ ile $1.0$ arasındadır; $1.0$ dalga biçimlerinin ölçek farkı hariç kusursuz aynı morfolojide olduğunu gösterir.

### 4.4. Kazanç Oranları ve En Küçük Kareler Kazancı (Gain Ratios & Least-Squares Gain)
Sistem üç farklı genlik oranı hesaplar:
1. **Tepe Kazanç Oranı (Peak Gain Ratio):** $\frac{\max |y|}{\max |x|}$.
2. **RMS Kazanç Oranı (RMS Gain Ratio):** $\frac{\text{RMS}(y)}{\text{RMS}(x)}$.
   > *Arayüzdeki Teknik Not:* RMS kazanç oranı toplamsal gürültüden (noise) doğrudan etkilenir; bu nedenle saf bir doğrusal kazanç kestiricisi değildir.
3. **En Küçük Kareler Kazancı ($g$ — Least-Squares Gain):**
   Hizalama sonrasında artık hata enerjisini $\|y - g \cdot x\|^2$ minimize eden optimal skaler:
   $$g = \frac{\sum x[n] y[n]}{\sum x[n]^2}$$
   Bu değer, akustik yolun ve donanım yükseltecinin gerçek doğrusal ölçekleme faktörüdür.

### 4.5. Hata ve Doğruluk Metrikleri (RMSE, NRMSE, SER)
- **RMSE (Root Mean Square Error):** Kestirim hatası $e[n] = y[n] - g \cdot x[n]$ dizisinin standart sapması/RMS değeri:
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{n=1}^N (y[n] - g \cdot x[n])^2}$$
- **NRMSE (Normalized RMSE):** Hatanın referans sinyalin RMS gücüne oranı:
  $$\text{NRMSE} = \frac{\text{RMSE}}{\text{RMS}(x)}$$
- **SER (Signal-to-Error Ratio, dB):** Referans sinyal gücünün kalan hata gücüne oranı:
  $$\text{SER (dB)} = 10 \log_{10} \left( \frac{\sum x[n]^2}{\sum (y[n] - g \cdot x[n])^2} \right)$$
  Yüksek SER (örn. $>25$ dB), donanımın sinyal formunu minimum gürültü ve minimum doğrusal olmayan bozulmayla aktardığını gösterir.

### 4.6. Spektral Karşılaştırma ve Bant Enerjisi Farkları (PSD & Band Energy)
Welch periyodogramı kullanılarak referans ve yakalanan sinyalin güç spektral yoğunlukları (PSD, dB/Hz) hesaplanır.
Ayrıca PCG için kritik 4 frekans bandındaki enerji oranları karşılaştırılır:
- **0–20 Hz (Alt-akustik / Hareket Artefaktı Bandı):** Sensör hareketleri, sürtünme ve kablo gürültüsü.
- **20–150 Hz (Temel Kalp Sesleri Bandı):** S1 ve S2 kalp seslerinin ana mekanik akustik enerjisi.
- **150–600 Hz (Üfürüm / Yüksek Frekans Bandı):** Patolojik sistolik/diyastolik üfürümler, klikler ve kapak açılma sesleri.
- **>600 Hz (Yüksek Akustik / Sensör Gürültü Bandı):** Sensör termal gürültüsü ve çevre gürültüsü.

### 4.7. Büyüklük-Karesi Tutarlılığı (Magnitude-Squared Coherence, $\gamma^2(f)$)
İki sinyalin frekansa bağlı doğrusal ilişkisini gösterir:
$$\gamma_{xy}^2(f) = \frac{|P_{xy}(f)|^2}{P_{xx}(f) P_{yy}(f)}$$
$\gamma^2(f) \in [0, 1]$ aralığındadır. Değerin 1'e yakın olması, o frekanstaki yakalanan sinyalin doğrudan referans sinyalin doğrusal bir cevabı olduğunu kanıtlar. Değerin düşmesi, o frekansta sisteme gürültü eklendiğini veya doğrusal olmayan harmonik bozulmalar olduğunu gösterir. Workbench, klinik PCG bandı olan 20–600 Hz arasındaki ortalama tutarlılığı (`mean_coherence_pcg_band`) özet metrik olarak raporlar.

---

## 5. Neden UI Grafikleri Seyreltilmiş (Decimated) Ama Metrikler Tam Sinyal Üzerinde Hesaplanır?

AuscultaForge'un temel mimari ilkelerinden biri **Hesaplama Doğruluğu ile Görsel İşleme Yükünün Ayrıştırılmasıdır**:

1. **Ortak Zaman Eksenli Görsel Seyreltme (`decimate_aligned_traces_shared_time`):**
   - 48 kHz örnekleme frekansında 15 saniyelik bir kayıt 720.000 adet 32-bit kayan noktalı sayı içerir.
   - Bu verinin ham haliyle React DOM'a veya SVG motoruna gönderilmesi, tarayıcının kilitlenmesine, saniyede 1–2 kareye düşmesine ve arayüzün yanıt vermemesine neden olur.
   - Referans, yakalanan ve hata sinyalleri bağımsız kutularda seyreltilip yapay bir ortak zaman eksenine oturtulmaz. Bunun yerine ortak kova sınırları belirlenir; her kovada hem referansın hem de yakalanan sinyalin uç noktaları (ekstrema: argmin/argmax) tespit edilir, bu indekslerin birleşimi kronolojik olarak sıralanır ve her üç sinyal de **birebir aynı zaman anlarında (`time_ms[i]`)** örneklenir. Böylece $e[i] = y_{\text{cap}}[i] - x_{\text{ref}}[i]$ eşitliği görsel seride de tam olarak korunur.
2. **Tam Hızlı Metrik Hesaplaması (Full-Rate DSP):**
   - Seyreltilmiş veri yalnızca ekran piksellerini beslemek içindir; **asla metrik hesabında kullanılmaz**.
   - Çapraz korelasyon, gecikme, kazanç, RMSE, SER ve tutarlılık metrikleri; 48 kHz / 4 kHz tam çözünürlüklü NumPy dizileri üzerinde $N$ elemanlı vektörel işlemlerle hesaplanır.
   - Bu sayede tarayıcı akıcı kalırken, rapordaki mühendislik metrikleri milimetrik/mikrosaniyelik matematiksel kesinliğe sahip olur.
3. **Akustik Uyaran vs. Zemin Gerçek Ayrımı:**
   - İçe aktarılan referans WAV, hoparlör/aktüatöre gönderilen **bilinen bir dijital uyarandır (reference stimulus / excitation)**.
   - Göğüs parçası ve mikrofona ulaşan ses; hoparlör transfer fonksiyonu, fantom dokusu akustik yayılımı ve mekanik kuplajdan geçer. Bu nedenle referans WAV, göğüs parçası noktasındaki kalibre edilmiş bir akustik "zemin gerçek" (ground truth) değil, tüm bu kanalın yanıtını ölçmek için kullanılan standart bir referans girdidir.

---

## 6. Neden Bu Değerler Mühendislik Metrikleridir, Asla Klinik Teşhis Değildir?

AuscultaForge sistemi bir tıbbi cihaz veya otomatik tanı yazılımı değildir; bir **fonokardiyografi donanım ve akustik mühendisliği geliştirme platformudur**.

Bu nedenle arayüzde ve raporlarda aşağıdaki kavramsal ayrım katı bir şekilde uygulanır:

| Yasaklanan Klinik Terimler | Kullanılan Mühendislik Terimleri |
| :--- | :--- |
| Sağlıklı / Hasta Kalp | Referans vs Yakalanan Sinyal (Reference vs Capture) |
| Klinik Kalite Skoru | Sinyal Benzerliği (NCC, SER dB) |
| Hastalık Teşhisi / Olasılığı | Spektral Karşılaştırma / Bant Enerji Dağılımı |
| Sensör Doğruluğu / Başarısı | Zaman Hizalama & En Küçük Kareler Kazancı ($g$) |
| İyi / Kötü Hasta Sinyali | Edinim Bütünlüğü (Acquisition Integrity, 0 drops) |

Bu metrikler bir hekime hastanın sağlığını söylemez; **donanım mühendisine sensörün, filtrelerin, ADC'nin ve akustik kuplajın referans sinyali ne kadar doğrusal ve gürültüsüz ilettiğini** gösterir.

---

## 7. Raporlama ve Dışa Aktarma Güvenliği (Report Persistence & Provenance)

Karşılaştırma sonuçları `experiments/analysis/<analysis_id>/comparison.json` konumunda saklanır. Rapor tasarımı katı güvenlik kurallarına uyar:
- **Mutlak Yol Yasaktır (No Absolute Machine Paths):** Raporda geliştiricinin bilgisayarına ait disk yolları (`C:\Users\...`) yer almaz. Referanslar göreceli kimliklerle (`asset_id`, `session_id`) ve SHA-256 özetleriyle tutulur.
- **Yol Aşımı Koruması (Path Traversal Protection):** `asset_id`, `session_id` ve `analysis_id` parametreleri güvenli karakter filtresinden (`^[a-zA-Z0-9_-]+$`) geçirilir; `..` veya dizin dışına çıkma girişimleri anında 400 hatasıyla reddedilir.
- **Girdi Doğrulama:** Yüklenen referans dosyalar yalnızca WAV formatında ve mono olmalıdır; bozuk, boş veya çok kanallı dosyalar net hata mesajıyla reddedilir.
- **Kapsamlı Kanıt Zinciri (Provenance):** Her raporda AuscultaForge sürümü, Git commit SHA'sı, Python, NumPy ve SciPy kütüphane sürümleri damgalanır.

---

## 8. Jüri ve Bitirme Savunması İçin 30 Saniyelik Özet (30-Second Defense Pitch)

> *"AuscultaForge projesinde stetoskop donanımımızın akustik performansını insan kulağının öznel algısına veya rastgele hasta kayıtlarına bırakmadık. Geliştirdiğimiz Doğrulama Laboratuvarı sayesinde; bilinen temiz bir PCG referans sinyalini akustik fantom üzerinden sensörümüze veriyor, kaydedilen oturumu referansla mikrosaniye hassasiyetinde otomatik olarak zaman hizalamasına tabi tutuyor; en küçük kareler kazancı, sinyal-hata oranı (SER), spektral güç yoğunluğu ve frekans tutarlılığı (coherence) gibi nicel mühendislik metrikleriyle donanımımızın akustik iletim kalitesini ölçülebilir ve tekrarlanabilir bir laboratuvar standardına bağlıyoruz."*
