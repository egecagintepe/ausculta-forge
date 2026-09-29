# 06 — Akış Kalite Denetimi ve Bütünlük İzleme (Stream Quality Monitoring)

## Bu nedir?

Akış kalite denetimi, mikrodenetleyiciden veya bir simülatörden gelen `SampleBlock` dizisinin zamanlama, sıra numarası ve örnekleme frekansı tutarlılığını denetleyen; paket kaybı, sıralama bozulması veya zaman kayması olduğunda bunu anında tespit edip raporlayan teknik denetim ve hata tespit mekanizmasıdır (diagnostic health check).

---

## AuscultaForge Neden Bunu Kullanıyor?

Gömülü sistemlerde (özellikle UART, USB CDC veya DMA tamponlarında) donanım taşmaları (FIFO overflow), elektriksel kesintiler veya işletim sistemi zamanlama gecikmeleri nedeniyle paketler kaybolabilir veya gecikebilir.

Eğer kaybolan bir blok DSP filtresine fark ettirilmeden aradaki boşluk kapatılırsa:
1. Filtre durum matrisi (`zi`) zaman süreksizliğine uğrar ve sinyale sahte yüksek genlikli yapay klikler (artifacts) enjekte eder.
2. Kalp atım hızı (BPM) ve ritim hesaplamaları zaman ekseninde geri dönülemez biçimde sapar.
3. Kullanıcıya ve analiz hattına sunulan sinyalin güvenilirliği kaybolur.

`StreamQualityMonitor`, bu tip anomalileri sinyal işleme katmanına girdiği anda yakalayarak operatörü ve sistemi uyarır.

---

## Denetlenen Anomali Türleri

[`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L34-L105) içinde `StreamQualityMonitor` sınıfı şu durumları izler:

```text
1. Normal Akış:
   Seq: 0 (t=0.00s) ──► Seq: 1 (t=0.12s) ──► Seq: 2 (t=0.25s)  [SAĞLIKLI]

2. Paket Kaybı (Dropped Blocks):
   Seq: 0 (t=0.00s) ──► Seq: 1 (t=0.12s) ──► Seq: 4 (t=0.51s)  [UYARI: 2 blok kayıp (2, 3)]

3. Yinelenen Paket (Repeated Sequence):
   Seq: 0 (t=0.00s) ──► Seq: 1 (t=0.12s) ──► Seq: 1 (t=0.12s)  [UYARI: Blok tekrarı]

4. Zaman Regresyonu (Timestamp Regression):
   Seq: 0 (t=0.00s) ──► Seq: 1 (t=0.25s) ──► Seq: 2 (t=0.10s)  [UYARI: Zaman geriye aktı]

5. Örnekleme Frekansı Değişimi:
   Block: fs=2000 Hz ──► Block: fs=4000 Hz                       [UYARI: Frekans uyuşmazlığı]
```

---

## `QualityReport` ve `is_healthy` Durumu

Her `inspect_block()` çağrısı tespit edilen anomali metinlerini döndürür ve bir kümülatif durum raporu tutar:

```python
@dataclass(slots=True)
class QualityReport:
    total_blocks: int = 0
    total_samples: int = 0
    dropped_blocks: int = 0             # Tahmini kayıp blok adedi
    repeated_sequences: int = 0         # Tekrarlanan blok sayısı
    sequence_discontinuities: int = 0   # Sıra atlama/bozulma olay sayısı
    timestamp_regressions: int = 0      # Zamanın geriye gittiği anlar
    sample_rate_changes: int = 0        # Frekans değişim olayları
    is_healthy: bool = True             # Hiç anomali yoksa True
```

Eğer `dropped_blocks > 0` veya zaman anomalisi varsa `is_healthy` derhal `False` olur ve UI göstergesine uyarı bayrağı iletilir.

---

## Neden Bu Tasarım Seçildi?

- **Protokol Bağımsızlığı:** Bu kontroller UART CRC'si veya bayt seviyesi framing ile ilgilenmez; doğrudan nesne düzeyindeki `SampleBlock` üzerinde çalışır. Böylece ister Wi-Fi soketi, ister USB seri port, ister test WAV kaynağı olsun aynı kalite motoru görev yapar.
- **Sıfır Ek Yük:** Kontroller sadece 3 adet tamsayı ve kayan nokta karşılaştırmasından ibarettir; işlemciye ek yük getirmez.

---

## İlgili Dosyalar ve Testler

- Uygulama: [`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L34-L105)
- Testler: [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py#L107-L159)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Gerçek zamanlı sinyal edinimi güvenilirlik gerektirir. Seri hatlarda veya tamponlarda oluşabilecek tek bir paket kaybı bile DSP filtre durumunu bozar ve kalp ritmini yanlış hesaplatabilir. AuscultaForge'a entegre ettiğimiz `StreamQualityMonitor`, her gelen bloğun sıra numarasını, zaman damgasını ve örnekleme frekansını anlık olarak denetler. Tek bir paket düşmesi, tekrarı veya zamanlama kayması durumunda filtreyi ve operatörü uyararak sinyal bütünlüğünü garanti altına alır."*
