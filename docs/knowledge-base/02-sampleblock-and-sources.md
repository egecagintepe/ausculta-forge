# 02 â€” SampleBlock ve Kaynak SoyutlamasÄ± (Source Abstraction)

## Bu nedir?

`SampleBlock`, AuscultaForge sisteminde fiziksel donanÄ±mdan, seri haberleÅŸmeden veya dosya biÃ§imlerinden baÄŸÄ±msÄ±z olarak ses verisini taÅŸÄ±yan standart veri aktarÄ±m birimidir.

Kaynak soyutlamasÄ± (Source abstraction) ise ses verisinin nereden geldiÄŸini (yapay Ã¼retim, WAV dosyasÄ±, USB seri port, Wi-Fi soketi) sinyal iÅŸleme hattÄ±ndan (DSP) tamamen gizleyen yazÄ±lÄ±m tasarÄ±m desenidir.

---

## Veri Modeli: `SampleBlock`

[`software/pcg_core/models.py`](../../software/pcg_core/models.py) iÃ§inde tanÄ±mlÄ± olan yapÄ±:

```python
@dataclass(slots=True)
class SampleBlock:
    sequence: int          # Blok sÄ±ra takip numarasÄ± (0, 1, 2, ...)
    timestamp_s: float     # BloÄŸun baÅŸlangÄ±Ã§ zaman damgasÄ± (saniye)
    sample_rate_hz: int    # Ã–rnekleme frekansÄ± (Hz)
    samples: np.ndarray    # 1D float32, normalize edilmiÅŸ [-1.0, 1.0] dizi
    source: str = "unknown"# Veri kaynaÄŸÄ± kimliÄŸi ("mock", "a0001.wav", vb.)
```

### TasarÄ±m Tercihleri ve Detaylar
1. **`slots=True`:** Python nesne ek yÃ¼kÃ¼nÃ¼ (`__dict__`) ortadan kaldÄ±rÄ±r. Saniyede onlarca blok aktarÄ±lÄ±rken bellek tahsisini (allocation) ve Ã§Ã¶p toplayÄ±cÄ± (garbage collector) baskÄ±sÄ±nÄ± asgariye indirir.
2. **`float32` Normalizasyon:** FarklÄ± ADC Ã§Ã¶zÃ¼nÃ¼rlÃ¼kleri (12-bit, 16-bit, 24-bit) doÄŸrudan ham tamsayÄ± olarak deÄŸil, $[-1.0, 1.0]$ aralÄ±ÄŸÄ±na normalize edilerek taÅŸÄ±nÄ±r. Bu sayede DSP filtre katsayÄ±larÄ± ve RMS metrikleri donanÄ±m bit derinliÄŸinden baÄŸÄ±msÄ±zlaÅŸÄ±r.
3. **Tek KanallÄ± 1-D DoÄŸrulama:** `__post_init__` iÃ§inde boyut ve pozitif frekans kontrolÃ¼ yapÄ±larak geÃ§ersiz verinin algoritmaya girmesi ilk adÄ±mda engellenir.

---

## Kaynak TÃ¼rleri ve Rolleri

```text
               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
               â”‚    MockPCGSource      â”‚ â”€â”€â–º Sentetik S1/S2 test verisi
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
               â”‚       WavSource       â”‚ â”€â”€â–º Ã‡evrimdÄ±ÅŸÄ± toplu analiz
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
               â”‚   RealtimeWavSource   â”‚ â”€â”€â–º CanlÄ± MCU akÄ±ÅŸ simÃ¼latÃ¶rÃ¼
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
               â”‚ *Gelecek* SerialSourceâ”‚ â”€â”€â–º DonanÄ±m KaynaÄŸÄ± (Aday: ESP32 / USB-UART)
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
                           â–¼  (Hepsi SampleBlock Iterator Ã¼retir)
               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
               â”‚      SampleBlock      â”‚
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
                           â–¼
               â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
               â”‚  Ortak DSP & Metrik   â”‚
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

1. **`MockPCGSource` ([`sources.py`](../../software/pcg_core/sources.py#L9-L60)):**
   - Belirtilen kalp atÄ±m hÄ±zÄ±nda (BPM) sÃ¶nÃ¼mlÃ¼ sinÃ¼s paketleriyle S1/S2 sesleri ve arka plan gÃ¼rÃ¼ltÃ¼sÃ¼ Ã¼retir.
   - DonanÄ±m veya internet baÄŸlantÄ±sÄ± olmaksÄ±zÄ±n DSP hattÄ±nÄ± Ã§alÄ±ÅŸtÄ±rmayÄ± saÄŸlar.
2. **`WavSource` ([`sources.py`](../../software/pcg_core/sources.py#L62-L93)):**
   - Diskten mono WAV dosyasÄ± okur (16-bit tamsayÄ±larÄ± `float32`'ye Ã§evirir) ve bloklar halinde sunar.
   - Ã‡evrimdÄ±ÅŸÄ± doÄŸrulama ve veri kÃ¼mesi analizi iÃ§in kullanÄ±lÄ±r.
3. **`RealtimeWavSource` ([`sources.py`](../../software/pcg_core/sources.py#L95-L137)):**
   - WAV kaydÄ±nÄ± gerÃ§ek duvar saati (wall-clock) hÄ±zÄ±nda replaying yaparak canlÄ± MCU akÄ±ÅŸÄ±nÄ± taklit eder.
   - HÄ±zlÄ± testler iÃ§in `--fast` (unpaced) modunu destekler.
4. **Gelecekteki `SerialSource`:**
   - MCU'dan gelen seri paketleri ayrÄ±ÅŸtÄ±rÄ±p aynÄ± `SampleBlock` nesnesini oluÅŸturacaktÄ±r.

---

## Neden Bu TasarÄ±m SeÃ§ildi? Hangi Problemleri Ã–nlÃ¼yor?

- **Protokol Kilidini Ã–nleme:** TaÅŸÄ±ma katmanÄ± kablolu Native USB olarak seÃ§ilmiÅŸ olup wire paket formatÄ± (CRC, baÅŸlÄ±k baytlarÄ±, framing) henÃ¼z kilitlenmemiÅŸtir. Sinyal iÅŸleme kodunun donanÄ±m baytlarÄ±na doÄŸrudan baÄŸlanmasÄ± engellenmiÅŸtir.
- **Tekrarlanabilir Test Edilebilirlik:** Filtreleme ve analiz kodlarÄ± hiÃ§bir zaman "gerÃ§ek porta baÄŸlÄ± mÄ±yÄ±m?" kontrolÃ¼ yapmaz; bu sayede birim testleri sÄ±fÄ±r donanÄ±mla nanosaniyeler iÃ§inde koÅŸar.

---

## Ä°lgili Dosyalar ve Testler

- Veri yapÄ±sÄ±: [`software/pcg_core/models.py`](../../software/pcg_core/models.py)
- Kaynak sÄ±nÄ±flarÄ±: [`software/pcg_core/sources.py`](../../software/pcg_core/sources.py)
- Testler: [`software/tests/test_core.py`](../../software/tests/test_core.py#L8-L12), [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py#L17-L54)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"YazÄ±lÄ±m mimarimizin kalbinde `SampleBlock` arayÃ¼zÃ¼ yer alÄ±r. GiriÅŸ verisinin nereden geldiÄŸi (yapay sinyal, gerÃ§ek WAV kaydÄ± veya mikrodenetleyici UART hattÄ±) sinyal iÅŸleme algoritmalarÄ±mÄ±z iÃ§in farksÄ±zdÄ±r. TÃ¼m kaynaklar veriyi aynÄ± normalize float32 bloklarÄ±, sÄ±ra numarasÄ± ve zaman damgasÄ±yla iletir. Bu gevÅŸek baÄŸlÄ±lÄ±k (loose coupling), donanÄ±m tasarÄ±mÄ±ndaki olasÄ± revizyonlarÄ±n PC yazÄ±lÄ±mÄ±nÄ± etkilemesini tamamen engeller."*
