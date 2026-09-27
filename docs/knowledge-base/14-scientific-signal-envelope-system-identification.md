# 14 — Bilimsel Sinyal Karakterizasyonu, Zarf Laboratuvarı ve Sistem Tanılama Temeli

## 1. Bu Dokümanın Amacı

Bu doküman, `feature/scientific-signal-envelope-systemid-foundation` milestone'unda eklenen **bilimsel sinyal analiz katmanını** açıklar. Bu katman üç temel mühendislik yeteneği sunar:

1. **Sinyal Kalitesi Karakterizasyonu** (*Signal Quality Characterization*)
2. **Deterministik Zarf Laboratuvarı** (*Envelope Lab — Stage A*)
3. **SISO Sistem Tanılama Temeli** (*System Identification Foundation — H1 FRF*)

Bu milestone'un amacı etkileyici matematik eklemek **DEĞİLDİR**. Amaç; fantom deneyleri, referans/yakalama karşılaştırmaları, deterministik PCG öznitelik araştırması, tekrarlanabilirlik çalışmaları ve gelecekteki Springer LR-HSMM çalışması için **küçük, savunulabilir ve tam test edilmiş** bir mühendislik analiz katmanı oluşturmaktır.

---

## 2. Mimari Konum: Bilimsel Katman Nerededir?

Bilimsel analiz katmanı, `pcg_core/scientific/` modülünde bulunur ve mevcut AuscultaForge üçlü sinyal temsili modeline (*Architectural Triad*) uyar:

```text
Donanım / Dosya
       │
       ▼
  SampleBlock / Float32 Dizisi
       │
       ▼
  Edinim Temsili (Acquisition Signal)
       │  ← Bilimsel katman buradaki tam-hız dizileri tüketir
       ▼
  Analiz Sinyali (Analysis Signal) — profil filtreleri uygulanmış
       │
       ▼
  Bilimsel Motorlar (Scientific Engines)
       │
       ▼
  Sınırlandırılmış Görüntüleme Temsili (Display Representation, ≤ 600 nokta)
```

**Kesin Kural:** Bilimsel metrikler **asla** görüntüleme sınırları (display bounds) nedeniyle bozulmuş diziler üzerinde hesaplanmaz. Tüm nicel hesaplamalar tam hızlı (full-rate) analiz sinyalleri üzerinde yapılır.

---

## 3. Modül Yapısı ve Dosya Haritası

```text
software/pcg_core/scientific/
├── __init__.py           # Public API: tüm modelleri ve fonksiyonları dışa aktarır
├── models.py             # JSON-safe veri yapıları ve versiyonlu yapılandırma şemaları
├── signal_quality.py     # Skaler sinyal kalitesi metrikleri (RMS, Peak, CF, ZCR, FS hits)
├── spectral.py           # Welch PSD motoru ve rasyonel yeniden örnekleme
├── envelopes.py          # Hilbert, Moving RMS, TKEO, PSD-band zarfları
└── system_id.py          # SISO H1 FRF, coherence, auto/cross-spectra
```

### Test Dosyaları

```text
software/tests/
├── test_scientific_signal_quality.py  # 11 birim testi
├── test_scientific_spectral.py        # Welch PSD doğrulama testleri
├── test_scientific_envelopes.py       # Zarf algoritmaları testleri
├── test_scientific_system_id.py       # H1 FRF ve coherence testleri
└── test_scientific_api.py             # API entegrasyon testleri (fastapi gerektirir)
```

---

## 4. Sinyal Kalitesi Karakterizasyonu

### 4.1 Nedir?

`compute_signal_quality()` fonksiyonu, tam hızlı analiz dizileri üzerinde deterministik skaler metrikler üretir:

| Metrik | Formül / Tanım | Birim |
|--------|----------------|-------|
| **RMS** | $x_{\text{rms}} = \sqrt{\frac{1}{N}\sum_{n=0}^{N-1} x[n]^2}$ | Normalize genlik (FS) |
| **Peak Absolute** | $\max\|x[n]\|$ | Normalize genlik (FS) |
| **Peak-to-Peak** | $\max(x) - \min(x)$ | Normalize genlik (FS) |
| **Crest Factor** | $CF = \|x_{\text{peak}}\| / x_{\text{rms}}$ | Boyutsuz |
| **Digital FS Utilization** | Tepe genlik / 1.0 FS | Boyutsuz [0, 1] |
| **Digital Saturation Count** | $\|x[n]\| \geq 0.999$ olan örnek sayısı | Tamsayı |
| **Zero-Crossing Rate** | DC çıkarılmış sinyalde işaret değişim oranı | Boyutsuz |

### 4.2 Ne DEĞİLDİR?

- **Sayısal doygunluk (digital saturation)** fiziksel akustik aşırı yüklenme (acoustic overload) kanıtı **DEĞİLDİR.** Mikrofonun akustik üst sınır noktası (AOP) kalibre edilmemiştir.
- **Zero-crossing rate** güvenilir bir kalp sesi kalitesi sınıflandırıcısı veya S1/S2 dedektörü **DEĞİLDİR.**
- Keyfi bileşik "kalite skoru" (ör. 85/100) kullanılmaz; farklı fiziksel arıza modlarını gizler.

### 4.3 Kod Referansı

- Fonksiyon: `pcg_core.scientific.signal_quality.compute_signal_quality()`
- Model: `pcg_core.scientific.models.SignalCharacterizationResult`
- Yapılandırma: `pcg_core.scientific.models.SignalQualityConfig`

---

## 5. Welch Güç Spektral Yoğunluğu (PSD) Motoru

### 5.1 Nedir?

`compute_welch_psd()` fonksiyonu, SciPy'nin `scipy.signal.welch()` API'sini kullanarak pencerelenmiş, örtüşen segmentlerle ortalamalı periodogram hesaplar.

**Varsayılan Parametreler:**
- Pencere: Hann
- Örtüşme (Overlap): %50
- Ölçekleme: `density` → birim: `normalize_amplitude² / Hz` (boyutsuz FS²/Hz)
- Detrending: `constant` (DC çıkarma)

### 5.2 Kritik Terminoloji Ayrımları

| Doğru Terim | Yanlış/Aşırı İddia |
|-------------|---------------------|
| Frekans adımı (frequency-bin spacing): $\Delta f = f_s / N_{\text{FFT}}$ | "Spektral çözünürlük" olarak **adlandırılmaz** |
| Sıfır ekleme (zero-padding): DTFT enterpolasyonu | "Yeni fiziksel çözünürlük bilgisi" olarak **adlandırılmaz** |
| Bağıl dB ($\text{dB re } 1.0\, \text{FS}^2/\text{Hz}$) | dB SPL olarak **adlandırılmaz** |

### 5.3 Eşdeğer Gürültü Bant Genişliği (ENBW)

ENBW, kullanılan pencere fonksiyonunun frekans sızıntısını (leakage) dengeleyerek tepe noktasını ne kadar genişlettiğini ölçer. Hann penceresi için $\text{ENBW} \approx 1.50 \cdot \Delta f$.

### 5.4 Analiz Yeniden Örneklemesi

`resample_analysis_signal()` fonksiyonu, 48 kHz edinim sinyalini `scipy.signal.resample_poly()` ile rasyonel çok fazlı (polyphase) filtreden geçirerek güvenli biçimde hedef hıza (varsayılan 1000 Hz) indirir.

### 5.5 Kod Referansı

- Fonksiyon: `pcg_core.scientific.spectral.compute_welch_psd()`
- Model: `pcg_core.scientific.models.SpectralAnalysisResult`
- Yapılandırma: `pcg_core.scientific.models.WelchConfig`

---

## 6. Zarf Laboratuvarı (Envelope Lab — Stage A)

### 6.1 Uygulanan Algoritmalar

**1. Hilbert Dönüşümü Zarfı (Analytic Signal Magnitude)**

$$e(t) = |x(t) + j \cdot \mathcal{H}\{x(t)\}|$$

- Sürekli zaman-domeni zarf çıkarımı; grup gecikmesi (group delay) bozulması yoktur.
- Tepe noktaları akustik burst enerji yoğunlaşmalarını işaret eder.
- Fonksiyon: `compute_hilbert_envelope()`

**2. Kayan RMS Zarfı (Moving RMS Energy Envelope)**

$$e_{\text{rms}}[n] = \sqrt{\frac{1}{W}\sum_{k=0}^{W-1} x[n-k]^2}$$

- Varsayılan pencere süresi: 20 ms (özelleştirilebilir).
- Fonksiyon: `compute_moving_rms_envelope()`

**3. Teager-Kaiser Enerji Operatörü (TKEO)**

$$\Psi[x[n]] = x[n]^2 - x[n-1] \cdot x[n+1]$$

- Anlık genlik VE anlık frekansa eş zamanlı duyarlıdır.
- Sınır politikası: `replicate` (edge padding).
- **DENEYSELDİR.** TKEO tepesi otomatik olarak S1 veya S2 kalp sesi **DEĞİLDİR.**
- Fonksiyon: `compute_tkeo()`

**4. PSD-Band Zarfı (Springer 40–60 Hz Research Feature)**

- Kısa zamanlı pencerelenmiş enerji: 50 ms Hamming penceresi, %50 örtüşme.
- Springer et al. (2016) PCG segmentasyon literatüründeki deterministik spektral öznitelik akışını yeniden üretir.
- **40–60 Hz evrensel bir PCG standart bandı DEĞİLDİR.**
- Fonksiyon: `compute_psd_band_envelope()`

### 6.2 Homomorfik Zarf Durumu

Homomorfik zarf çıkarımı (log → filter → exp) arayüzü tanımlanmış ancak algoritmik uygulaması **Stage-B'ye ertelenmiştir**. Neden: birincil kaynak parametreleştirmesi (Schmidt et al., R005) henüz doğrulanmamıştır. Küçük ve doğru bir milestone, doğrulanmamış bir sezgisellikten tercih edilir.

### 6.3 Kod Referansı

- Modül: `pcg_core.scientific.envelopes`
- Bileşik fonksiyon: `compute_envelope_lab()` — tüm aktif zarfları hesaplar
- Model: `pcg_core.scientific.models.EnvelopeLabResult`, `EnvelopeSeries`
- Yapılandırma: `pcg_core.scientific.models.EnvelopeLabConfig`

---

## 7. SISO Sistem Tanılama Temeli (H1 FRF)

### 7.1 Matematiksel Çerçeve

Bu modül, klasik H1 kestirici modeli altında tek-giriş tek-çıkış (SISO) en-iyi-doğrusal frekans cevabı tahmini gerçekleştirir:

**Model:**
$$y[n] = (h * x)[n] + v[n]$$

Burada $x[n]$ bilinen referans uyarımı, $y[n]$ yakalanan cevap ve $v[n]$ girişle ilişkisiz gürültüdür.

**H1 Kestirici:**
$$H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$$

**SciPy CSD Konvansiyonu:**
`scipy.signal.csd(x, y)` → $\langle X^*(f) \cdot Y(f) \rangle = S_{xy}(f)$

**Ordinary Magnitude-Squared Coherence:**
$$\gamma_{xy}^2(f) = \frac{|S_{xy}(f)|^2}{S_{xx}(f) \cdot S_{yy}(f)}, \quad 0 \leq \gamma_{xy}^2 \leq 1$$

### 7.2 Uyarılmış Frekans Enerji Maskesi (Excited-Frequency Energy Mask)

Koherans ve FRF hesaplamaları yalnızca giriş uyarımının yeterli enerjiye sahip olduğu frekanslarda fiziksel olarak anlamlıdır. Açık bir maske oluşturulur:

$$\text{mask}(f) = (f \geq f_{\text{low}}) \wedge (f \leq f_{\text{high}}) \wedge (10\log_{10}(G_{xx}(f) / \max(G_{xx})) \geq \text{threshold\_dB})$$

`mean_coherence_over_excited_band` skaler özet metriği, kesinlikle bu maskelenen bölgede hesaplanır.

### 7.3 Koherans Neyi İSPATLAMAZ

> **Yüksek koherans fiziksel nedensellik (causality) kanıtı DEĞİLDİR.**

Ordinary magnitude-squared coherence, doğrusal stokastik bir model altında frekansa bağlı doğrusal ilişkiyi (*linear association*) ölçer. İki sinyal arasındaki yüksek koherans değeri fiziksel bir neden-sonuç ilişkisini tek başına ispatlamaz.

### 7.4 Uçtan Uca İletim Zinciri Metrolojik Sınırı

Fantom deneylerinde (Stimulus WAV → DAC → Amplifier → Speaker/Exciter → Phantom → Coupling → Chestpiece → Sensor → ESP32 → USB → Host), H1 kestirimi **tüm uçtan uca iletim zincirini** karakterize eder.

- İzole bir stetoskop frekans cevabı **DEĞİLDİR.**
- Anatomik göğüs duvarı cevabı **DEĞİLDİR.**
- Kalibre edilmiş akustik ses basıncı **DEĞİLDİR.**

### 7.5 Kod Referansı

- Fonksiyon: `pcg_core.scientific.system_id.estimate_siso_system_id()`
- Model: `pcg_core.scientific.models.SystemIdentificationResult`
- Yapılandırma: `pcg_core.scientific.models.SystemIdConfig`

---

## 8. JSON-Safe Serileştirme

Tüm bilimsel sonuç nesneleri (`SignalCharacterizationResult`, `SpectralAnalysisResult`, `EnvelopeLabResult`, `SystemIdentificationResult`) `.to_dict()` yöntemiyle JSON-safe sözlüklere dönüştürülür.

`NaN` ve `Inf` değerler `models.sanitize_float()` ve `sanitize_list()` yardımcılarıyla temizlenir. Bu, WebSocket ve REST API yanıtlarında JSON serileştirme hatalarını önler.

---

## 9. Frontend Bileşeni: ScientificLab

`ScientificLab.tsx` bileşeni, bilimsel analiz sonuçlarını dört sekmeli bir arayüzde sunar:

1. **Signal Quality** — Skaler metrik kartları, sinyal dalga formu, metroloji açıklamaları
2. **Welch Spectrum** — PSD eğrisi, frekans adımı, ENBW bilgisi
3. **Envelope Lab** — Çoklu zarf izleri, TKEO/Springer karşılaştırması
4. **System Identification** — H1 Bode diyagramları (genlik ve faz), koherans eğrisi

Her metrik kartında açılabilir "Metrology Notes" (metroloji notları) paneli bulunur. Bu panel:
- Ne olduğunu açıklar
- Neden faydalı olduğunu belirtir
- Büyük/küçük değerlerin ne anlama geldiğini açıklar
- **Ne ispatlamadığını** vurgular

---

## 10. Analiz Profilleri

Bilimsel analiz motoru, versiyonlu profil yapılandırmaları ile çalışır:

| Profil Adı | Filtre Yapılandırması | Kullanım Amacı |
|------------|----------------------|----------------|
| `GENERAL_PCG_V1` | 20–600 Hz 4. derece Butterworth | Genel PCG mühendislik analizi |
| `RAW_INTEGRITY_V1` | Filtre yok (tam bant genişliği) | Edinim bütünlüğü doğrulaması |
| `BROADBAND_SYSTEM_ID_V1` | Filtre yok | Sistem tanılama geniş bant FRF |
| `SPRINGER_SEGMENTATION_RESEARCH_V1` | 25–400 Hz | Springer PCG segmentasyon araştırması |

---

## 11. Test Stratejisi

Tüm bilimsel modüller deterministik birim testleriyle doğrulanır:

- **Bilinen sinyal testleri:** Saf sinüs, beyaz gürültü ve birim darbe dizileri ile beklenen metrik değerlerin doğrulanması
- **Sınır koşulu testleri:** Boş dizi, tek örneklik dizi, NaN/Inf içeren dizi
- **Numerik kararlılık testleri:** Çok küçük genlikli sinyaller (RMS ≈ 0)
- **Konvansiyon doğrulama:** SciPy CSD konvansiyonunun $\langle X^* Y \rangle$ olduğunun açık testi
- **Koherans sınır testi:** $\gamma^2 \in [0.0, 1.0]$ garantisi

---

## 12. Jüri ve Savunma İçin 30 Saniyelik Özet

> *"Bu milestone'da AuscultaForge'a savunulabilir bir bilimsel sinyal karakterizasyon katmanı ekledik. Sinyal kalitesi metrikleri (RMS, Crest Factor, FS utilization, ZCR), Welch güç spektral yoğunluğu motoru, dört farklı deterministik zarf algoritması (Hilbert, Moving RMS, TKEO, Springer 40–60 Hz PSD-band) ve H1-model SISO sistem tanılama temeli — hepsi tam test edilmiş, JSON-safe serileştirmeli ve metrolojik sınırları açıkça belgelenmiş olarak uygulandı. Arayüzde her metrik kartı 'ne ispatlamadığını' açıkça belirtir; kalibrasyonu yapılmamış donanımda akustik basınç birimi (Pa, dB SPL) iddiası veya klinik tanı skoru sunulmaz."*
