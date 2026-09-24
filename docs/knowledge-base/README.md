# AuscultaForge — Mühendislik Bilgi Bankası (Engineering Knowledge Base)

Bu bilgi bankası, **AuscultaForge** akıllı dijital stetoskop bitirme projesinin mimari, algoritmik ve sinyal işleme temellerini açıklamak, ekip içi ortak teknik dili sağlamak ve akademik savunmalarda her tasarım tercihini mühendislik temelleriyle savunabilmek amacıyla hazırlanmıştır.

Buradaki dokümanlar genel teorik ders notu yığını değil; doğrudan AuscultaForge kaynak kodunda uygulanan mimarinin, veri yapılarının ve sinyal işleme kararlarının gerekçelendirilmiş açıklamalarıdır.

---

## İçindekiler Dizini

| No | Doküman | Odaklandığı Konu |
|---|---|---|
| 00 | [Proje Genel Bakışı](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/00-project-overview.md) | Proje vizyonu, donanımdan bağımsız geliştirme, ekip rolleri, mevcut kilometre taşı. |
| 01 | [PCG Temelleri](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/01-pcg-fundamentals.md) | Fonokardiyogram, S1/S2 sesleri, örnekleme frekansı ($f_s$), Nyquist kriteri ve örtüşme (aliasing). |
| 02 | [SampleBlock ve Kaynak Soyutlaması](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/02-sampleblock-and-sources.md) | Veri kapsülleme modeli, Mock/WAV/Realtime/MCU kaynak soyutlaması ve gevşek bağlılık (loose coupling). |
| 03 | [Akış ve Kayan Pencere Tamponu](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/03-streaming-and-rolling-buffer.md) | Blok tabanlı akış, gecikme-verimlilik dengesi, sıra ve zaman damgaları, `RollingBuffer` FIFO mantığı. |
| 04 | [Sayısal Sinyal İşleme ve Filtreleme](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/04-dsp-and-filtering.md) | Butterworth bant geçiren filtre, durumsal filtreleme (`sosfilt` ve `zi`), bloklar arası süreklilik, geçici 20–600 Hz bandı. |
| 05 | [Spektral Analiz](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/05-spectral-analysis.md) | FFT, Welch PSD ve Spektrogram karşılaştırması, zaman-frekans çözünürlüğü ve canlı spektral çerçeveler. |
| 06 | [Akış Kalite Denetimi](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/06-stream-quality-monitoring.md) | `StreamQualityMonitor`, paket kaybı, sıra atlama, zaman gerilemesi ve örnekleme frekansı değişim tespiti. |
| 07 | [Test ve Doğrulama Stratejisi](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/07-testing-and-validation.md) | Ağdan bağımsız sentetik birim testler, fast mode test yürütümü ve tekrarlanabilir deney altyapısı. |
| -- | [Terimler Sözlüğü (Glossary)](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/docs/knowledge-base/GLOSSARY.md) | Biyomedikal, gömülü sistem ve DSP terimlerinin Türkçe-İngilizce tanımları. |

---

## Zorunlu Mühendislik Kuralı (Engineering Rule Going Forward)

Projenin sürdürülebilirliğini, akademik kalitesini ve savunulabilirliğini teminat altına almak için repo genelinde şu kural uygulanır:

> [!IMPORTANT]
> Projeye eklenecek her yeni majör kabiliyet veya modül aşağıdaki 4 adımı eksiksiz içermek zorundadır:
> 1. **Kod Uygulaması (Implementation):** Temiz, modüler, aşırı bağımlılıklardan arındırılmış kod.
> 2. **Otomasyonlu Birim Testleri (Automated Tests):** Harici ağa veya manuel adımlara bağlı olmayan deterministik pytest testleri.
> 3. **Mimari / Dokümantasyon Güncellemesi (Architecture Update):** `README.md` ve `docs/architecture/` güncellemeleri.
> 4. **Bilgi Bankası Gerekçelendirmesi (Knowledge-Base Explanation):** Yeni bir mühendislik konsepti, algoritma veya donanım arayüzü eklendiğinde bu bilgi bankasında tasarım gerekçesi ve alternatifleriyle belgelenmelidir.
