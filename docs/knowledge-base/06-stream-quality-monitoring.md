# 06 â€” AkÄ±ÅŸ Kalite Denetimi ve BÃ¼tÃ¼nlÃ¼k Ä°zleme (Stream Quality Monitoring)

## Bu nedir?

AkÄ±ÅŸ kalite denetimi, mikrodenetleyiciden veya bir simÃ¼latÃ¶rden gelen `SampleBlock` dizisinin zamanlama, sÄ±ra numarasÄ± ve Ã¶rnekleme frekansÄ± tutarlÄ±lÄ±ÄŸÄ±nÄ± denetleyen; paket kaybÄ±, sÄ±ralama bozulmasÄ± veya zaman kaymasÄ± olduÄŸunda bunu anÄ±nda tespit edip raporlayan teknik denetim ve hata tespit mekanizmasÄ±dÄ±r (diagnostic health check).

---

## AuscultaForge Neden Bunu KullanÄ±yor?

GÃ¶mÃ¼lÃ¼ sistemlerde (Ã¶zellikle UART, USB CDC veya DMA tamponlarÄ±nda) donanÄ±m taÅŸmalarÄ± (FIFO overflow), elektriksel kesintiler veya iÅŸletim sistemi zamanlama gecikmeleri nedeniyle paketler kaybolabilir veya gecikebilir.

EÄŸer kaybolan bir blok DSP filtresine fark ettirilmeden aradaki boÅŸluk kapatÄ±lÄ±rsa:
1. Filtre durum matrisi (`zi`) zaman sÃ¼reksizliÄŸine uÄŸrar ve sinyale sahte yÃ¼ksek genlikli yapay klikler (artifacts) enjekte eder.
2. Kalp atÄ±m hÄ±zÄ± (BPM) ve ritim hesaplamalarÄ± zaman ekseninde geri dÃ¶nÃ¼lemez biÃ§imde sapar.
3. KullanÄ±cÄ±ya ve analiz hattÄ±na sunulan sinyalin gÃ¼venilirliÄŸi kaybolur.

`StreamQualityMonitor`, bu tip anomalileri sinyal iÅŸleme katmanÄ±na girdiÄŸi anda yakalayarak operatÃ¶rÃ¼ ve sistemi uyarÄ±r.

---

## Denetlenen Anomali TÃ¼rleri

[`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L34-L105) iÃ§inde `StreamQualityMonitor` sÄ±nÄ±fÄ± ÅŸu durumlarÄ± izler:

```text
1. Normal AkÄ±ÅŸ:
   Seq: 0 (t=0.00s) â”€â”€â–º Seq: 1 (t=0.12s) â”€â”€â–º Seq: 2 (t=0.25s)  [SAÄLIKLI]

2. Paket KaybÄ± (Dropped Blocks):
   Seq: 0 (t=0.00s) â”€â”€â–º Seq: 1 (t=0.12s) â”€â”€â–º Seq: 4 (t=0.51s)  [UYARI: 2 blok kayÄ±p (2, 3)]

3. Yinelenen Paket (Repeated Sequence):
   Seq: 0 (t=0.00s) â”€â”€â–º Seq: 1 (t=0.12s) â”€â”€â–º Seq: 1 (t=0.12s)  [UYARI: Blok tekrarÄ±]

4. Zaman Regresyonu (Timestamp Regression):
   Seq: 0 (t=0.00s) â”€â”€â–º Seq: 1 (t=0.25s) â”€â”€â–º Seq: 2 (t=0.10s)  [UYARI: Zaman geriye aktÄ±]

5. Ã–rnekleme FrekansÄ± DeÄŸiÅŸimi:
   Block: fs=2000 Hz â”€â”€â–º Block: fs=4000 Hz                       [UYARI: Frekans uyuÅŸmazlÄ±ÄŸÄ±]
```

---

## `QualityReport` ve `is_healthy` Durumu

Her `inspect_block()` Ã§aÄŸrÄ±sÄ± tespit edilen anomali metinlerini dÃ¶ndÃ¼rÃ¼r ve bir kÃ¼mÃ¼latif durum raporu tutar:

```python
@dataclass(slots=True)
class QualityReport:
    total_blocks: int = 0
    total_samples: int = 0
    dropped_blocks: int = 0             # Tahmini kayÄ±p blok adedi
    repeated_sequences: int = 0         # Tekrarlanan blok sayÄ±sÄ±
    sequence_discontinuities: int = 0   # SÄ±ra atlama/bozulma olay sayÄ±sÄ±
    timestamp_regressions: int = 0      # ZamanÄ±n geriye gittiÄŸi anlar
    sample_rate_changes: int = 0        # Frekans deÄŸiÅŸim olaylarÄ±
    is_healthy: bool = True             # HiÃ§ anomali yoksa True
```

EÄŸer `dropped_blocks > 0` veya zaman anomalisi varsa `is_healthy` derhal `False` olur ve UI gÃ¶stergesine uyarÄ± bayraÄŸÄ± iletilir.

---

## Neden Bu TasarÄ±m SeÃ§ildi?

- **Protokol BaÄŸÄ±msÄ±zlÄ±ÄŸÄ±:** Bu kontroller UART CRC'si veya bayt seviyesi framing ile ilgilenmez; doÄŸrudan nesne dÃ¼zeyindeki `SampleBlock` Ã¼zerinde Ã§alÄ±ÅŸÄ±r. BÃ¶ylece ister Wi-Fi soketi, ister USB seri port, ister test WAV kaynaÄŸÄ± olsun aynÄ± kalite motoru gÃ¶rev yapar.
- **SÄ±fÄ±r Ek YÃ¼k:** Kontroller sadece 3 adet tamsayÄ± ve kayan nokta karÅŸÄ±laÅŸtÄ±rmasÄ±ndan ibarettir; iÅŸlemciye ek yÃ¼k getirmez.

---

## Ä°lgili Dosyalar ve Testler

- Uygulama: [`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L34-L105)
- Testler: [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py#L107-L159)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"GerÃ§ek zamanlÄ± sinyal edinimi gÃ¼venilirlik gerektirir. Seri hatlarda veya tamponlarda oluÅŸabilecek tek bir paket kaybÄ± bile DSP filtre durumunu bozar ve kalp ritmini yanlÄ±ÅŸ hesaplatabilir. AuscultaForge'a entegre ettiÄŸimiz `StreamQualityMonitor`, her gelen bloÄŸun sÄ±ra numarasÄ±nÄ±, zaman damgasÄ±nÄ± ve Ã¶rnekleme frekansÄ±nÄ± anlÄ±k olarak denetler. Tek bir paket dÃ¼ÅŸmesi, tekrarÄ± veya zamanlama kaymasÄ± durumunda filtreyi ve operatÃ¶rÃ¼ uyararak sinyal bÃ¼tÃ¼nlÃ¼ÄŸÃ¼nÃ¼ garanti altÄ±na alÄ±r."*
