# 07 — Test, Doğrulama ve Tekrarlanabilirlik Stratejisi

## Bu nedir?

Bu doküman, AuscultaForge yazılım bileşenlerinin doğruluğunu, sinyal işleme algoritmalarının matematiksel kararlılığını ve veri bütünlüğünü teminat altına alan otomatik test ve deneysel doğrulama metodolojisini açıklar.

---

## Dış Bağımsızlık ve Sentetik Test Prensibi

AuscultaForge birim testleri (unit tests) iki katı kurala dayanır:
1. **Sıfır Ağ Bağımlılığı:** Testler PhysioNet veya internetten dosya indirmeye çalışmaz. İnternetsiz bir geliştirici bilgisayarında veya çevrimdışı CI/CD sunucusunda koşabilmelidir.
2. **Sentetik Determinizm:** Büyük harici kayıtlar veya ham veri setleri yerine, `tmp_path` fixture'ı ile geçici dizinlerde tam olarak bilinen frekansta (ör. 50 Hz saf sinüs) ve bilinen sürede matematiksel sinyaller üretilir. Çıktıların (örneğin tepe frekansının $50\text{ Hz}$ bulunması) kesin matematiksel toleranslarla doğrulanması sağlanır.

---

## Neden Testlerde Gerçek Zamanlı Bekleme (`time.sleep`) Yoktur?

Canlı akış test edilirken gerçek duvar saati hızında ($1\times$) çalışılsaydı:
- 35 saniyelik bir WAV testini çalıştırmak 35 saniye sürerdi.
- 10 farklı test koşusu dakikalarca bekletir ve geliştirici çevikliğini (velocity) felç ederdi.

**Çözüm:** `RealtimeWavSource` sınıfı `realtime=False` (veya CLI'da `--fast`) parametresi içerir. Algoritma duvar saati beklemesi yapmaksızın tüm akış mantığını, blok sırasını, zaman damgalarını ve tampon kaymasını CPU'nun izin verdiği en yüksek hızda (yaklaşık 0.05 saniyede) icra eder. Böylece 15+ kapsamlı test 1.5 saniyenin altında tamamlanır.

---

## Test Katmanları

```text
software/tests/
├── test_core.py         ──► SampleBlock modeli, float32 doğrulaması, temel filtre koşumu
├── test_analysis.py     ──► Mock/WAV analizi, RMS/Peak hesapları, spektrogram boyutları, Nyquist sınırı
├── test_streaming.py    ──► Kayan tampon, sıra kayıpları, tekrarlar, regresyonlar, kısa son bloklar
└── test_experiment.py   ──► Deney konfigürasyonu, SHA-256 bütünlüğü, tekrarlanabilirlik
```

---

## Gelecek Doğrulama Aşamaları: Fantom ve Donanım Doğrulaması

Yazılım hattı doğrulandıktan sonra sonraki proje fazlarında şu adımlar izlenecektir:
1. **Akustik Fantom Testleri (Acoustic Phantom):** İnsan göğüs kafesini ve doku akustik empedansını taklit eden silikon/jelatin fantom üzerinde bilinen frekansta ses kaynakları çalınarak mikrofon edinim başlığı test edilecektir.
2. **Elektronik Kalibrasyon:** MCU'nun analog ADC veya dijital I2S kanalına bilinen sinüs dalgaları verilerek SNR (Sinyal-Gürültü Oranı) ve THD (Toplam Harmonik Bozulma) ölçülecektir.

---

## İlgili Dosyalar

- Birim testleri: [`software/tests/test_core.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_core.py), [`software/tests/test_analysis.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_analysis.py), [`software/tests/test_streaming.py`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/software/tests/test_streaming.py)
- Merkezi Pytest Ayarı: [`pytest.ini`](file:///c:/Users/Ege%20%C3%87a%C4%9F%C4%B1n/Downloads/pcg_software_starter/pytest.ini)

---

## Sunumda / Savunmada 30 Saniyelik Açıklama

> *"Yazılımımızın doğruluğunu 'çalışıyor görünüyor' seviyesinde bırakmadık. Geliştirdiğimiz test paketi harici ağlara veya donanıma bağımlı olmadan, sentetik sinyallerle filtre cevabını, spektrogram hassasiyetini, tampon sınır taşmalarını ve paket kaybı tespitini otomatik olarak doğrular. 'Fast mode' altyapımız sayesinde onlarca saniyelik bir canlı akış senaryosu milisaniyeler içinde simüle edilerek saniyeler içinde tüm testler eksiksiz tamamlanır."*
