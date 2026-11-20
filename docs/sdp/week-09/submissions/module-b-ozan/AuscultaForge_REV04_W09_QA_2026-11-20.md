# AuscultaForge | REV04 / WEEK 09 (20 Kasım 2026) kontrol notu

**Aktif hafta:** **Week 09 = 16–22 Kasım 2026**. Bu belge, 20 Kasım Cuma durumunu gösterir. 18 Kasım fiziksel INMP441 G2 gerçekleşmesi Week09 içinde tamamlanan **alt test**tir; resmî Week09 akustik fantom üzerinden tanınabilir S1/S2 ve kaynak–kayıt sayısal kıyası **PENDING**. Week08'den kalan 30 dakikalık sürekli akış ve 20–500 Hz transfer cevabı testleri de PENDING'dir. Gelecekteki Week10–12 hedefleri bu haftanın gerçekleşeni gibi yazılmadı.

## Week 09 modül durumu

| Modül | W09 hedefi | 20 Kasım kanıtlı durum | Kalan iş |
|---|---|---|---|
| A — Kaan | Fantom üzerinde tanınabilir S1/S2 | 18 Kasım mikrofon breadboard/akustik uyaran PASS; fantom yok | RTV-2 kür/katman, stetoskop kuplajı, PAM8403/exciter üzerinden bilinen PCG S1/S2 |
| B — Ozan | Kayıpsız, doğru zamanlı, kırpılmasız akış | 4×10 sn G2 ve G1 pre/post veri bütünlüğü PASS; ilk uyaran %0,2775 near-clip | Düşük sesli/kırpılmasız fantom akışı; ayrı regüle 5 V/BTL kontrol; ≥30 dk eski W08 işi |
| C — Ege | Kaynak PCG-kayıt sayısal karşılaştırma | Gerçek INMP441 ses analizi var; 23,2 dB ve 8,0 dB farklı oturum | Fiziksel fantom playback hizalama/NCC/coherence/S1-S2; GitHub son iki WAV hash uyumu |

**Değiştirilen belgeler:** `W04_B_procurement-bom-test_REV04_W09_2026-11-20.xlsx` içinde yeni `W09_Durum` sekmesi ve Week 09 tarihli mevcut test/aksiyon notları; `W04_B_system-design-technical-specification_REV04_W09_2026-11-20.docx` içinde açık Week 09 kapsam açıklaması ile Ek F.5–F.6. Önceki REV03 baz, tutarlar ve 18 Kasım verileri korunmuştur.

**Akademik tarih politikası:** 20 Kasım itibarıyla güncel hafta 09'dur. 23–29 Kasım Week10 geleceğe ait takip planıdır; W09 hedefi geçemediyse bunun tarihi ve gerekçesi ayrıca raporlanacaktır. Ders kapısı başarı iddiası yoktur.

---

# AuscultaForge | REV04 inceleme, fiyat uzlaştırma ve açık işler

**İnceleme tarihi:** 20 Kasım 2026  
**İncelenen kaynaklar:** `W04_B_procurement-bom-test_REV03(4).xlsx`, `W04_B_system-design-technical-specification_REV03(4).docx`, `AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip`, iki ürün ekran görüntüsü ve GitHub `egecagintepe/ausculta-forge` 18 Kasım kanıt dizini.  
**GitHub durumu:** Hiçbir commit, push veya PR açılmadı. Bu dosyalar kullanıcı kontrolüne sunulan REV04 taslaklarıdır.

## 1. Satın alma revizyonu

| Kalem | Model / kaynak | Adet | Ekranda görülen fiyat | Doğrulama seviyesi |
|---|---|---:|---:|---|
| A-01 | Galena Çift Taraflı Steteskop Profesyonel Yetişkin, Trendyol satıcı MEDICATION | 1 | 283,00 TL | Kullanıcı satın aldığını bildirdi; ürün ekranı var, ödeme/fatura/teslim kanıtı yok |
| A-09 | AnkaHobiMarket RTV-2 kalıp silikonu + katalizör, yarı şeffaf, 5 Shore, 500 g | 1 | 350,00 TL | Kullanıcı satın aldığını bildirdi; ürün ekranı var, ödeme/fatura/teslim kanıtı yok |
| **Yeni iki ürün** | | | **633,00 TL** | Gözlemlenen ürün ekran fiyatlarının toplamı |

* Rev03 önceki çalışma toplamı: **3.613,21 TL**. Burada Motorobit 2×7×9 cm plaket için **90,00 TL** fatura ile henüz teyit edilmemiş fiyat tahmini bulunur.
* **Güncel provizyonel toplam = 3.613,21 + 350,00 + 283,00 = 4.246,21 TL.** İki Trendyol siparişinin fiilen ödenen tutarı, kargo/indirim/kupon/vergi gösterimi ayrıca teyit edilmelidir.
* **90 TL eski tahmin çıkarılırsa alternatif baz = 4.156,21 TL.** Bu da tamamı fatura ile doğrulanmış gerçek harcama demek değildir.
* Rev03'ün A-01 Medikaltec 679,99 TL ve A-09 hazır 3 mm silikon levha 1.173,00 TL fiyatları **tarihsel aday** idi. Yeni Galena/RTV-2 bunların yerine güncel satın alma bildirimi olarak işlendi; iki versiyon birden satın alım maliyetine eklenmedi.
* RTV-2 döküm kiti **ultrason jeli değildir** ve **hazır 3 mm silikon levha değildir**. Katman geometrisi ve mekanik davranış ölçümle belirlenecek.

## 2. 18 Kasım fiziksel kanıt kontrolü

| Deney | ZIP içeriği / doğrulama | Karar |
|---|---|---|
| `SHA256SUMS.txt` | 148/148 listelenen dosya SHA-256 değeri doğrulandı | **PASS** — ZIP'in kendi içindeki listeye göre |
| G1 flash öncesi | 480.000 örnek, 1.875 frame, 0 in-stream loss | **PASS** |
| G1 flash sonrası | 480.000 örnek, 1.875 frame, 0 in-stream loss | **PASS** — dual-mode G1 çalışıyor; rollback backup binary'sine ayrı dönüş testi değil |
| G2 INMP441 | Quiet + stimulus1 + stimulus2 + stimulus3, her biri 48 kHz × 10 saniye × 480.000 örnek | **PASS** — fiziksel dijital veri edinimi |
| Fiziksel ray | 3,28 V, Agilent U1232A; operatör beyanı | **KISMİ** — multimetre ekran fotoğrafı eksik |
| Pin bağlantısı | SCK→GPIO4, WS→GPIO5, SD→GPIO6, L/R→GND | **Fonksiyonel PASS**; alt akustik port makro ve harici scope clock ölçümü eksik |
| DMA kapanışı | `generated_samples=480256`, `fully_queued_samples=480000`, `dropped_samples=256`, `post_target_drained_samples=256`, `in_stream_dropped_samples=0` | **Açıkça ayrıldı** — 256 kapanış örneği, kayıt akışı içinde kayıp değil |
| İlk uyaran | 20–500 Hz göreli güç oranı 23,2 dB; yaklaşık %0,2775 >0,98 FS near-clipping | **Koşullu** — gerçek akustik SNR/sensitivity kalibrasyonu değil |
| Son uyaran | ZIP `wednesday_g2_comparison.json` son karşılaştırma 8,0 dB | **PASS (fonksiyonel)** — 23,2 dB ile aynı oturum/değişmez sensör performansı sanılmamalı |
| Akustik fantom S1/S2 | Bilinen kalp WAV kaynak-kayıt eşleştirmesi yok | **YAPILMADI** |
| ECM/analog AFE | Kısa devre giriş noise floor, gain, bandwidth ve ADC kıyası yok | **YAPILMADI** |
| ≥30 dakika USB | 4 ayrı 10 saniyelik deneme var, tek kesintisiz 30 dk yok | **YAPILMADI** |

### Ciddi kanıt tutarsızlığı — GitHub WAV SHA'ları

ZIP arşivinin gerçek `raw.wav` dosyalarını bağımsız SHA-256 ile hesapladım; arşivdeki 148 digest tutuyor. Ancak GitHub `experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json` dosyasındaki **son iki ses kaydı digest'i ZIP ham WAV dosyalarıyla eşleşmiyor**. Oturum adları aynı:

| Oturum | ZIP gerçek `raw.wav` SHA-256 | GitHub özetindeki SHA-256 |
|---|---|---|
| `session_20261118_094939_4888e670` | `733de8fdd1f722a7a6be9e17d354261561da53852d9aa5a6c691cd9503c3c857` | `6662e737c3da3fe43fcbaab2be77648356a59960ff7b5d204787f71cbef8c1fa` |
| `session_20261118_100102_4e58ac08` | `26c78582df26bcd209c1f051f09aca19c8462b9fc7067cd30a0a59eba57faa33` | `1381dcce8a1feefc0516709848f075da34bdf88f3957bf8e5c26f784e2ea4169` |

**Gerekli işlem:** Ege ile doğru ham WAV/bundle sürümü karşılaştırılmalı; GitHub özetinde hangi dosyanın hash'inin gösterildiği açıklanmalı ve gerekirse özet düzeltilmeli. **Ham WAV'leri değiştirmeyin veya tutarsızlığı sessizce yok etmeyin.** İlk iki oturum hash'i eşleşiyor.

## 3. Word ve Excel'de yapılanlar

**Excel —** Rev04 güncel maliyet tablosu eklendi (`Gerçek_Sipariş_Rev04`); `Sipariş_Kayıt`, `Satın_Alma`, `Sipariş_Hazırlık`, `ANA_BOM`, `Dönüştürücü_Karşılaştırma` ve `NOTLAR` güncellendi. `Test_Matrisi` mevcut test ID'leri korunarak fiilî G1/G2 sonuçlarıyla revize edildi; **mikrofonun çalışması** ile **dersin fantom G2 kapısı** ayrıldı. `Rev04_G2_Kanit`, `Rev04_Acik_Konular` eklendi; `Revizyon_Gecmisi` Rev04 satırı açıldı. Rev03 tarihsel sipariş sayfası değiştirilmedi. 16 çalışma sayfası, 57 formül düğümü, belirgin formül hatası yok; toplamlar formüllerle **4.246,21 / 4.156,21 TL** veriyor.

**Word —** `DSS-SYS-001 REV04` doküman kimliği, 20.11.2026 tarihi ve revizyon geçmişi güncellendi. Saha pin eşleşmesi, çalışan USB CDC/Profile B protokolü, G1/G2 fonksiyonel sonuçları, yeni malzeme ve fiyatlar güncellendi. 18 Kasım kanıtlarının sınırlarını anlatan yeni **Ek F** eklendi; eski Rev03 Ek E satın alma tablosu **tarihsel baz** olarak korunarak double-count önlendi. Çıktı 36 sayfa olarak yeniden işlendi, sayfa arası gereksiz boşluk kaldırıldı.

## 4. Sonraki laboratuvarda dikkat edilecek kapılar

1. **Elektriksel emniyet:** PAM8403, ESP32-S3 GPIO'larından değil, doğru kutuplu bağımsız ve regüle 5 V kaynaktan beslenecek. PAM8403 köprü tipi (BTL) hoparlör `OUT−` uçları asla GND'ye veya topraklı osiloskop şase klipsine bağlanmayacak. INMP441 VDD yalnız güvenli 3,3 V.
2. **Kimyasal/mekanik:** RTV-2'nin tam marka/sürüm etiketi, katalizör oranı, SDS, kür koşulu ve son sertleşme doğrulanacak; ayrı küçük numunede test edilmeden elektronik, akustik port veya stetoskop diyaframı üstüne dökülmeyecek. Farklı ürünlerin %2–4 oranları otomatik taşınmayacak. Ultrason jeli ve rijit fantom çerçevesi alımı/ağırlığı açık.
3. **Kaan:** Galena stetoskop başlığının diyafram/çan çapları, 30 mm/12 Ω exciter yerleşimi, silikon kalınlığı/gerginlik, baskı/kuplaj geometrisi çizimle sabitlenecek; referans ölçüm yöntemi seçilecek.
4. **Ozan:** PAM8403 güç kaynağı, AUX giriş, BTL tek kanal ve 12 Ω exciter kablolaması için enerjisiz kontrol; sıcaklık/bozulma düşük düzey testleri; ölçüm fotoğrafları. UART/CDC portu lab bilgisayarında yeniden keşfedilecek.
5. **Ege:** Bilinen CirCor WAV'in doğru örnekleme ve hoparlör çıkışı, senkron marker/cross-correlation, USB raw WAV ve sayısal kaynak-kayıt kıyası. Mevcut firmware test süresi sınırı nedeniyle ≥30 dk dayanıklılık için ayrı firmware/protokol hazırlığı gerekiyor.
6. **Kapanış testleri:** `T-AUD-05` (fiziksel fantom S1/S2), `T-AUD-01/02/03/04` (LF cevap, kalibrasyon, tekrar, 50 Hz), `T-AUD-06` (ECM/MEMS kıyası), `T-USB-01/T-PKT-01` (≥30 dk), `T-LAT-01` (latency), PWR rail noise ve malzeme tekrarlanabilirliği.

## 5. Kaynak bağlantıları

- GitHub G2 kabul: https://github.com/egecagintepe/ausculta-forge/blob/main/docs/engineering/release/WEEK9_18NOV2026_PHYSICAL_G2_ACCEPTANCE.md
- GitHub kanıt özet: https://github.com/egecagintepe/ausculta-forge/blob/main/experiments/hardware/team_2026-11-18/RETURN_EVIDENCE_SUMMARY.json
- RTV-2 ürün ilanı: https://www.trendyol.com/ankahobimarket/rtv-2-kalip-silikon-katalizor-500-gr-5-shore-yari-seffaf-p-244791941
- Galena ürün ilanı: https://www.trendyol.com/galena/cift-tarafli-steteskop-profesyonel-yetiskin-p-62239526
- Galena resmî çift taraflı ürün: https://www.galena.com.tr/tr/urunler/hastane-urunleri/steteskop/147/steteskop-cift-tarafli.html

**Son karar:** REV04 Word/Excel, kullanıcının incelemesi için hazır. Eksik faturalar ve GitHub hash uyuşmazlığı giderilene dek satın alma tutarı **geçici** ve fiziksel S1/S2 fantom testi **açık** kalmalıdır. GitHub'a kullanıcı onayından önce dosya yüklenmeyecek.
