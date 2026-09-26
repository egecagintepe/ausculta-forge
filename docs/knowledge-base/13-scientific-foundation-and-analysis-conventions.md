# 13 — Bilimsel Temeller, Sinyal Temsilleri ve Metrolojik Standartlar

## 1. Bu Dokümanın Amacı

Bu doküman, AuscultaForge projesinde kullanılan tüm sayısal sinyal işleme (DSP), spektral kestirim, akustik fantom doğrulaması ve fonokardiyografi (PCG) analiz algoritmalarının **akademik literatüre ve katı metrolojik kurallara dayandırılmasını** sağlayan bilimsel çerçeveyi açıklar.

Projemizde hiçbir matematiksel formül veya filtre katsayısı rastgele ya da "kulağa hoş geldiği için" seçilmez. Her algoritma; fiziksel problem, matematiksel model, varsayımlar, hakemli literatür dayanağı, algoritmik yapılandırma, deterministik birim testler ve arayüz yorumlama zinciriyle izlenebilir (*traceable*) olmak zorundadır.

---

## 2. Üç Temel Sinyal Temsili Modeli (Architectural Triad)

AuscultaForge yazılım mimarisinde sinyaller birbirine asla karıştırılmayan **üç kesin düzeyde** temsil edilir:

```text
┌────────────────────────────────────────────────────────┐
│ 1. EDİNİM SİNYALİ (Acquisition Signal)                 │
│ - Donanım sınırı: 48 kHz, mono, 32-bit slotta 24 bit   │
│ - Sunucu edinim: tam hızda normalize float32           │
│ - SessionRecorder: tam hızda float32 WAV kayıt         │
│ - Sıfır yapay filtre, sıfır seyreltme, tam doğruluk    │
│ - Not: Bit-exact tamsayı arşivleme araştırma açığıdır │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. ANALİZ SİNYALİ (Analysis Signal)                    │
│ - Belirli bir mühendislik görevi için işlenmiş akış    │
│ - Örn: 20–600 Hz bant geçiren filtreli oturum verisi   │
│ - Örn: 1000 Hz'e rasyonel anti-alias ile seyreltilmiş  │
│ - Asla arayüz çizim sınırları nedeniyle bozulmaz       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. GÖRÜNTÜLEME SİNYALİ (Display Signal)                │
│ - React / SVG arayüzü için sınırlanmış (<= 600 nokta)  │
│ - Ortak zaman eksenli tepe koruyucu seyreltme          │
│ - Yalnızca insan gözü ve ekran pikselleri içindir     │
│ - KESİN KURAL: Asla sayısal metrik hesabına GİRMEZ!   │
└────────────────────────────────────────────────────────┘
```

---

## 3. 48 kHz Ham Edinim vs. PCG Bant Genişliği Ayrımı

Hardware Rev-A donanım standartlarımızda edinim frekansı **48,000 Hz** olarak belirlenmiştir.

> **Jüri ve Savunma Açıklaması:** 48 kHz ham edinim frekansı, kalp seslerinin 24 kHz'lik bir Nyquist bant genişliğine ihtiyaç duyduğu anlamına **GELMEZ**. PCG sinyalinin klinik ve akustik enerjisinin %99'undan fazlası 1,000 Hz'in altındadır.
> 
> 48 kHz'in seçilme nedenleri tamamen donanımsal ve metrolojiktir:
> 1. Donanım üzerindeki I2S MEMS mikrofonun (PUI DMM-4026-B-I2S-R) doğal dahili sigma-delta çalışma modunu desteklemek,
> 2. Analog ön yüzde dik eğimli, faz bozulmasına yol açan analog filtre ihtiyacını ortadan kaldırarak yazılımsal aşırı örnekleme (*oversampling*) sağlamak,
> 3. Akustik fantom deneylerinde 1,000 Hz üzerindeki sistem rezonanslarını ve çevre gürültüsünü geniş bantta gözlemleyebilmek.

Özel PCG analizleri (örneğin segmentasyon veya zarf çıkarımı), 48 kHz ham sinyali `scipy.signal.resample_poly` ile çok fazlı rasyonel filtrelemeden geçirerek matematiksel olarak güvenli biçimde 1,000 Hz'e indirir.

---

## 4. Spektral Analiz Standartları ve Welch Yöntemi

Spektral terimler projemizde gelişigüzel kullanılamaz:

1. **Spektrum vs. Güç Spektral Yoğunluğu (PSD):**
   - **Güç Spektrumu (Power Spectrum, $\text{FS}^2$):** Ayrık sinüzoidal bileşenlerin saf gücünü gösterir.
   - **Güç Spektral Yoğunluğu (PSD, $\text{FS}^2/\text{Hz}$):** Sürekli rastgele gürültü ve biyomedikal akustik dalgaların frekansa düşen güç yoğunluğunu gösterir (Heinzel et al., R003). AuscultaForge varsayılan olarak PSD kullanır.
2. **Frekans Çözünürlüğü ($\Delta f$):**
   $$\Delta f = \frac{f_s}{N_{\text{fft}}}$$
   Donanımın 512 örneklik paket boyutu 48 kHz'de $48000 / 512 = 93.75\text{ Hz}$ frekans adımı verir. Bu çözünürlük 30–150 Hz arasındaki kalp seslerini ayırmak için yetersizdir. Bu nedenle spektral analiz, donanım paketlerini biriktirerek en az 2048 örneklik pencerelerle çalışır ($\Delta f \le 23.4\text{ Hz}$) ya da alt frekansa indirgenmiş sinyal kullanır.
3. **Eşdeğer Gürültü Bant Genişliği (ENBW):**
   Bir pencere fonksiyonu (Hann, Hamming) frekans sızıntısını (*leakage*) engellerken tepe noktasını genişletir. `SpectralAnalysisConfig.enbw(fs)` metodu bu genişlemeyi matematiksel olarak hesaplar (Hann penceresinde $\text{ENBW} \approx 1.50 \cdot \Delta f$).
4. **DC Çıkarma (Detrending):**
   Sensörün DC kayması pencereleme nedeniyle 0–20 Hz bandına taşarak kalp seslerini gölgeler. Bu nedenle spektral kestirimden önce sinyalin ortalaması çıkarılır (`DetrendMode.CONSTANT`).

---

## 5. Filtre Anlambilimi: Nedensel (Causal) vs. Sıfır Fazlı (Zero-Phase)

AuscultaForge'da tek bir "tıbbi evrensel kalp sesi bandı" yoktur:
- **Genel Mühendislik Ön Ayarı (`GENERAL_PCG_V1`):** 20–600 Hz, 4. derece Butterworth filtre.
- **Maksimum Düzlük vs. Faz Bozulması:** Butterworth filtresi geçiş bandında dalgalanmasız (maximally flat) bir genlik cevabı verir; ancak faz cevabı doğrusal değildir.
- **Canlı Akışta Nedensellik Kuralı:** Gerçek zamanlı akışta (`StreamingBandpass`) yalnızca nedensel IIR filtreler kullanılabilir. Sinyali zamanda ileri-geri süzen sıfır fazlı filtreler (`sosfiltfilt`) yalnızca çevrimdışı analizde kullanılabilir ve bu durum raporda açıkça belirtilir.

---

## 6. Birimler ve Kalibrasyon İlkeleri

AuscultaForge; kalibrasyonu yapılmamış donanımlarla kesin fiziksel basınç birimleri sunmayı **kesinlikle reddeder**:

| Yasaklanan Fiziksel İddia | Reddedilme Nedeni | İzin Verilen Mühendislik Temsili |
|---|---|---|
| **Pascal ($\text{Pa}$)** | Mikrofonun akustik duyarlılığı ($\text{dBFS/Pa}$) ölçülmemiştir. | Sayısal Tam Ölçek (`normalized_fs`, $[-1.0, +1.0]$) |
| **Ses Basınç Düzeyi ($\text{dB SPL}$)** | $20\,\mu\text{Pa}$ referansına göre kalibre edilmiş akustik kuplör yoktur. | Sayısal Desibel (`dBFS`), Bağıl Desibel (`dB`) |
| **Klinik Teşhis / Hastalık Skoru** | Yazılım bir tanı cihazı değil, mühendislik doğrulama aracıdır. | Sinyal Benzerliği (NCC, SER dB), Edinim Bütünlüğü |

---

## 7. Dört Durumlu PCG Segmentasyon Yol Haritası

Kalp seslerinin $S_1$, Sistol, $S_2$, Diyastol olarak ayrıştırılması üç aşamalı olarak planlanmıştır:

```text
AŞAMA A (Planlanan NEXT_DSP):
Deterministik Zarf Çıkarımı
- Hilbert Dönüşümü Zarfı
- Homomorfik Zarf (Schmidt et al., R005)
- Kayan Enerji Zarfı
- Aday akustik tepe noktaları

            │
            ▼
AŞAMA B (Planlanan RESEARCH_LATER):
Springer et al. (R006) LR-HSMM Modelinin Yeniden Üretimi
- 4 adet zarf özniteliğinin 50 Hz'e seyreltilmesi
- Lojistik regresyon ile durum olasılıkları
- Süre bağımlı Gizli Yarı-Markov Modeli (HSMM)
- Modifiye Viterbi algoritması ile 4 durumun kodunun çözülmesi

            │
            ▼
AŞAMA C (Planlanan RESEARCH_LATER):
Liu et al. (R007) Bağımsız Doğrulama
- PhysioNet veri tabanları üzerinde hasta ayrık testler
- ±60 ms ve ±100 ms tolerans pencereleri
- Duyarlılık (Se), Kesinlik (PPV) ve F1 skoru raporlaması
```

---

## 8. Jüri ve Bitirme Savunması İçin 30 Saniyelik Özet (30-Second Defense Pitch)

> *"AuscultaForge projesinde sinyal işleme algoritmalarımızı ampirik tahminlere veya kara kutu yapay zeka iddialarına değil; Oppenheim, Rangayyan, Heinzel ve Springer gibi literatürün temel otoritelerine dayandırdık. 48 kHz ham edinim akışımız ile görsel arayüzümüz arasındaki üçlü sinyal temsilini (Edinim, Analiz, Görüntüleme) kesin çizgilerle ayırdık. Akustik kalibrasyonu olmayan bir donanımda Pascal veya dB SPL gibi yanıltıcı birimler raporlamayı reddederek; Welch spektral kestirimi, eşdeğer gürültü bant genişliği (ENBW) ve en küçük kareler kazancı gibi ölçülebilir mühendislik metrikleriyle tam izlenebilir bir araştırma platformu inşa ettik."*
