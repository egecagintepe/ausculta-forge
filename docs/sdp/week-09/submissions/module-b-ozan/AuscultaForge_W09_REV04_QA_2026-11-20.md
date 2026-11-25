> [!NOTE]
> **Tarihsel Belge Koruma ve Entegrasyon Notu (Historical Record & Integration Notice):**  
> Bu belge, 20 Kasım 2026 tarihinde Ozan (Modül B) tarafından hazırlanan **REV04 / 04-QA nihai yerel inceleme ve denetim raporudur**.  
> Belgedeki *"GitHub'a commit/push yapılmadı"* ve *"GitHub hedef yolu docs/sdp/week-09/submissions/module-b-ozan/"* ifadeleri yerel hazırlık anındaki tarihsel durumu yansıtmakta olup; bu belge PR #36 (`feature/rev04-evidence-integration`) dalına kanonik kaynak olarak dahil edilmiş ve `main` ile uzlaştırılmıştır.  
> Aşağıda yer alan *"Kapanmamış GitHub WAV SHA-256 uyumsuzluğu"* bölümündeki gözlem, belgenin yazıldığı sırada `origin/main` üzerinde açık olan durumu belgelemektedir. Bu uyumsuzluk, PR #36 dalında ikinci laboratuvar ZIP'i (`100114Z.zip`, 148/148 `SHA256SUMS.txt` tam eşleşme), oturum JSON kanıtları ve orkestratör durum dosyasıyla doğrulanarak çözümlenmiştir (ayrıntılar için ilgili bölüm altındaki Entegrasyon Notuna bakınız). Düzeltilmiş SHA değerleri korunmaktadır.

# AuscultaForge — REV04 / Week 09 QA Düzeltme ve Açık Kanıt Raporu

**Tarih:** 20 Kasım 2026 — Week 09 (16–22 Kasım 2026)  
**Durum:** 20 Kasım 2026 itibarıyla son QA onaylı yayın paketi; hedef GitHub yolu `docs/sdp/week-09/submissions/module-b-ozan/`.

## Güncel dosyalar (tek geçerli QA seti)

1. **Excel:** `W09_B_procurement-bom-test_REV04_2026-11-20.xlsx` — **17 sekme**.
2. **Word:** `W09_B_system-design-technical-specification_REV04_2026-11-20.docx` — **38 sayfa** (görüntüleme testi).
3. **QA raporu:** `AuscultaForge_W09_REV04_QA_2026-11-20.md`.

Güncel dosyalar `W09_B_` önekiyle adlandırılmıştır; `REV04` yalnız belge sürümüdür. Tarihsel Week 04 / Rev03 içerikleri korunmuştur. `REV03` tarihli kayıtlar yalnız önceki tasarım/sipariş kararlarının **tarihsel kanıtı** olarak tutulmuştur. `REV04-W09-QA` küçük uyum düzeltmesidir; yeni laboratuvar deneyi gerçekleştirildiğini iddia etmez.

## Ekran görüntüsündeki 6 bulgu ve yapılan düzeltmeler

| No. | İlk inceleme bulgusu | Düzeltilen yer ve sonuç |
|---|---|---|
| 1 | Word/Böl.17, Ek D `[R15]` ve QA notunda farklı dosya adları | Word **Bölüm 13** ve **17** güncel Excel QA dosyasına; Ek D `[R15]` güncel workbook adına yönlendirildi. QA raporundaki ve Excel `Rev04_Acik_Konular` içindeki güncel dosya adları eşitlendi. Eski W03/REV03 referansları **tarihsel olduğu yerlerde** korundu. |
| 2 | 12×12 cm plaket yok; `B-01-` bozuk ID; toplam adet/ebat uyuşmazlığı | Excel `Sipariş_Kayıt!A18:K19`: **B-01a** = 1×12×12 cm, **35,35 TL** önceki sepet fiyatı; **B-01b** = 2×7×9 cm, **2×45 = 90 TL tahmini**. Artık iki kalem arka arkaya ve ayrı formüllü. `Satın_Alma!A17:P17` **B-01 (grup)** 1+2=**3 adet**; açıklama ve `P17` ilgili satırlarla uyumlu. |
| 3 | Satın_Alma A-01/A-09 hücrelerinde eski `BEKLE` / 'sipariş öncesi' notları | `Satın_Alma!O5:P5` ve `O13:P13` yeni durum: **ALINDIĞI BİLDİRİLDİ**, ancak **fatura/nihai ödeme/teslim ve fiziksel uyum/kür doğrulaması açık**. Galena **283 TL** ve RTV-2 **350 TL** yalnız kullanıcı ekran fiyatıdır. Eski Medikaltec/3 mm silikon levha adayları tarihsel alternatif olarak ayrı tutuldu. |
| 4 | ANA_BOM `Durum` boş veya 18 Kasım deneyinden önceki durumda | `ANA_BOM!I5:J5` (ESP32), `I7:J7` (INMP441), `I34:J36` (M1/M2/M3) güncellendi. En az bir ESP32-S3+INMP441 **18 Kasım fiziksel kısa süreli testi** geçti; diğer cihazların test/teslimi varsayılmadı. M1/M2 alındığı bildirildi fakat teslim/fatura teyitsiz; M3 (rijit çerçeve/ultrason jeli) **açık**. |
| 5 | Word içindekiler, Böl.13/17.3, Ek B'de eski anlatım | İçindekilerde Ek E ve Ek F **ayrı satır**; Böl. 13 güncel `Test_Matrisi` dosyasını gösterir, Böl.17.3 yeni kullanıcı-alım bildirimini ve gerçek mikrofon testini ayırır. Ek B **D-003, D-004, D-005, D-006, D-026** 18 Kasım'da doğrulanan I²S GPIO4/5/6, USB CDC/Profile B/CRC ve veri bütünlüğüyle düzeltildi. **Bağımsız saat, uzun test ve kalibrasyon** hâlâ açık. Böl.19 ve Ek E eski kayıtları güncel durumla karıştırmamak için açıklığa kavuşturuldu. |
| 6 | QA sekme sayısı ve T-AUD-05 statü çelişkisi | Gerçek sekme sayısı **17**; `Test_Matrisi!I14` ve `W09_Durum!D14` **aynı ifade**: `PENDING — W09 (20.11); bağımsız fantom S1/S2 ve kaynak–kayıt fiziksel testi yapılmadı`. Mikrofon fonksiyonel G2 sonucu bu resmî Week 09 fantom kapısıyla birleştirilmedi. |

## Maliyet uzlaştırması: çifte kayıt yok

| Açıklama | Tutar |
|---|---:|
| Önceki Rev03 tedarikçi baz toplamı | **3.613,21 TL** |
| Bu bazın içinde yer alan teyitsiz 2×7×9 cm plaket fiyat tahmini | **90,00 TL** |
| B-01a 12×12 cm plaketin eski sepet fiyatı (35,35 TL) | **Önceki bazın zaten içinde; ayrıca eklenmez** |
| Galena çift taraflı stetoskop ekran fiyatı | **283,00 TL** |
| RTV-2 silikon + katalizör 500 g ekran fiyatı | **350,00 TL** |
| Yeni bildirilen ürünlerin ekran fiyatları toplamı | **633,00 TL** |
| **Rev04 geçici toplam (90 TL tahmin dahil)** | **4.246,21 TL** |
| **90 TL eski Motorobit tahmini hariç alternatif toplam** | **4.156,21 TL** |

Bu tutarlar **banka/fiş bazlı gerçek harcama toplamı değildir**. Ekran görüntülerindeki fiyatlar satın alma bildirimi olarak kaydedildi; indirim, kargo, KDV gösterimi, iade ve nihai ödeme bilgileri ayrıca teyit gerektirir. `Gerçek_Sipariş_Rev04` tedarikçi toplamları geçici ana bazdır; `Satın_Alma` veya `Sipariş_Kayıt` alt satırlarını yeniden toplayıp bu toplamın üstüne eklemeyin.

## Gerçek Week 09 ilerlemesi — 20 Kasım fotoğrafı

- **PASS (fonksiyonel alt test):** 18 Kasım fiziksel G1 pre/post testleri; gerçek ESP32-S3 + INMP441 üzerinde 48 kHz, toplam **4 ayrı 10 saniye**, **1.920.000 kaydedilmiş örnek**, **0 akış-içi örnek kaybı**. Bunlar **30 dakika kesintisiz çalışma** değildir.
- **Güç ve kablolama:** VDD **3,28 V** operatör beyanı, multimetre fotoğrafı eksik; SCK GPIO4, WS GPIO5, SD GPIO6, L/R=GND sahada kullanıldı. Bağımsız osiloskop/logic analyzer zamanlama kanıtı eksik.
- **DMA kapanışı:** `post_target_drained_samples=256` hedef sonrası tampon boşaltmadır; kaydedilmiş akışta kayıp olarak sayılmaz.
- **Akustik uyarım:** 23,2 dB ile 8,0 dB **farklı oturumların bağıl seviyeleridir**; mutlak kalibre akustik SNR değildir. İlk güçlü uyaran kaydında **%0,2775** yakın kırpılma var; düşük ses seviyeli tekrar açık.
- **PENDING (resmî Week 09 fantom kapısı):** Galena + kürlü RTV-2 + 30 mm/12 Ω exciter + PAM8403 üzerinden **bilinen PCG kaynak WAV'ın fantomda oynatılması, gerçek kaynak–kayıt hizalanması ve S1/S2 doğrulaması** henüz yapılmadı.
- **Diğer açıklar:** 20–500 Hz ölçülmüş frekans cevabı (özellikle 20–60 Hz), ≥30 dk USB, analog Kingstate/MCP6022 AFE gürültü/kazanç/bant genişliği ve referans kalibrasyon.

### Kapanmamış GitHub WAV SHA-256 uyumsuzluğu

Yerel laboratuvar ZIP içindeki listelenmiş **148/148** dosya SHA-256 kontrolü geçiyor. Ancak GitHub `RETURN_EVIDENCE_SUMMARY.json` dosyasında aynı oturum adlarına karşılık gelen son iki WAV hash'i farklı görünüyor. Bu durum **doküman hatası gibi sessizce silinmedi**; Ege ile gerçek RAW WAV dosyalarının sürümü/provenance uzlaştırılmalı. Tekrar GitHub'a yüklemeden önce gereken kanıt kontrolüdür.

- `session_20261118_094939_4888e670`: ZIP `733de8fdd1f722a7a6be9e17d354261561da53852d9aa5a6c691cd9503c3c857`, GitHub özet `6662e737c3da3fe43fcbaab2be77648356a59960ff7b5d204787f71cbef8c1fa`.
- `session_20261118_100102_4e58ac08`: ZIP `26c78582df26bcd209c1f051f09aca19c8462b9fc7067cd30a0a59eba57faa33`, GitHub özet `1381dcce8a1feefc0516709848f075da34bdf88f3957bf8e5c26f784e2ea4169`.

> [!IMPORTANT]
> **Entegrasyon Sonrası Durum Notu (PR #36 Çözümü):**  
> Ozan'ın yukarıdaki tespiti, belgenin yazıldığı tarihte `main` dalındaki (`8445eea`) `RETURN_EVIDENCE_SUMMARY.json` dosyasında bulunan kopyalama hatasını doğru biçimde yakalamıştır.  
> Bu PR (#36) kapsamında yapılan bağımsız adli denetimde:
> 1. `AuscultaForge_Lab_Return_Kaan_Ozan_20261118_100114Z.zip` paketi 148/148 dosya bazında bit-for-bit doğrulanmıştır.
> 2. `RETURN_PACKAGE_MANIFEST.json` dosyasının yalnızca ilk iki oturumu (`091909` ve `093225`) kapsadığı; 3. ve 4. oturumların (`094939` ve `100102`) ise laboratuvar akışında sonradan alındığı tespit edilmiştir.
> 3. Bu son iki oturumun gerçek fiziksel WAV dosyalarının SHA-256 değerlerinin ZIP içindeki `SHA256SUMS.txt`, oturum JSON dosyaları (`session_stimulus_4888e670.json` ve `session_stimulus_4e58ac08.json`) ve orkestratör durum dosyası (`wednesday_20261118_state.json`) ile tam olarak uyuşan **`733de8fdd1f722a7a6be9e17d354261561da53852d9aa5a6c691cd9503c3c857`** ve **`26c78582df26bcd209c1f051f09aca19c8462b9fc7067cd30a0a59eba57faa33`** olduğu kanıtlanmıştır.
> 4. Dolayısıyla PR dalında `RETURN_EVIDENCE_SUMMARY.json` ve `PHYSICAL_G2_ACCEPTANCE_REPORT.md` dosyalarındaki hatalı değerler düzeltilmiş olup, düzeltilmiş gerçek SHA değerleri korunmaktadır.

## QA kontrolleri ve teslim sınırı

- Excel **17 sekme ve 57 formül**; `Sipariş_Kayıt!G18=35,35`, `G19=90`, `Gerçek_Sipariş_Rev04!D17=4.246,21`, `D18=4.156,21`, `Test_Matrisi!I14` ile `W09_Durum!D14` uyumlu. 20 Kasım son kontrolünde `Test_Matrisi!I8/I10/I16/I17` de Week 8'den sarkan ve yalnız kısa akışla kısmen doğrulanan deneyleri açıkça belirtir.
- XLSX yeniden içe alınıp ana aralıklar incelendi; `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!` aramasında hücre eşleşmesi bulunmadı.
- Word yeniden PDF/PNG olarak çizdirildi; **38 sayfa** üretildi. İçindekiler, revizyon tablosu, Böl.13/17, Ek B/D ve son Ek F.5–F.6 bölümleri görsel kontrol edildi. Ek F yeni içeriktir; geçmiş sayfaların yerleşimi mümkün olduğunca korundu.
- GitHub Week 09 yayın hedefi: `docs/sdp/week-09/submissions/module-b-ozan/`. Yayınlanan commit/PR bilgisi bu statik QA notundan ayrı doğrulanacaktır.

**Onay öncesi dört açık teyit:** 7×9 cm plaketlerin nihai fiyat/dekontu, Galena/RTV-2 gerçek ödeme ve teslim bilgileri, fiziksel fantom montaj/PCG testi, GitHub son iki WAV hash uzlaşması. Bu kanıtlar gelmedikçe `ALINDIĞI BİLDİRİLDİ` / `PENDING` notları bilinçli olarak korunur.
