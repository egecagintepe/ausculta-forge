# 01 — PCG Temelleri ve Örnekleme Teorisi

## Bu nedir?

**Fonokardiyogram (Phonocardiogram - PCG)**, kalbin mekanik aktivitesi, kapakçık hareketleri ve kan akışı sırasında ortaya çıkan akustik titreşimlerin yüksek hassasiyetli bir mikrofon veya piezoelektrik dönüştürücü ile algılanıp zaman domeni dalga formu olarak kaydedilmesidir.

Elektrokardiyogram (EKG/ECG) kalbin elektriksel iletim sistemini ölçerken; PCG doğrudan mekanik ve hemodinamik olayları (kapak kapanma sesleri, türbülanslı kan akışı) yansıtır.

---

## Kalp Seslerinin Fizyolojik Temelleri

Kardiyak akustik sinyal temel olarak iki ana bileşenden ve olası üfürümlerden oluşur:

1. **S1 (Birinci Kalp Sesi - "Lubb"):**
   - **Mekanizma:** Ventriküler sistol başlangıcında atriyoventriküler (Mitral ve Triküspit) kapakların kapanmasıyla meydana gelir.
   - **Akustik Özellik:** Genellikle daha uzun süreli (~100–150 ms) ve daha düşük frekanslıdır (baskın frekans: 30–100 Hz).
2. **S2 (İkinci Kalp Sesi - "Dubb"):**
   - **Mekanizma:** Ventriküler diyastol başlangıcında semilunar (Aort ve Pulmoner) kapakların ani kapanmasıyla oluşur.
   - **Akustik Özellik:** S1'e göre daha keskin, daha kısa süreli (~60–100 ms) ve biraz daha yüksek frekanslıdır (baskın frekans: 50–150 Hz).
3. **Kardiyak Üfürümler (Murmurs):**
   - **Mekanizma:** Kapak yetmezliği (regürjitasyon) veya kapak darlığı (stenoz) sonucu kan akışının laminer durumdan türbülanslı duruma geçmesiyle oluşur.
   - **Akustik Özellik:** S1-S2 arasına veya sonrasına yayılan, 150–600 Hz (veya nadiren daha yüksek) frekans bölgesinde zayıf genlikli sürekli titreşimler içerir.

---

## Örnekleme Frekansı ($f_s$) ve Nyquist Kriteri

### Nyquist-Shannon Örnekleme Teoremi
Sürekli zamanlı (analog) bir sinyalin, sayısallaştırıldıktan sonra bilgi kaybı ve frekans bozulması olmaksızın yeniden oluşturulabilmesi için örnekleme frekansı ($f_s$), sinyalde bulunan en yüksek frekans bileşeninin ($f_{max}$) en az iki katı olmalıdır:
$$f_s \ge 2 \cdot f_{max} \quad \implies \quad f_{Nyquist} = \frac{f_s}{2}$$

### Örtüşme (Aliasing) Problemi ve Kritik Mühendislik Ayrımı
Eğer analog sinyalde $f_{Nyquist}$ üzerinde frekans bileşenleri bulunuyorsa ve bunlar örnekleme anında bastırılmazsa, bu yüksek frekanslar alt frekans bantlarına katlanarak sinyali geri dönülemez biçimde bozar (aliasing).

> [!WARNING]
> **Kritik Mühendislik İlkesi:** Host PC tarafında uyguladığımız sayısal filtreleme (yazılımsal Butterworth bant geçiren filtre), örnekleme anında (ADC katmanında) zaten oluşmuş bir örtüşmeyi (aliasing) **asla geriye döndüremez veya önleyemez**.
> - **Anti-Aliasing Sorumluluğu:** Örnekleme öncesinde analog donanım katmanında (analog aktif/pasif alçak geçiren filtre) veya dahili donanımsal decimator/anti-aliasing filtresine sahip bir dijital MEMS sensör mimarisinde çözülmek zorundadır.
> - **Sayısal Filtrelemenin Rolü:** PC tarafındaki yazılımsal filtreleme ise yalnızca Nyquist sınırları içinde başarıyla sayısallaştırılmış sinyalden ilgi duyulan geçici 20–600 Hz bandını ayırmak, temel hat kaymasını (baseline wander) ve yüksek frekans kalıntılarını süzen bir ardıl işleme (post-processing) katmanıdır.

```text
Genlik
  ▲
  │       Temel PCG (20-150 Hz)
  │       ┌───────┐
  │       │       │    Üfürüm (150-600 Hz)
  │       │       │    ┌─────────┐
  │       │       │    │         │          Nyquist Sınırı (fs/2 = 1000 Hz)
  │       │       │    │         │               │
  └───────┴───────┴────┴─────────┴───────────────┼────────► Frekans (Hz)
  0       20     150            600            1000 (fs = 2000 Hz)
```

---

## AuscultaForge Neden 2000 Hz ve 4000 Hz Kullanıyor?

- Kalp seslerinin klinik olarak anlamlı enerji spektrumu 20 Hz ile 600 Hz arasına sıkışmıştır.
- $f_s = 2000\text{ Hz}$ seçildiğinde Nyquist sınırı $1000\text{ Hz}$ olur. Bu, 600 Hz'lik üst akustik sınır için $400\text{ Hz}$'lik güvenli bir geçiş bandı bırakır ($1000\text{ Hz} > 600\text{ Hz}$).
- Uluslararası altın standart veri tabanları:
  - **PhysioNet / CinC Challenge 2016:** $2,000\text{ Hz}$ mono WAV formatında sağlanır.
  - **CirCor DigiScope (2022):** $4,000\text{ Hz}$ mono WAV formatında sağlanır.
- AuscultaForge bu iki frekansı da (`models.py`, `sources.py`, `analysis.py`) dinamik olarak destekler ve sabit 4000 Hz varsayımı yapmaz.

---

## Sistemde Nerede Bulunuyor?

- Sinyal modelleme ve $f_s$ doğrulaması: [`software/pcg_core/models.py`](../../software/pcg_core/models.py#L4-L22)
- Sentetik S1/S2 sinyal üretimi: [`software/pcg_core/sources.py`](../../software/pcg_core/sources.py#L19-L43) (`MockPCGSource._make_signal`)
- Spektral bant ayrımı: [`software/pcg_core/analysis.py`](../../software/pcg_core/analysis.py#L105-L115)
- Testler: [`software/tests/test_analysis.py`](../../software/tests/test_analysis.py#L37-L60)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Kardiyak akustik sinyallerin majör enerjisi 20 ila 150 Hz arasındaki S1 ve S2 seslerindedir; patolojik üfürümler ise 600 Hz'e kadar uzanabilir. Nyquist kriterine göre $f_s \ge 2 f_{max}$ şartı gereği en az 1200 Hz örnekleme gerekir. AuscultaForge'da hem açık literatür standardı olan PhysioNet 2000 Hz ve CirCor 4000 Hz frekanslarını destekleyen hem de donanım edinim birimimiz için güvenli geçiş bandı bırakan esnek bir örnekleme mimarisi kurduk."*
