# MÃ¼hendislik Bilgi BankasÄ± (Engineering Knowledge Base)
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Senior Design Project (Platform / YazÄ±lÄ±m Kod AdÄ±: `AuscultaForge`)

Bu bilgi bankasÄ±, **Smart Digital Stethoscope** bitirme projesinin (dahili yazÄ±lÄ±m/platform kod adÄ±: **AuscultaForge**) mimari, algoritmik ve sinyal iÅŸleme temellerini aÃ§Ä±klamak, ekip iÃ§i ortak teknik dili saÄŸlamak ve akademik savunmalarda her tasarÄ±m tercihini mÃ¼hendislik temelleriyle savunabilmek amacÄ±yla hazÄ±rlanmÄ±ÅŸtÄ±r.

Buradaki dokÃ¼manlar genel teorik ders notu yÄ±ÄŸÄ±nÄ± deÄŸil; doÄŸrudan proje kaynak kodunda uygulanan mimarinin, veri yapÄ±larÄ±nÄ±n ve sinyal iÅŸleme kararlarÄ±nÄ±n gerekÃ§elendirilmiÅŸ aÃ§Ä±klamalarÄ±dÄ±r.

---

## Ä°Ã§indekiler Dizini

| No | DokÃ¼man | OdaklandÄ±ÄŸÄ± Konu |
|---|---|---|
| 00 | [Proje Genel BakÄ±ÅŸÄ±](00-project-overview.md) | Proje vizyonu, donanÄ±mdan baÄŸÄ±msÄ±z geliÅŸtirme, ekip rolleri, mevcut kilometre taÅŸÄ±. |
| 01 | [PCG Temelleri](01-pcg-fundamentals.md) | Fonokardiyogram, S1/S2 sesleri, Ã¶rnekleme frekansÄ± ($f_s$), Nyquist kriteri ve Ã¶rtÃ¼ÅŸme (aliasing). |
| 02 | [SampleBlock ve Kaynak SoyutlamasÄ±](02-sampleblock-and-sources.md) | Veri kapsÃ¼lleme modeli, Mock/WAV/Realtime/MCU kaynak soyutlamasÄ± ve gevÅŸek baÄŸlÄ±lÄ±k (loose coupling). |
| 03 | [AkÄ±ÅŸ ve Kayan Pencere Tamponu](03-streaming-and-rolling-buffer.md) | Blok tabanlÄ± akÄ±ÅŸ, gecikme-verimlilik dengesi, sÄ±ra ve zaman damgalarÄ±, `RollingBuffer` FIFO mantÄ±ÄŸÄ±. |
| 04 | [SayÄ±sal Sinyal Ä°ÅŸleme ve Filtreleme](04-dsp-and-filtering.md) | Butterworth bant geÃ§iren filtre, durumsal filtreleme (`sosfilt` ve `zi`), bloklar arasÄ± sÃ¼reklilik, 20â€“500 Hz bandÄ±. |
| 05 | [Spektral Analiz](05-spectral-analysis.md) | FFT, Welch PSD ve Spektrogram karÅŸÄ±laÅŸtÄ±rmasÄ±, zaman-frekans Ã§Ã¶zÃ¼nÃ¼rlÃ¼ÄŸÃ¼ ve canlÄ± spektral Ã§erÃ§eveler. |
| 06 | [AkÄ±ÅŸ Kalite Denetimi](06-stream-quality-monitoring.md) | `StreamQualityMonitor`, paket kaybÄ±, sÄ±ra atlama, zaman gerilemesi ve Ã¶rnekleme frekansÄ± deÄŸiÅŸim tespiti. |
| 07 | [Test ve DoÄŸrulama Stratejisi](07-testing-and-validation.md) | AÄŸdan baÄŸÄ±msÄ±z sentetik birim testler, fast mode test yÃ¼rÃ¼tÃ¼mÃ¼ ve tekrarlanabilir deney altyapÄ±sÄ±. |
| 08 | [Referans ve Yakalanan Sinyal DoÄŸrulama](08-reference-vs-capture-validation.md) | Ã‡apraz korelasyonla gecikme tespiti, sinyal hizalama, kazanÃ§, RMSE/SER, uyum ve fantom test gerekÃ§esi. |
| 09 | [Oturum KaydÄ± ve Tekrar Oynatma](09-session-recording-and-replay.md) | SessionRecorder, WAV dosya formatÄ±, tam hÄ±zda float32 kayÄ±t ve tekrar oynatma mimarisi. |
| 10 | [Cihaz Ã‡alÄ±ÅŸma ZamanÄ± ve USB HazÄ±rlÄ±ÄŸÄ±](10-device-runtime-and-usb-readiness.md) | DeviceRuntime, fiziksel USB taÅŸÄ±ma katmanÄ±, MCU iletiÅŸimi ve cihaz yaÅŸam dÃ¶ngÃ¼sÃ¼ yÃ¶netimi. |
| 11 | [Sunucu Verimi, GÃ¶rÃ¼ntÃ¼leme Seyreltmesi ve Geri BasÄ±nÃ§](11-host-throughput-display-decimation-and-backpressure.md) | DisplayPipeline, tepe koruyucu seyreltme, edinim/gÃ¶rÃ¼ntÃ¼leme ayrÄ±mÄ± ve geri basÄ±nÃ§ izolasyonu. |
| 12 | [Oturum Analizi ve Referans-Yakalama DoÄŸrulama TezgahÄ±](12-session-analysis-and-reference-capture-workbench.md) | AnalysisWorkbench, oturum denetimi, referans karÅŸÄ±laÅŸtÄ±rmasÄ± ve hizalama metrikleri. |
| 13 | [Bilimsel Temeller ve Analiz StandartlarÄ±](13-scientific-foundation-and-analysis-conventions.md) | ÃœÃ§lÃ¼ sinyal temsili, Welch PSD standartlarÄ±, birim/kalibrasyon ilkeleri, segmentasyon yol haritasÄ±. |
| 14 | [Bilimsel Sinyal Karakterizasyonu, Zarf LaboratuvarÄ± ve Sistem TanÄ±lama](14-scientific-signal-envelope-system-identification.md) | Signal quality, Hilbert/TKEO/Springer zarf algoritmalarÄ±, H1 FRF, koherans ve ScientificLab UI. |
| 15 | [Springer LR-HSMM Kalp Sesi Segmentasyonu](15-springer-lr-hsmm-segmentation.md) | Springer LR-HSMM matematiksel modeli, 4 zarf Ã¶zniteliÄŸi, Schmidt spike giderme, durasyon modeli ve geniÅŸletilmiÅŸ Viterbi (Ä°leri AraÅŸtÄ±rma). |
| 16 | [GerÃ§ek PCG Segmentasyonu DoÄŸrulamasÄ±](16-real-pcg-segmentation-validation.md) | Stage-C CirCor v1.0.3 doÄŸrulama Ã§erÃ§evesi, denek sÄ±zÄ±ntÄ±sÄ±nÄ± Ã¶nleme, olay toleranslarÄ±, uÃ§tan-uca ve koÅŸullu metrikler (Ä°leri AraÅŸtÄ±rma). |
| -- | [Terimler SÃ¶zlÃ¼ÄŸÃ¼ (Glossary)](GLOSSARY.md) | Biyomedikal, gÃ¶mÃ¼lÃ¼ sistem ve DSP terimlerinin TÃ¼rkÃ§e-Ä°ngilizce tanÄ±mlarÄ±. |

---

## Zorunlu MÃ¼hendislik KuralÄ± (Engineering Rule Going Forward)

Projenin sÃ¼rdÃ¼rÃ¼lebilirliÄŸini, akademik kalitesini ve savunulabilirliÄŸini teminat altÄ±na almak iÃ§in repo genelinde ÅŸu kural uygulanÄ±r:

> [!IMPORTANT]
> Projeye eklenecek her yeni majÃ¶r kabiliyet veya modÃ¼l aÅŸaÄŸÄ±daki 4 adÄ±mÄ± eksiksiz iÃ§ermek zorundadÄ±r:
> 1. **Kod UygulamasÄ± (Implementation):** Temiz, modÃ¼ler, aÅŸÄ±rÄ± baÄŸÄ±mlÄ±lÄ±klardan arÄ±ndÄ±rÄ±lmÄ±ÅŸ kod.
> 2. **Otomasyonlu Birim Testleri (Automated Tests):** Harici aÄŸa veya manuel adÄ±mlara baÄŸlÄ± olmayan deterministik pytest testleri.
> 3. **Mimari / DokÃ¼mantasyon GÃ¼ncellemesi (Architecture Update):** `README.md` ve `docs/architecture/` gÃ¼ncellemeleri.
> 4. **Bilgi BankasÄ± GerekÃ§elendirmesi (Knowledge-Base Explanation):** Yeni bir mÃ¼hendislik konsepti, algoritma veya donanÄ±m arayÃ¼zÃ¼ eklendiÄŸinde bu bilgi bankasÄ±nda tasarÄ±m gerekÃ§esi ve alternatifleriyle belgelenmelidir.
