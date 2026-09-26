# 09 — Sinyal Edinim Oturumu Kaydı ve Yeniden Yürütme (Session Recording & Replay)

## Bu nedir?

AuscultaForge sisteminde bir **Edinim Oturumu (Acquisition Session)**; sensörden, mikrodenetleyiciden veya bench simülatöründen gelen kesintisiz `SampleBlock` akışının ham (raw), filtrelenmemiş ve üzerinde hiçbir kayıplı dönüştürme yapılmamış biçimde diske kaydedilmesini sağlayan çekirdek mimari mekanizmadır.

Her kayıt oturumu, `experiments/sessions/<session_id>/` dizini altında iki bileşenden oluşan ayrık bir veri çifti üretir:
```text
experiments/sessions/<session_id>/
├── raw.wav          # Sayısallaştırılmış ham PCG ses dalgası (IEEE 32-bit Float veya 16-bit PCM)
└── session.json     # Donanım, zamanlama, SHA-256 özeti ve akış kalite metriklerini içeren yan dosya (sidecar)
```

---

## 1. Neden İşlenmiş (Filtrelenmiş) Veri Ham Verinin Yerini Alamaz?

Biyomedikal mühendislik ve sinyal işleme sistemlerinde en kritik kural: **Ham sensör verisinin asla kalıcı olarak filtreyle ezilmemesidir.**

1. **Geri Dönülemez Bilgi Kaybı (Irreversible Loss):**
   - Sayısal bir Butterworth veya Chebyshev bandpass filtresi (örneğin 20–200 Hz), bu frekans aralığının dışındaki tüm akustik bileşenleri zayıflatır.
   - Eğer gelecekte kalp üfürümlerinin yüksek frekanslı klikleri (300–600 Hz) veya sub-audible infrasound bileşenleri (< 20 Hz) incelenmek istenirse, ham veri yok edilmişse geri getirilemez.
2. **Algoritma ve Filtre Evrimi (DSP Agility):**
   - Bugün kullanılan 4. derece Butterworth filtre katsayıları, yarın akustik fantom bench testleri sonucunda optimize edilmiş FIR veya IIR filtrelerle değiştirilebilir.
   - Ham veri saklandığı sürece, aylar önce kaydedilmiş bir hasta/fantom oturumu yeni geliştirilen filtrelerden tekrar geçirilerek karşılaştırma yapılabilir.
3. **Regülasyon ve Teşhis Denetlenebilirliği (Audit Trail):**
   - Medikal cihaz standartlarında (FDA / CE) işlenmiş veri bir "çıktı"dır; asıl yasal ve bilimsel kanıt sensörün ürettiği ham sayısallaştırılmış sinyaldir.

---

## 2. WAV + JSON Yan Dosya (Sidecar) Mimarisi

AuscultaForge, oturum verilerini tek bir devasa veritabanı veya karmaşık özel ikili format yerine endüstri standardı **WAV + JSON Sidecar** formatında saklar.

### Neden Bu Yaklaşım Seçildi?
- **Ayrık Endişeler (Separation of Concerns):** Sinyalin kendisi yüksek verimli sayısal ses formatında (`raw.wav`), sinyalin bağlamı ise insan ve makine tarafından okunabilen açık metin formatında (`session.json`) tutulur.
- **Standart Uyumluluk:** `raw.wav` dosyası harici araçlarla (Audacity, MATLAB, SciPy, PhysioNet araçları) ek hiçbir dönüştürücüye ihtiyaç duymadan açılabilir.
- **Veritabanı Bağımsızlığı:** Harici bir SQL/NoSQL veritabanı motoru (SQLite, PostgreSQL, MongoDB) kurma zorunluluğunu ortadan kaldırarak taşınabilirliği maksimize eder. Bir oturumu paylaşmak için klasörü kopyalamak yeterlidir.

---

## 3. İzlenebilirlik (Provenance) ve SHA-256 Bütünlük Koruması

Her `session.json` dosyası aşağıdaki doğrulanabilir köken (provenance) alanlarını içerir:

| Alan | Amaç | Örnek |
|---|---|---|
| `session_id` | Oturuma özgü benzersiz zaman damgalı kimlik | `session_20260926_164500_a1b2c3d4` |
| `started_at_utc` / `ended_at_utc` | ISO 8601 UTC başlangıç ve bitiş zamanları | `2026-09-26T13:45:00.123456+00:00` |
| `sample_rate_hz` | Kesin örnekleme frekansı | `4000` |
| `total_samples` / `total_blocks` | Tam örnek ve `SampleBlock` sayısı | `60000` samples / `468` blocks |
| `duration_s` | Örnek sayısına dayalı kesin süre | `15.0000` s |
| `first_sequence` / `last_sequence` | MCU/kaynak sıra numaraları | `0` / `468` |
| `raw_wav_sha256` | `raw.wav` dosyasının kriptografik SHA-256 özeti | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `git_commit_sha` | Kayıt anındaki repository HEAD commit özeti | `667daa7...` |
| `environment` | Python, NumPy, SciPy sürümleri ve işletim sistemi | `{"python": "3.11.9", "numpy": "2.4.6", ...}` |
| `stream_quality` | Düşen blok, sıra bozulması ve gecikme sayıları | `{"dropped_blocks": 0, "is_healthy": true}` |

### SHA-256 Neden Şarttır?
Dosyanın diskte bozulup bozulmadığını, üzerine yanlışlıkla yazılıp yazılmadığını veya üzerinde tahrifat yapılıp yapılmadığını matematiksel kesinlikle kanıtlar.

---

## 4. Ortasında Örnekleme Frekansı Değişen Akışların Güvenli Reddi

Bir edinim oturumu sırasında (örneğin donanımdan gelen bir komut veya arıza nedeniyle) örnekleme frekansı değişirse ($f_s = 4000 \text{ Hz} \rightarrow 2000 \text{ Hz}$):
- **Hatalı Yaklaşım:** İki farklı frekanstaki sinyalleri tek bir WAV dosyasında peş peşe yazmak. Bu durumda zaman ekseni tamamen bozulur, filtreler patlar ve yanıltıcı bir kayıt oluşur.
- **AuscultaForge Çözümü:** `SessionRecorder.record_block` frekans değişimini anında yakalar, kaydı güvenli bir şekilde keser ve `RecordingSampleRateError` istisnası fırlatır. Asla yanıltıcı tek frekanslı bir dosya üretilmez.

---

## 5. Yeniden Yürütülebilirlik (Replayability) ve Boru Hattı Uyumu

Kaydedilmiş bir oturum, AuscultaForge boru hattında birinci sınıf bir veri kaynağıdır:
```python
from pcg_core import create_session_source

# Kaydedilmiş bir oturumu doğrudan WavSource veya RealtimeWavSource olarak yükleme
source = create_session_source(session_id="session_20260926_...", realtime=True)
for block in source.blocks():
    # Canlı donanım akışıyla birebir aynı SampleBlock nesnesi
    ...
```

Bu sayede:
1. Kaydedilen bir oturum masaüstü arayüzünde (UI) canlıymış gibi baştan sona tekrar oynatılabilir.
2. Filtre parametreleri ve metrikler gerçek zamanlı olarak ayarlanabilir.

---

## 6. Oturum Kaydı ile Akustik Fantom Doğrulaması Arasındaki İlişki

Fantom doğrulama metodolojisinde (`docs/knowledge-base/08-reference-vs-capture-validation.md`):
- Hoparlörden bilinen bir referans PCG yürütülür.
- Prototip stetoskop ve ESP32-S3 bu sinyali yakalarken bir **Edinim Oturumu** başlatılır.
- Oturum tamamlandığında `experiments/sessions/<session_id>/raw.wav` elde edilir.
- Doğrulama aracı (`pcg_core.validate_capture`) referans WAV ile bu oturumun `raw.wav` dosyasını karşılaştırarak:
  - Çapraz korelasyon
  - Gecikme (delay_ms)
  - RMS kazanç oranı ve En Küçük Kareler kazancı ($g$)
  - Sinyal-Hata Oranı (SER)
  çıkarır. Oturum kaydı olmaksızın bu doğrulama adımı tekrarlanamaz.

---

## 7. 30 Saniyelik Bitirme / Jüri Savunması Özeti

> *"AuscultaForge'da kayıt mimarisi ham verinin dokunulmazlığı prensibine dayanır. DSP filtreleri asla ham sesin üzerine yazılmaz. Her oturum, 32-bit kayıpsız ham ses dalgası (`raw.wav`) ve SHA-256 kriptografik özeti, git commit hash'i, ortam sürümleri ve akış kalitesini belgeleyen bir JSON yan dosyası (`session.json`) ile arşivlenir. Bu sayede aylar sonra bile aynı kayıt yeni filtrelerle yeniden yürütülebilir ve akustik fantom deneylerinde elde edilen referans-yakalama metrikleri bilimsel olarak kanıtlanabilir kalır."*
