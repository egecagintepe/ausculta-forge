# 15 — Springer LR-HSMM Kalp Sesi Segmentasyonu

## 1. Bu Dokümanın Amacı ve Kapsamı

Bu doküman, AuscultaForge projesinde `feature/springer-lr-hsmm-segmentation` dalı ile hayata geçirilen **kaynak-sadık Springer Lojistik Regresyon + Saklı Yarı-Markov Model (LR-HSMM) kalp sesi segmentasyonu** altyapısını açıklar.

Hedeflenen çevrimsel durum dizisi:

$$\text{S1} \longrightarrow \text{Sistol} \longrightarrow \text{S2} \longrightarrow \text{Diyastol} \longrightarrow \text{S1}$$

### Kesin Bilimsel ve Klinik Ayrım: Segmentasyon Teşhis Değildir
Bu modül bir **akustik zaman segmentasyonu** (*temporal acoustic segmentation*) aracıdır.
- **Teşhis (Diagnosis) DEĞİLDİR.**
- **Patoloji sınıflandırması (Pathology classification) DEĞİLDİR.**
- **Hastalık tespiti (Disease detection) DEĞİLDİR.**
- **Klinik karar destek sistemi (Clinical decision support) DEĞİLDİR.**
- **Klinik altın standart (Ground truth) DEĞİLDİR.**
- **Bir yapay zeka sağlık skoru (AI health score) DEĞİLDİR.**

Model çıktısı olarak işaretlenen S1 ve S2 sınırları, yalnızca akustik dalga biçiminden istatistiksel modellerle türetilmiş zamansal tahminlerdir. Asla "normal", "anormal", "sağlıklı" veya "hastalık" etiketi üretmez.

---

## 2. Kaynak Hiyerarşisi ve Literatür Temeli

Bu çalışma aşağıdaki kaynak hiyerarşisine tam uyumlu olarak inşa edilmiştir:

1. **Birincil Bilimsel Makale (R006):**
   - David B. Springer, Lionel Tarassenko, Gari D. Clifford
   - *"Logistic Regression-HSMM-based Heart Sound Segmentation"*
   - IEEE Transactions on Biomedical Engineering, DOI: 10.1109/TBME.2015.2475278 (2016).
2. **Resmi Referans Uygulama (PhysioNet HSS v1.0):**
   - David Springer, PhysioNet: *"Logistic Regression-HSMM-based Heart Sound Segmentation"*, Version 1.0.
3. **Arka Plan Durasyon Modeli (R005):**
   - Schmidt et al. (2010), *"Duration-dependent HMM segmentation"*.
4. **Bağımsız Değerlendirme (R007):**
   - Liu et al., *"Multi-database evaluation of the HSMM algorithm"*.

---

## 3. Lisanslama ve GPL Bağımsızlığı İlkesi

PhysioNet üzerindeki resmi Springer MATLAB kod tabanı **GNU General Public License (GPL)** ile lisanslanmıştır.

AuscultaForge fikri mülkiyet ve lisans temizliğini korumak için:
- GPL lisanslı MATLAB kodları **asla doğrudan veya satır satır Python'a kopyalanmamıştır / tercüme edilmemiştir**.
- Matematiksel yöntem; hakemli makale denklemleri, belgelenmiş parametre tabloları ve açık istatistiksel tanımlar temel alınarak sıfırdan bağımsız bir Python mimarisiyle kodlanmıştır.
- Harici PhysioNet MATLAB kodu yalnızca bir **Geliştirme Kahini (Development Oracle)** olarak davranışsal karşılaştırma amacıyla referans alınmıştır; depoya hiçbir MATLAB dosyası (`.m`, `.mat`, MEX/C) veya harici veri seti eklenmemiştir (*no vendoring*).

---

## 4. Makale (Paper) ve PhysioNet Referans Kodu Arasındaki Farklar

Bilimsel dürüstlük gereği, yayınlanan makale metni (*prose*) ile PhysioNet'te paylaşılan resmi MATLAB referans kodunun birebir özdeş olmadığı açıkça belgelenmiştir. Bu farklar kod tabanında iki ayrı açık profil olarak tanımlanmıştır:

| Özellik | `SPRINGER_PHYSIONET_REFERENCE_V1` | `SPRINGER_PAPER_4FEATURE_V1` |
| :--- | :--- | :--- |
| **Bant Geçiren Filtre** | 25–400 Hz sıfır fazlı Butterworth (2. derece tasarım, filtfilt) | Makale öznitelik bölümünde belirtilmemiştir; 1000 Hz polifaz resampling |
| **Schmidt Spike Giderme** | Aktif (~500 ms pencereler, 3× medyan eşik) | Makale ana metninde açıkça belirtilmemiştir (opsiyonel) |
| **Öznitelik Sayısı** | 3 öznitelik (Homomorfik, Hilbert, PSD) varsayılan | 4 öznitelik (Homomorfik, Hilbert, PSD, Dalgacık) |
| **Dalgacık (Wavelet)** | Varsayılan olarak kapalı (`include_wavelet = false`) | Makalede en yüksek başarıyı veren modelde açık (`rbio3.9`, seviye 3) |
| **PSD Hesaplama Modu** | 40–60 Hz frekans kutularının toplamı | 40–60 Hz aralığındaki ortalama PSD değeri |
| **Çıkış Hızı** | 50 Hz öznitelik akışı | 50 Hz öznitelik akışı |

Kullanıcı veya analist hangi profilin çalıştırıldığını sonuç nesnesindeki `profile_id` üzerinden kesin olarak görür; profiller sessizce birbirine karıştırılmaz.

---

## 5. Sinyal Temsili ve Hız Hiyerarşisi

AuscultaForge'un çok katmanlı sinyal temsili hiyerarşisi korunmuştur:

```text
1. Edinim Sinyali (Acquisition Signal, örn. 48.000 Hz veya 4.000 Hz)
   │
   ▼  [resample_analysis_signal: rasyonel polifaz anti-aliased filtreleme]
2. Springer Analiz Sinyali (Analysis Signal, 1.000 Hz)
   │
   ▼  [Öznitelik çıkarımı: 8 Hz alçak geçiren homomorfik, Hilbert, 40-60 Hz PSD, Dalgacık]
   ▼  [50 Hz'e desimasyon & kayıt bazında z-score normalizasyonu]
3. HSMM Gözlem Akışı (Feature Stream, 50 Hz)
   │
   ▼  [Lojistik regresyon emisyonları & Genişletilmiş Viterbi kod çözümü]
4. Durum Dizisi (State Sequence, 50 Hz) & Zaman Aralıkları (State Intervals, saniye cinsinden)
   │
   ▼  [Görselleştirme için tepeleri koruyarak ≤ 600 noktaya desimasyon]
5. Görüntüleme Temsili (Display Representation)
```

---

## 6. Schmidt İteratif Spike Giderme Algoritması

PCG kayıtlarında steteskopun hastanın cildine teması veya hareket kaynaklı aşırı genlikli ani darbeler (spikes), filtrelerin ve Hilbert dönüşümünün dinamik aralığını bozabilir.

Referans Schmidt/Springer algoritması şu adımlarla çalışır:
1. Sinyal yaklaşık 500 ms'lik (500 örnek @ 1000 Hz) pencerelere bölünür.
2. Her penceredeki maksimum mutlak genlik hesaplanır: $M_w = \max |x_w|$.
3. Herhangi bir pencerenin tepesi, pencerelerin medyanının 3 katını aşıyorsa ($\max M_w > 3 \times \text{median}(M)$):
   - En büyük tepeye sahip pencere ve tepenin tam konumu bulunur.
   - Tepenin solundaki ve sağındaki en yakın **sıfır geçişleri** (*zero-crossing boundaries*) tespit edilir.
   - Bu sınırların arasındaki spike aralığı sıfırlanır (veya çok küçük gürültüyle doldurulur).
   - Pencere maksimumları yeniden hesaplanır ve döngü tekrarlanır.
4. **Güvenlik Korumaları:** Sonsuz döngüleri önlemek için maksimum 50 iterasyon sınırı konmuştur; sessiz/düz sinyallerde sıfıra bölme engellenmiştir.

---

## 7. Dört Akustik Zarf Özniteliği

### A. Homomorfik Zarf (Homomorphic Envelope)
Makale ve referans kodun önerdiği şekilde:
1. Analitik sinyal hesaplanır: $z(t) = x(t) + j \cdot \mathcal{H}\{x(t)\}$
2. Genlik elde edilir: $m(t) = |z(t)|$
3. Sayısal kararlılık için logaritması alınır: $y(t) = \ln(\max(m(t), 10^{-12}))$
4. Log genlik, ~8 Hz kesim frekanslı 1. derece Butterworth filtresi ile ileri-geri sıfır fazlı (`filtfilt`) süzülür.
5. Üstel dönüşümle zaman domenine dönülür: $e_{\text{homo}}(t) = \exp(y_{\text{filt}}(t))$

### B. Hilbert Zarfı (Hilbert Envelope)
Analitik sinyalin anlık genliği doğrudan kullanılır:
$$e_{\text{hilbert}}(t) = |x(t) + j \cdot \mathcal{H}\{x(t)\}|$$

### C. PSD Zarfı (Short-Time PSD Feature, 40–60 Hz)
Kalp seslerinin temel frekans bileşenleri çoğunlukla 40–60 Hz arasında yoğunlaşır.
- Pencere: 50 ms Hamming penceresi
- Örtüşme: %50
- Frekans ızgarasında 40–60 Hz bandındaki güç yoğunluğu hesaplanır ve 50 Hz zaman eksenine enterpole edilir.

### D. Dalgacık Zarfı (Wavelet Feature)
Makalede en yüksek skoru veren Level-3 ayrışımı:
- Dalgacık ailesi: Reverse Biorthogonal 3.9 (`rbio3.9`) veya Daubechies 10 (`db10`).
- Uygulama: `pywt.wavedec` ile 3 seviyeli DWT uygulanır. Yalnızca 3. seviye detay katsayıları (`cD3`) tutulup diğerleri sıfırlanarak `pywt.waverec` ile 1000 Hz zaman ızgarasında tam hizalı olarak yeniden oluşturulur. Ardından mutlak genliğin 8 Hz alçak geçiren zarfı alınır. Bu sayede öznitelikler arasında faz kayması yaşanmaz.

---

## 8. Kalp Hızı ve Durasyon İstatistiği

Schmidt/Springer algoritması, önceden işlenmiş 1000 Hz sinyalinin homomorfik zarfının normalleştirilmiş **özilişkisi** (*normalized autocorrelation*) üzerinden çalışır:

1. 500 ms ile 2000 ms arasındaki gecikme (*lag*) aralığında (30–120 BPM fizyolojik sınırlar) en yüksek özilişki tepesi aranır:
   $$\text{BPM} = \frac{60}{T_{\text{cycle}}}$$
2. Sistolik aralık ($T_{\text{sys}}$), 200 ms ile $T_{\text{cycle}} / 2$ arasındaki en belirgin tepe üzerinden kestirilir.
3. 50 Hz gözlem hızında 4 durumun Gauss durasyon parametreleri hesaplanır:
   - **S1**: Ortalama $\mu = 122\text{ ms}$, standart sapma $\sigma = 22\text{ ms}$
   - **S2**: Ortalama $\mu = 94\text{ ms}$, standart sapma $\sigma = 22\text{ ms}$
   - **Sistol**: Ortalama $\mu = T_{\text{sys}} - 122\text{ ms}$, $\sigma \approx 25\text{ ms}$
   - **Diyastol**: Ortalama $\mu = T_{\text{cycle}} - T_{\text{sys}} - 94\text{ ms}$, Schmidt formülü ile belirlenen $\sigma$

Fizyolojik veya matematiksel olarak imkansız durumlarda (örn. negatif sistol süresi, yetersiz sinyal uzunluğu), sistem hayali bir değer üretmez ve `SEGMENTATION_PARAMETERS_INVALID` veya `HEART_RATE_ESTIMATION_FAILED` hatası ile sonlanır.

---

## 9. Lojistik Regresyon ve Bayes Düzeltmeli HSMM

Klasik HMM durum sürelerini geometrik (hafızasız) kabul ederken, **Saklı Yarı-Markov Model (HSMM)** her durumun süresini açık bir olasılık dağılımı ($p_i(d)$) ile modeller.

1. **Lojistik Regresyon (Bire Karşı Diğerleri — One-vs-Rest):**
   Her 4 durum için (S1, Sistol, S2, Diyastol) ayrı bir ikili lojistik regresyon modeli eğitilir:
   $$P(\text{state} = i \mid \mathbf{x}) = \sigma(\mathbf{w}_i^T \mathbf{x} + b_i)$$
   Sınıf dengesizliği, negatif örneklerin deterministik rastgele tohumla alt-örneklenmesi (*subsampling*) ile giderilir.
2. **Bayes Emisyon Düzeltmesi:**
   HSMM durum geçişlerinde gözlem olasılığı $P(\mathbf{x} \mid \text{state} = i)$ değerine ihtiyaç duyar:
   $$P(\mathbf{x} \mid \text{state} = i) = \frac{P(\text{state} = i \mid \mathbf{x}) \cdot P(\mathbf{x})}{P(\text{state} = i)}$$
   Burada $P(\mathbf{x})$, tüm gözlemlerin çok değişkenli normal dağılımı ($\mathcal{N}(\boldsymbol{\mu}, \boldsymbol{\Sigma})$) olarak modellenir.

---

## 10. Genişletilmiş Viterbi Algoritması (Extended Viterbi)

Bir steteskop kaydının tam olarak S1 başlangıcında başlaması veya diyastolün tam sonunda bitmesi beklenemez. Sıradan Viterbi algoritması durumları sınırda kesmeye zorlarken, **Genişletilmiş Viterbi (Extended Viterbi)**:

- Kayıt başında kısmi olarak başlamış bir durumu (örn. diyastolün ortasında başlayan kayıt),
- Kayıt sonunda henüz tamamlanmamış bir durumu (örn. sistolün ortasında kesilen kayıt)

doğal olarak destekler. Hipotezlenen durum sürelerinin sınırların dışına taşmasına izin verilirken, emisyon puanı yalnızca kayıtta mevcut olan gerçek gözlem çerçeveleri üzerinden toplanır.

### Hesaplama Karmaşıklığı ve Önek Toplamları (Prefix Sums)
Her çerçeve ve her olası süre $d \in [d_{\min}, d_{\max}]$ için emisyon logaritmasını tekrar tekrar toplamak $O(T \cdot S \cdot D^2)$ karmaşıklık yaratır. AuscultaForge uygulamasında emisyon logaritmalarının kümülatif toplam dizisi (**prefix sums**) tutularak:
$$\sum_{t=t_0}^{t_1} \ln b_i(\mathbf{x}_t) = \text{cum\_log\_b}[t_1 + 1] - \text{cum\_log\_b}[t_0]$$
formülüyle herhangi bir aralık puanı $O(1)$ zamanda hesaplanır. Bu sayede algoritma saf Python/NumPy ortamında milisaniyeler içinde tamamlanır.

---

## 11. 30 Saniyelik Tez Savunma Yanıtı

> *"Springer LR-HSMM yöntemi, ham PCG sinyalini önce dört farklı zarf özniteliğine dönüştürür. Lojistik regresyon, bu özniteliklerden her kardiyak durumun anlık olasılığını kestirir. Yarı-Markov modeli (HSMM) ise S1, sistol, S2 ve diyastolün beklenen fizyolojik sürelerini ve çevrimsel geçiş sırasını zorunlu kılar. Genişletilmiş Viterbi kod çözücü, kaydın bir durumun ortasında başlayıp bitebileceğini de hesaba katarak en olası küresel durum dizisini logaritmik uzayda deterministik olarak çözer."*

---

## 12. Bilimsel Uygulama ve Doğrulama Durum Tablosu

| Bileşen / İddia | Durum Seviyesi | Açıklama |
| :--- | :--- | :--- |
| **Homomorfik Zarf (8 Hz filtfilt)** | `IMPLEMENTED` & `TESTED` | Epsilon korumalı logaritma, sıfır fazlı süzme, 9 birim testi ile doğrulandı |
| **Hilbert Zarfı** | `IMPLEMENTED` & `TESTED` | Analitik sinyal genliği, deterministik testlerle doğrulandı |
| **PSD Özniteliği (Paper vs Ref)** | `IMPLEMENTED` & `TESTED` | İki modun farklılıkları ve frekans ızgarası test edildi |
| **Dalgacık Zarfı (rbio3.9)** | `IMPLEMENTED` & `TESTED` | PyWavelets tabanlı seviye 3 rekonstrüksiyon tam zaman hizalı |
| **Schmidt Spike Giderme** | `IMPLEMENTED` & `TESTED` | Sıfır geçişi tespiti, 50 iterasyon sınırı, tek ve çoklu spike testleri |
| **Schmidt Kalp Hızı Kestirimi** | `IMPLEMENTED` & `TESTED` | 60, 75, 100 BPM sentetik PCG üzerinde tolerans dahilinde doğrulandı |
| **Durasyon Dağılımları (50 Hz)** | `IMPLEMENTED` & `TESTED` | Referans denklemleri el hesaplamalarıyla çapraz test edildi |
| **Genişletilmiş Viterbi Kod Çözümü** | `IMPLEMENTED` & `TESTED` | Kısmi sınır durumları (başta ve sonda yarım durumlar) başarıyla test edildi |
| **MATLAB İle Birebir Sayısal Denklik** | `REFERENCE_ORACLE_NOT_EXECUTED` | Harici MATLAB lisansı/çalıştırma ortamı mevcut olmadığından ikili denklik iddia edilmemiştir |
| **Makaledeki %95.63 F1 Başarımı** | `SOURCE SUPPORTED` | Yalnızca makalenin kendi veri seti sonucudur; AuscultaForge'un klinik başarımı olarak iddia edilemez |
