# 01 â€” PCG Temelleri ve Ã–rnekleme Teorisi

## Bu nedir?

**Fonokardiyogram (Phonocardiogram - PCG)**, kalbin mekanik aktivitesi, kapakÃ§Ä±k hareketleri ve kan akÄ±ÅŸÄ± sÄ±rasÄ±nda ortaya Ã§Ä±kan akustik titreÅŸimlerin yÃ¼ksek hassasiyetli bir mikrofon veya piezoelektrik dÃ¶nÃ¼ÅŸtÃ¼rÃ¼cÃ¼ ile algÄ±lanÄ±p zaman domeni dalga formu olarak kaydedilmesidir.

Elektrokardiyogram (EKG/ECG) kalbin elektriksel iletim sistemini Ã¶lÃ§erken; PCG doÄŸrudan mekanik ve hemodinamik olaylarÄ± (kapak kapanma sesleri, tÃ¼rbÃ¼lanslÄ± kan akÄ±ÅŸÄ±) yansÄ±tÄ±r.

---

## Kalp Seslerinin Fizyolojik Temelleri

Kardiyak akustik sinyal temel olarak iki ana bileÅŸenden ve olasÄ± Ã¼fÃ¼rÃ¼mlerden oluÅŸur:

1. **S1 (Birinci Kalp Sesi - "Lubb"):**
   - **Mekanizma:** VentrikÃ¼ler sistol baÅŸlangÄ±cÄ±nda atriyoventrikÃ¼ler (Mitral ve TrikÃ¼spit) kapaklarÄ±n kapanmasÄ±yla meydana gelir.
   - **Akustik Ã–zellik:** Genellikle daha uzun sÃ¼reli (~100â€“150 ms) ve daha dÃ¼ÅŸÃ¼k frekanslÄ±dÄ±r (baskÄ±n frekans: 30â€“100 Hz).
2. **S2 (Ä°kinci Kalp Sesi - "Dubb"):**
   - **Mekanizma:** VentrikÃ¼ler diyastol baÅŸlangÄ±cÄ±nda semilunar (Aort ve Pulmoner) kapaklarÄ±n ani kapanmasÄ±yla oluÅŸur.
   - **Akustik Ã–zellik:** S1'e gÃ¶re daha keskin, daha kÄ±sa sÃ¼reli (~60â€“100 ms) ve biraz daha yÃ¼ksek frekanslÄ±dÄ±r (baskÄ±n frekans: 50â€“150 Hz).
3. **Kardiyak ÃœfÃ¼rÃ¼mler (Murmurs):**
   - **Mekanizma:** Kapak yetmezliÄŸi (regÃ¼rjitasyon) veya kapak darlÄ±ÄŸÄ± (stenoz) sonucu kan akÄ±ÅŸÄ±nÄ±n laminer durumdan tÃ¼rbÃ¼lanslÄ± duruma geÃ§mesiyle oluÅŸur.
   - **Akustik Ã–zellik:** S1-S2 arasÄ±na veya sonrasÄ±na yayÄ±lan, 150â€“600 Hz (veya nadiren daha yÃ¼ksek) frekans bÃ¶lgesinde zayÄ±f genlikli sÃ¼rekli titreÅŸimler iÃ§erir.

---

## Ã–rnekleme FrekansÄ± ($f_s$) ve Nyquist Kriteri

### Nyquist-Shannon Ã–rnekleme Teoremi
SÃ¼rekli zamanlÄ± (analog) bir sinyalin, sayÄ±sallaÅŸtÄ±rÄ±ldÄ±ktan sonra bilgi kaybÄ± ve frekans bozulmasÄ± olmaksÄ±zÄ±n yeniden oluÅŸturulabilmesi iÃ§in Ã¶rnekleme frekansÄ± ($f_s$), sinyalde bulunan en yÃ¼ksek frekans bileÅŸeninin ($f_{max}$) en az iki katÄ± olmalÄ±dÄ±r:
$$f_s \ge 2 \cdot f_{max} \quad \implies \quad f_{Nyquist} = \frac{f_s}{2}$$

### Ã–rtÃ¼ÅŸme (Aliasing) Problemi ve Kritik MÃ¼hendislik AyrÄ±mÄ±
EÄŸer analog sinyalde $f_{Nyquist}$ Ã¼zerinde frekans bileÅŸenleri bulunuyorsa ve bunlar Ã¶rnekleme anÄ±nda bastÄ±rÄ±lmazsa, bu yÃ¼ksek frekanslar alt frekans bantlarÄ±na katlanarak sinyali geri dÃ¶nÃ¼lemez biÃ§imde bozar (aliasing).

> [!WARNING]
> **Kritik MÃ¼hendislik Ä°lkesi:** Host PC tarafÄ±nda uyguladÄ±ÄŸÄ±mÄ±z sayÄ±sal filtreleme (yazÄ±lÄ±msal Butterworth bant geÃ§iren filtre), Ã¶rnekleme anÄ±nda (ADC katmanÄ±nda) zaten oluÅŸmuÅŸ bir Ã¶rtÃ¼ÅŸmeyi (aliasing) **asla geriye dÃ¶ndÃ¼remez veya Ã¶nleyemez**.
> - **Anti-Aliasing SorumluluÄŸu:** Ã–rnekleme Ã¶ncesinde analog donanÄ±m katmanÄ±nda (analog aktif/pasif alÃ§ak geÃ§iren filtre) veya dahili donanÄ±msal decimator/anti-aliasing filtresine sahip bir dijital MEMS sensÃ¶r mimarisinde Ã§Ã¶zÃ¼lmek zorundadÄ±r.
> - **SayÄ±sal Filtrelemenin RolÃ¼:** PC tarafÄ±ndaki yazÄ±lÄ±msal filtreleme ise yalnÄ±zca Nyquist sÄ±nÄ±rlarÄ± iÃ§inde baÅŸarÄ±yla sayÄ±sallaÅŸtÄ±rÄ±lmÄ±ÅŸ sinyalden ilgi duyulan geÃ§ici 20â€“600 Hz bandÄ±nÄ± ayÄ±rmak, temel hat kaymasÄ±nÄ± (baseline wander) ve yÃ¼ksek frekans kalÄ±ntÄ±larÄ±nÄ± sÃ¼zen bir ardÄ±l iÅŸleme (post-processing) katmanÄ±dÄ±r.

```text
Genlik
  â–²
  â”‚       Temel PCG (20-150 Hz)
  â”‚       â”Œâ”€â”€â”€â”€â”€â”€â”€â”
  â”‚       â”‚       â”‚    ÃœfÃ¼rÃ¼m (150-600 Hz)
  â”‚       â”‚       â”‚    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚       â”‚       â”‚    â”‚         â”‚          Nyquist SÄ±nÄ±rÄ± (fs/2 = 1000 Hz)
  â”‚       â”‚       â”‚    â”‚         â”‚               â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â–º Frekans (Hz)
  0       20     150            600            1000 (fs = 2000 Hz)
```

---

## AuscultaForge Neden 2000 Hz ve 4000 Hz KullanÄ±yor?

- Kalp seslerinin klinik olarak anlamlÄ± enerji spektrumu 20 Hz ile 600 Hz arasÄ±na sÄ±kÄ±ÅŸmÄ±ÅŸtÄ±r.
- $f_s = 2000\text{ Hz}$ seÃ§ildiÄŸinde Nyquist sÄ±nÄ±rÄ± $1000\text{ Hz}$ olur. Bu, 600 Hz'lik Ã¼st akustik sÄ±nÄ±r iÃ§in $400\text{ Hz}$'lik gÃ¼venli bir geÃ§iÅŸ bandÄ± bÄ±rakÄ±r ($1000\text{ Hz} > 600\text{ Hz}$).
- UluslararasÄ± altÄ±n standart veri tabanlarÄ±:
  - **PhysioNet / CinC Challenge 2016:** $2,000\text{ Hz}$ mono WAV formatÄ±nda saÄŸlanÄ±r.
  - **CirCor DigiScope (2022):** $4,000\text{ Hz}$ mono WAV formatÄ±nda saÄŸlanÄ±r.
- AuscultaForge bu iki frekansÄ± da (`models.py`, `sources.py`, `analysis.py`) dinamik olarak destekler ve sabit 4000 Hz varsayÄ±mÄ± yapmaz.

---

## Sistemde Nerede Bulunuyor?

- Sinyal modelleme ve $f_s$ doÄŸrulamasÄ±: [`software/pcg_core/models.py`](../../software/pcg_core/models.py#L4-L22)
- Sentetik S1/S2 sinyal Ã¼retimi: [`software/pcg_core/sources.py`](../../software/pcg_core/sources.py#L19-L43) (`MockPCGSource._make_signal`)
- Spektral bant ayrÄ±mÄ±: [`software/pcg_core/analysis.py`](../../software/pcg_core/analysis.py#L105-L115)
- Testler: [`software/tests/test_analysis.py`](../../software/tests/test_analysis.py#L37-L60)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"Kardiyak akustik sinyallerin majÃ¶r enerjisi 20 ila 150 Hz arasÄ±ndaki S1 ve S2 seslerindedir; patolojik Ã¼fÃ¼rÃ¼mler ise 600 Hz'e kadar uzanabilir. Nyquist kriterine gÃ¶re $f_s \ge 2 f_{max}$ ÅŸartÄ± gereÄŸi en az 1200 Hz Ã¶rnekleme gerekir. AuscultaForge'da hem aÃ§Ä±k literatÃ¼r standardÄ± olan PhysioNet 2000 Hz ve CirCor 4000 Hz frekanslarÄ±nÄ± destekleyen hem de donanÄ±m edinim birimimiz iÃ§in gÃ¼venli geÃ§iÅŸ bandÄ± bÄ±rakan esnek bir Ã¶rnekleme mimarisi kurduk."*
