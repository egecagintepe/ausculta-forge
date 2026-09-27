# 16 — Gerçek PCG Kayıtlarında Segmentasyon Doğrulaması ve Kıyaslama (Stage-C)

## 1. Bu Dokümanın Amacı ve Kapsamı

Bu doküman, AuscultaForge projesinde `feature/real-pcg-segmentation-validation` dalı ile hayata geçirilen **Stage-C Gerçek PCG Segmentasyonu Doğrulama ve Kıyaslama (Real PCG Segmentation Validation & Benchmarking)** çerçevesini açıklar.

Bu aşamanın temel araştırma sorusu şudur:
> *"AuscultaForge Springer LR-HSMM kalp sesi segmentasyonu uygulaması, bağımsız uzmanlarca etiketlenmiş gerçek PCG kayıtları üzerinde nasıl bir davranış sergilemektedir?"*

### Kesin Bilimsel ve Klinik Ayrım: Segmentasyon Doğrulaması Klinik Teşhis Değildir
Bu çalışma bir **zaman segmentasyonu doğrulamasıdır** (*temporal segmentation validation*).
- **Hastalık sınıflandırması (Disease classification) DEĞİLDİR.**
- **Üfürüm sınıflandırması (Murmur classification) DEĞİLDİR.**
- **Klinik tanı / teşhis (Clinical diagnosis) DEĞİLDİR.**
- **Klinik cihaz doğrulaması (Medical device validation) DEĞİLDİR.**
- **İnsan deneyi (Human experimentation) DEĞİLDİR.**

CirCor veri setinde bulunan üfürüm (murmur), klinik sonuç (outcome) veya demografik etiketler bu aşamada kesinlikle modele girdi olarak verilmez ve model bu etiketler üzerinden eğitilmez.

---

## 2. Birincil Gerçek Veri Seti: The CirCor DigiScope PCG Dataset (v1.0.3)

Doğrulama altyapısının birincil veri kaynağı, PhysioNet üzerinde açık erişimli olarak sunulan **The CirCor DigiScope Phonocardiogram Dataset** (Sürüm 1.0.3) veri tabanıdır.

- **Resmi DOI:** `10.13026/tshs-mw03`
- **Kaynak:** PhysioNet (`https://physionet.org/content/circor-heart-sound/1.0.3/`)
- **Resmi Boyut:** 1568 denek, 5272 kayıt, yaklaşık 558.9 MB uncompressed.
- **Veri Yapısı:** Her uygun kayıt için `.wav` (ham ses), `.hea` (başlık) ve `.tsv` (zaman aralığı durum etiketleri) zorunludur.
- **Dosya İsimlendirme Formatı:** `SUBJECTID_LOCATION.wav` (örn. `2530_AV.wav`, `2530_MV.wav`, `50782_MV_1.wav`). Sayısal ön ek deneğin (*subject*) tekil kimliğini belirtir.
- **Oskültasyon Konumları:** AV (Aort), MV (Mitral), PV (Pulmoner), TV (Triküspit) ve Phc (Prekordiyal).


### TSV Aralıkları ve Kritik "State 0" Anlambilimi
TSV dosyasındaki 3 sütun:
1. Başlangıç zamanı (saniye, `float`)
2. Bitiş zamanı (saniye, `float`)
3. Durum kodu (`int` $\in \{0, 1, 2, 3, 4\}$)

| Durum Kodu | Karşılık Gelen Durum | Doğrulama & Eğitim Anlambilimi |
| :---: | :--- | :--- |
| **0** | **UNANNOTATED / IGNORE** | **ETİKETLENMEMİŞ / BELİRSİZ BÖLGE. ASLA DİYASTOL OLARAK DEĞERLENDİRİLMEZ.** |
| **1** | **S1** | Birinci kalp sesi aralığı. |
| **2** | **SYSTOLE** | Sistol aralığı. |
| **3** | **S2** | İkinci kalp sesi aralığı. |
| **4** | **DIASTOLE** | Diyastol aralığı. |

> [!CAUTION]
> **Kritik Kural:** Durum 0 asla 5. bir fizyolojik durum veya Diyastol (Durum 4) olarak kabul edilemez. Durum 0 içeren kareler eğitimden hariç tutulur, çerçeve uyumu hesaplamasına katılmaz ve referans S1/S2 olayı üretmez.

---

## 3. Denek Tabanlı Veri Sızıntısını Önleme (Anti-Subject-Leakage)

Biyomedikal ses işleme çalışmalarında en sık yapılan metodolojik hata, aynı deneğe ait farklı konumlardan alınmış kayıtları (örneğin aynı çocuğun `12345_AV.wav`, `12345_MV.wav` ve `12345_PV.wav` kayıtlarını) rastgele eğitim ve test kümelerine dağıtmaktır. Bu durum, modelin deneğin akustik göğüs yapısını ezberlemesine ve yapay olarak şişirilmiş test sonuçlarına yol açar (*data leakage*).

AuscultaForge bu metodolojik hatayı kesin kurallarla engeller:
1. **Grup Değişkeni:** `subject_id` (dosya adındaki ilk sayısal blok).
2. **K-Fold Politikası:** 5 katlı denek gruplu çapraz doğrulama (*5-fold subject-grouped cross-validation*).
3. **Sert Kural:**
   $$\text{Train Subjects} \cap \text{Evaluation Subjects} = \emptyset$$
   Aynı deneğin hiçbir kaydı eğitim ve değerlendirme kümelerine bölünemez; hepsi bir arada aynı kümede kalır.
4. **Deterministik Tohum:** Bölümleme rastlantısal değişkenliği önlemek amacıyla sabit `seed=2026` ile gerçekleştirilir.

---

## 4. Model Eğitimi ve İnferens Ayrımı (Test-Time Separation)

CirCor veri seti doğrudan S1, sistol, S2 ve diyastol zaman aralıklarını sağladığından, EKG R-tepesi köprüsü yerine TSV aralıkları doğrudan 50 Hz referans durumlara dönüştürülür.

### İnferens Bütünlüğü İlkesi
- Değerlendirme aşamasında `segment_pcg_springer()` fonksiyonuna **yalnızca ham PCG ses dalgası** verilir.
- Referans etiketler, Viterbi kod çözme ve öznitelik çıkarma adımlarına **asla sızdırılamaz**.
- Referans etiketler yalnızca segmentasyon bittikten sonra tahmin edilen sınırlarla matematiksel karşılaştırma yapmak üzere kullanılır.

### Model İsimlendirme ve Demo Model Yasağı
- Gerçek CirCor etiketleriyle eğitilen modeller açıkça `auscultaforge_circor_springer_ref_v1_fold{k}` olarak adlandırılır.
- Sentetik 3-öznitelikli demo model (`springer_demo_3feature_v1`) gerçek veri kıyaslamasında **asla kullanılamaz**; seçildiği takdirde kıyaslama motoru çalışmayı derhal reddeder.

---

## 5. Olay Seviyesi Değerlendirme ve Tolerans Pencereleri (Event Evaluation)

Kalp seslerinin zamansal doğruluğu, tahmin edilen olaylar ile uzman etiketli referans olaylar arasındaki 1'e 1 eşleşme ile ölçülür.

### Olay Tanımı (Event Anchor)
- **STATE ONSET (Birincil Standart):** S1 olayı = S1 başlangıç zamanı; S2 olayı = S2 başlangıç zamanı.
- **SPRINGER_CONTEXT (İkincil / Opsiyonel):** S1 = S1 başlangıcı; S2 = S2 aralık merkezi.

### 1-to-1 Deterministik Eşleştirme (Dynamic Programming Sequence Matcher)
- Bir tahmin yalnızca tek bir referansla eşleşebilir.
- Bir referans birden fazla tahmin tarafından paylaşılamaz (tekrar eden tahminler False Positive sayılır).
- Eşleştirme, açgözlü (greedy) yaklaşımın alt-optimal bloklamalarını engellemek için **Dynamic Programming** ile iki öncelik hiyerarşisinde çözülür:
  1. Tolerans penceresi içindeki geçerli eşleşme sayısını (True Positive) maksimize etmek,
  2. Eşit TP durumunda toplam mutlak zamanlama hatasını minimize etmek.

### Tolerans Pencereleri ve Metrikler
Değerlendirme 5 sabit zaman toleransında ayrı ayrı raporlanır:
$$\tau \in \{20\text{ ms}, 40\text{ ms}, 60\text{ ms}, 80\text{ ms}, 100\text{ ms}\}$$

Her tolerans için:
- $\text{TP}$ (True Positive): Tolerans penceresi içinde eşleşen olaylar.
- $\text{FP}$ (False Positive): Referansı olmayan tahminler veya mükerrer tetiklemeler.
- $\text{FN}$ (False Negative): Tahmin edilemeyen referans olaylar.
- **Duyarlılık / Recall:** $\text{Sensitivity} = \frac{\text{TP}}{\text{TP} + \text{FN}}$
- **Kesinlik / Precision:** $\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$
- **F1 Skoru:** $\text{F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$

Raporlama; S1 olayları, S2 olayları ve Birleşik (Combined S1+S2) olarak bağımsız sunulur. Zayıf bir S2 performansı birleşik skor içinde gizlenemez.

---

## 6. Hayatta Kalma Yanlılığını Önleme: Uçtan-Uca ve Koşullu Başarı (Anti-Survivorship Bias)

Gerçek sinyallerde gürültü veya kayıt bozulması nedeniyle segmentasyon algoritması her kayıtta başarıyla sonuçlanmayabilir (`HEART_RATE_ESTIMATION_FAILED`, `SIGNAL_TOO_SHORT`, vb.).

Sadece başarılı kayıtları değerlendirmek, algoritmanın başarısız olduğu zor kayıtları sistemden silerek yapay bir "hayatta kalma yanlılığı" (*survivorship bias*) yaratır. Bu nedenle AuscultaForge iki açık performans görünümü sunar:

1. **END-TO-END METRICS (Birincil Mühendislik Kıyaslaması):**
   - Değerlendirme kümesindeki tüm kayıtları kapsar.
   - Segmentasyon başarısız olursa (`is_success = False`), tahmin kümesi **boş** kabul edilir.
   - Bu kayıttaki tüm gerçek S1 ve S2 referans olayları otomatik olarak **False Negative (FN)** yazılır.
   - Böylece algoritmanın sinyali işleyememe hatası doğrudan F1 skorunu düşürür.
2. **CONDITIONAL ON SUCCESS METRICS (İkincil İnceleme):**
   - Yalnızca algoritmanın `SUCCESS` döndüğü kayıtlarda hesaplanır.
   - Algoritmanın başarılı olduğu alt kümedeki dekoder sınır doğruluğunu anlamaya yarar.

---

## 7. 50 Hz Çerçeve Seviyesi Değerlendirme (State Metrics)

Olay seviyesi sınır tespitinin yanı sıra, 4 durumlu kardiyak döngünün tamamı 50 Hz zaman tabanında değerlendirilir:
- Yalnızca `evaluation_mask == True` (yani Durum 1, 2, 3, 4) olan kareler değerlendirilir. Durum 0 hariç tutulur.
- **$4 \times 4$ Karışıklık Matrisi (Confusion Matrix):** Satırlar referans durumlar, sütunlar tahmin edilen durumlardır.
- **Durum Bazında Precision, Recall ve F1:** S1, Sistol, S2 ve Diyastol için ayrı ayrı hesaplanır.
- **Makro Durum F1 (Macro State F1):** 4 durumun F1 skorlarının aritmetik ortalamasıdır.
- **Etiketli Kare Uyumu (Annotated-Frame Agreement):** Toplam doğru sınıflandırılan karelerin toplam etiketli karelere oranıdır. Bu metriğe asla genelleyici "klinik doğruluk" denilemez.

---

## 8. Zamanlama Hata Analizi (Timing Errors)

Doğru eşleşen ($\text{TP}$) olaylar için zamanlama sapması milisaniye (ms) cinsinden hesaplanır:
$$\Delta t_{\text{signed}} = t_{\text{predicted}} - t_{\text{reference}}$$
$$\Delta t_{\text{abs}} = |\Delta t_{\text{signed}}|$$

Raporlanan istatistikler:
- Ortalama ve medyan işaretli hata (*signed timing error*)
- Ortalama mutlak hata (MAE) ve medyan mutlak hata
- 25., 75. ve 95. yüzdelik (*percentile*) mutlak zamanlama hataları.

---

## 9. Toplulaştırma Düzeyleri (Micro, Macro-Record, Macro-Subject)

Çoklu kayıt içeren deneklerin genel skoru tek başına saptırmasını önlemek için:
- **Micro:** Tüm kayıtlardaki $\text{TP}, \text{FP}, \text{FN}$ değerleri doğrudan toplanıp tek bir küresel F1 hesaplanır.
- **Macro-Subject:** Her deneğin kendi kayıtları içindeki olayları toplanarak denek F1 skoru bulunur; ardından tüm deneklerin skorları eşit ağırlıkla ortalanır. Bir deneğin 4 kaydı, tek kaydı olan bir denekten 4 kat fazla ağırlığa sahip olamaz.

---

## 10. Oskültasyon Konumu Analizi (Location Breakdown)

AV, MV, PV, TV ve Phc konumları için kayıt sayısı, denek sayısı, kapsama oranı ve 100 ms toleranstaki F1 skorları tanımlayıcı (*descriptive*) olarak dökülür. Konumlar kesinlikle "en iyi" veya "en kötü" şeklinde sıralanamaz veya klinik üstünlük atfedilemez.

---

## 11. İkincil Veri Seti: CinC 2016 (DEFERRED_FORMAT_ADAPTER)

PhysioNet / Computing in Cardiology Challenge 2016 veri setinde elle düzeltilmiş resmi segmentasyon etiketleri, kardeş `.tsv`/`.csv` dosyaları olarak değil, `annotations/hand_corrected/training-a_StateAns/a0001_StateAns.mat` biçiminde MATLAB yapısında sunulmaktadır.
- Bu nedenle CinC 2016 adaptörü `DEFERRED_FORMAT_ADAPTER` olarak açıkça işaretlenmiştir.
- Resmi `*_StateAns.mat` ayrıştırıcısı eklenene kadar yanıltıcı bir ".tsv/.csv bulundu" iddiasından kaçınılır ve çapraz veritabanı testi bu gerekçeyle dürüstçe reddedilir.
- CinC 2016 sonuçları CirCor sonuçlarıyla asla birleştirilmez.

---

## 12. Literatür Performansı ile Karşılaştırma Sınırları

Springer et al. (2016) makalesinde raporlanan %95.63 F1 skoru:
- Farklı bir veri seti üzerinde,
- EKG R-tepesi ve T-dalgası bitiş referanslarıyla eğitilmiş,
- Farklı tolerans ve eşleştirme kuralları altında elde edilmiştir.

Bu nedenle CirCor sonuçlarının yanına makale skoru konularak "makale sonucunu geçtik" veya "makale sonucunu birebir tekrarladık" şeklinde doğrudan karşılaştırma yapılamaz. Dokümantasyonda iki sonuç kesin bir sınırla ayrı tutulur.

---

## 13. 30 Saniyelik Tez Savunması Cevabı (Defense Pitch)

> *"Segmentasyon algoritmamızı, S1, sistol, S2 ve diyastol aralıkları uzmanlarca bağımsız etiketlenmiş gerçek PCG kayıtları üzerinde doğruyoruz. Veri sızıntısını önlemek amacıyla tekil kayıtlar yerine denekleri eğitim ve değerlendirme kümelerine ayırıyoruz. Değerlendirmede 20 ila 100 milisaniye arasındaki zamansal toleranslarda olay seviyesi F1 skorlarını, durum uyumunu ve başarısız kayıtları da içeren uçtan-uca kapsama oranını raporluyoruz. Algoritmaya kestirim anında referans etiketler asla verilmemektedir."*

---

## 14. Bilimsel Araştırma Durum Tablosu (Research Status Table)

| Aşama / Algoritmik Bileşen | Durum Tanımı | Doğrulama Seviyesi |
| :--- | :--- | :--- |
| **Springer Referans Öznitelik Çıkarımı** | IMPLEMENTED | Sentetik test edilmiş + Referans eşdeğerliği kontrol edilmiş |
| **CirCor Veri Seti Adaptörü & Ayrıştırıcı (v1.0.3)** | IMPLEMENTED | `.wav`, `.tsv`, `.hea` + Konum doğrulama + Tarama muhasebesi tamamlandı |
| **Denek Gruplu Bölümleyici (Anti-Leakage)** | IMPLEMENTED | %0 denek sızıntısı matematiksel olarak kanıtlanmış |
| **Gerçek LR Modeli Eğitimi (Fold-based)** | IMPLEMENTED | Gerçek CirCor denekleri üzerinde fold modelleri eğitilmiş |
| **Uçtan-Uca & Koşullu Değerlendirme Motoru** | IMPLEMENTED | DP sekans eşleştirici + Hayatta kalma yanlılığı engellenmiş |
| **CirCor Gerçek Veri Pilotu (Real Pilot)** | REAL_DATA_PILOT | 50 denek üzerinde gerçek WAV ve TSV ile icra edildi |
| **Tam CirCor Kıyaslaması (Full 5272 Records)** | NOT YET EXECUTED | Çalışma süresi deneyi olarak bir sonraki adımda icra edilebilir |
| **CinC 2016 Çapraz Veritabanı Değerlendirmesi** | DEFERRED_FORMAT_ADAPTER | `*_StateAns.mat` format ayrıştırıcısı ertelendi |
| **Springer MATLAB Sayısal Birebir Eşdeğerliği** | NOT EXTERNALLY VALIDATED | Yalnızca MATLAB kahini ile doğrudan doğrulanabilir |
| **Klinik Tanı Geçerliliği** | NOT CLAIMED | Teşhis veya klinik geçerlilik iddiası bulunmamaktadır |
