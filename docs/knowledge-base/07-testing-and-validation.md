# 07 â€” Test, DoÄŸrulama ve Tekrarlanabilirlik Stratejisi

## Bu nedir?

Bu dokÃ¼man, AuscultaForge yazÄ±lÄ±m bileÅŸenlerinin doÄŸruluÄŸunu, sinyal iÅŸleme algoritmalarÄ±nÄ±n matematiksel kararlÄ±lÄ±ÄŸÄ±nÄ± ve veri bÃ¼tÃ¼nlÃ¼ÄŸÃ¼nÃ¼ teminat altÄ±na alan otomatik test ve deneysel doÄŸrulama metodolojisini aÃ§Ä±klar.

---

## DÄ±ÅŸ BaÄŸÄ±msÄ±zlÄ±k ve Sentetik Test Prensibi

AuscultaForge birim testleri (unit tests) iki katÄ± kurala dayanÄ±r:
1. **SÄ±fÄ±r AÄŸ BaÄŸÄ±mlÄ±lÄ±ÄŸÄ±:** Testler PhysioNet veya internetten dosya indirmeye Ã§alÄ±ÅŸmaz. Ä°nternetsiz bir geliÅŸtirici bilgisayarÄ±nda veya Ã§evrimdÄ±ÅŸÄ± CI/CD sunucusunda koÅŸabilmelidir.
2. **Sentetik Determinizm:** BÃ¼yÃ¼k harici kayÄ±tlar veya ham veri setleri yerine, `tmp_path` fixture'Ä± ile geÃ§ici dizinlerde tam olarak bilinen frekansta (Ã¶r. 50 Hz saf sinÃ¼s) ve bilinen sÃ¼rede matematiksel sinyaller Ã¼retilir. Ã‡Ä±ktÄ±larÄ±n (Ã¶rneÄŸin tepe frekansÄ±nÄ±n $50\text{ Hz}$ bulunmasÄ±) kesin matematiksel toleranslarla doÄŸrulanmasÄ± saÄŸlanÄ±r.

---

## Neden Testlerde GerÃ§ek ZamanlÄ± Bekleme (`time.sleep`) Yoktur?

CanlÄ± akÄ±ÅŸ test edilirken gerÃ§ek duvar saati hÄ±zÄ±nda ($1\times$) Ã§alÄ±ÅŸÄ±lsaydÄ±:
- 35 saniyelik bir WAV testini Ã§alÄ±ÅŸtÄ±rmak 35 saniye sÃ¼rerdi.
- 10 farklÄ± test koÅŸusu dakikalarca bekletir ve geliÅŸtirici Ã§evikliÄŸini (velocity) felÃ§ ederdi.

**Ã‡Ã¶zÃ¼m:** `RealtimeWavSource` sÄ±nÄ±fÄ± `realtime=False` (veya CLI'da `--fast`) parametresi iÃ§erir. Algoritma duvar saati beklemesi yapmaksÄ±zÄ±n tÃ¼m akÄ±ÅŸ mantÄ±ÄŸÄ±nÄ±, blok sÄ±rasÄ±nÄ±, zaman damgalarÄ±nÄ± ve tampon kaymasÄ±nÄ± CPU'nun izin verdiÄŸi en yÃ¼ksek hÄ±zda (yaklaÅŸÄ±k 0.05 saniyede) icra eder. BÃ¶ylece 15+ kapsamlÄ± test 1.5 saniyenin altÄ±nda tamamlanÄ±r.

---

## Test KatmanlarÄ±

```text
software/tests/
â”œâ”€â”€ test_core.py         â”€â”€â–º SampleBlock modeli, float32 doÄŸrulamasÄ±, temel filtre koÅŸumu
â”œâ”€â”€ test_analysis.py     â”€â”€â–º Mock/WAV analizi, RMS/Peak hesaplarÄ±, spektrogram boyutlarÄ±, Nyquist sÄ±nÄ±rÄ±
â”œâ”€â”€ test_streaming.py    â”€â”€â–º Kayan tampon, sÄ±ra kayÄ±plarÄ±, tekrarlar, regresyonlar, kÄ±sa son bloklar
â””â”€â”€ test_experiment.py   â”€â”€â–º Deney konfigÃ¼rasyonu, SHA-256 bÃ¼tÃ¼nlÃ¼ÄŸÃ¼, tekrarlanabilirlik
```

---

## Gelecek DoÄŸrulama AÅŸamalarÄ±: Fantom ve DonanÄ±m DoÄŸrulamasÄ±

YazÄ±lÄ±m hattÄ± doÄŸrulandÄ±ktan sonra sonraki proje fazlarÄ±nda ÅŸu adÄ±mlar izlenecektir:
1. **Akustik Fantom Testleri (Acoustic Phantom):** Ä°nsan gÃ¶ÄŸÃ¼s kafesini ve doku akustik empedansÄ±nÄ± taklit eden silikon/jelatin fantom Ã¼zerinde bilinen frekansta ses kaynaklarÄ± Ã§alÄ±narak mikrofon edinim baÅŸlÄ±ÄŸÄ± test edilecektir.
2. **Elektronik Kalibrasyon:** MCU'nun analog ADC veya dijital I2S kanalÄ±na bilinen sinÃ¼s dalgalarÄ± verilerek SNR (Sinyal-GÃ¼rÃ¼ltÃ¼ OranÄ±) ve THD (Toplam Harmonik Bozulma) Ã¶lÃ§Ã¼lecektir.

---

## Ä°lgili Dosyalar

- Birim testleri: [`software/tests/test_core.py`](../../software/tests/test_core.py), [`software/tests/test_analysis.py`](../../software/tests/test_analysis.py), [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py)
- Merkezi Pytest AyarÄ±: [`pytest.ini`](../../pytest.ini)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"YazÄ±lÄ±mÄ±mÄ±zÄ±n doÄŸruluÄŸunu 'Ã§alÄ±ÅŸÄ±yor gÃ¶rÃ¼nÃ¼yor' seviyesinde bÄ±rakmadÄ±k. GeliÅŸtirdiÄŸimiz test paketi harici aÄŸlara veya donanÄ±ma baÄŸÄ±mlÄ± olmadan, sentetik sinyallerle filtre cevabÄ±nÄ±, spektrogram hassasiyetini, tampon sÄ±nÄ±r taÅŸmalarÄ±nÄ± ve paket kaybÄ± tespitini otomatik olarak doÄŸrular. 'Fast mode' altyapÄ±mÄ±z sayesinde onlarca saniyelik bir canlÄ± akÄ±ÅŸ senaryosu milisaniyeler iÃ§inde simÃ¼le edilerek saniyeler iÃ§inde tÃ¼m testler eksiksiz tamamlanÄ±r."*
