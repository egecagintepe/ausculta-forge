# İlk laboratuvar: 2–3 saatlik plan

Süreler planlama payıdır, tamamlanma garantisi değildir. Donanım kabulü ölçümle belirlenir.

| Pay | Ege + Kaan işi | Kaydedilecek çıktı / durma koşulu |
| --- | --- | --- |
| 0–20 dk | Kart/modül/konnektör fotoğrafı, tek USB ile Windows kimliği | H0 formu; belirsiz güç/route varsa flash yok |
| 20–60 dk | Laptop doctor/build, ROM kimlik, açık flash onayı, UART boot | Manifest, first-flash, board_identity, boot; başarısızsa recovery/log |
| 60–120 dk | Üretim host HELLO, tam fiziksel G1, tekrar STOP/start | PHYSICAL_G1_PASSED için tüm gate'ler; hata ZIP'i de korunur |
| 120–180 dk | Koşullu source0, lehim/pin/3.3V/clock, quiet ve kontrollü ses kaydı | Raw WAV/session, qualify JSON, DMA/drop/clock kanıtı; koşullar yoksa G2 yok |

Fallback: build/USB hatasında kalan süreyi tekrar üretilebilir komut/versiyon/boot
kanıtına ayırın. Sorunu çözmek için ek devre bağlamayın. G1 tamamlanıp G2 kalırsa
günün mühendislik hedefi başarıyla ilerlemiştir; fiziksel G2 yine NOT_EXECUTED kalır.

## Devir ve sorumluluk

Ege: host/firmware entegrasyonu, Windows komutları, kayıt/DSP, hash/rapor.
Kaan: fiziksel montaj, lehim/süreklilik, mikrofon yerleşimi ve sonraki akustik/phantom.
Ozan: müsaitken protokol/acquisition akran kontrolü ve bağımsız test.
Bunlar görev planıdır; yapılmış katkı beyanı değildir. Yeni hata sahibi kişisel
kusurla değil katmanla seçilir: USB/FW, host/kayıt, elektrik/mekanik, bilimsel analiz.

## Parça kontrolü

| Sınıf | Durum / gereksinim |
| --- | --- |
| AVAILABLE | Fiziksel teslim ve adetleri ekip saymalı; geliştirme ortamı teslim kanıtı değildir |
| Sipariş bilgisi | ESP32-S3, INMP441, PAM8403, exciter ve diğer elektronik parçalar sipariş edilmiş; teslim/adet teyitsiz |
| REQUIRED FOR G1 | Laptop kurulumu, doğru ESP32-S3, veri USB kablosu, gerektiğinde doğrulanmış UART yolu |
| REQUIRED FOR G2 | INMP441, sağlam/lehimli başlıklar, jumper, multimetre; clock kontrolü için erişilebilir scope/logic analyzer |
| REQUIRED FOR PHANTOM | Onaylı stimulus/amfi/exciter planı, referans/ölçüm araçları, mekanik kuplaj ve geometri |
| NOT YET PURCHASED | Chestpiece ve silikon/jel kuplaj bileşenleri |

Lehim aleti ve tecrübeli montaj desteği mevcut mu ayrıca teyit edin. İlk G1 için
yeni parça önerilmez. AUX veya diğer satın alınmış kablolar onaylı şema olmadan kesilmez.
