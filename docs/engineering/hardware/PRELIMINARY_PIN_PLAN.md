# Ön PCB/pin planı — fiziksel bağlantı onayı DEĞİLDİR

Satıcı DSTK22852 / hedef WROOM-1-N16R8. [Kart dosyası](BOARD_DOSSIER_DSTK22852.md)
ve [INMP441 planı](INMP441_FIRST_ACQUISITION.md) kaynakları tekrar incelendi.
Fotoğraf kesin PCB revizyonu ve USB güzergâhı vermiyor; teslim kartının iki yüzüyle
eşleştirme gerekir. Satıcı ürünü modül kapasitesini belirtir, konnektör şeması sağlamaz.

| Mikrofon pini | Mantıksal ağ | Durum |
| --- | --- | --- |
| VDD/VCC | Ölçülmüş regüle 3V3 | Gerçek breakout etiketi doğrulanmalı; 5V/VBUS ASLA |
| GND | ESP GND | Süreklilik ölçümü gerekli |
| SCK/BCLK | GPIO4 çıkış | PROVISIONAL; header ve çakışma doğrulanmalı |
| WS/LRCLK | GPIO5 çıkış | PROVISIONAL |
| SD/DOUT | GPIO6 giriş | PROVISIONAL |
| L/R | GND, sol slot | Gerçek modül ve sol firmware slotu eşleştirilmeli |

19/20 USB; 26..37 bellek (N16R8 35..37 dahil); 0/3/45/46 strap;
43/44 UART debug; 38/48 ve revizyona bağlı47 başlangıç planına alınmaz.
48 kHz WS / stereo32 için nominal 3.072 MHz BCLK; ölçüm yapılmadı.

Enerji kes → lehim/başlık yönü → GND/süreklilik/kısa devre kontrolü → önce mikrofon
ayrıyken 3.3V ölçümü → enerjiyi tekrar kes → onaylı bağlantı → tek USB güç kaynağı.
I2S profile varsayılan kapalıdır. Pinleri GUI'de seçmek fiziksel onay yerine geçmez.
Header lehimsizse uygun lehim aracı ve deneyimli kişi olmadan gevşek pin kullanmayın.

**PAM8403 ayrı deneydir:** BTL hoparlör çıkışlarının iki ucu da sürülür; negatif
hoparlör çıkışını ortak toprağa veya topraklı osiloskop klipsine bağlamayın. Mikrofon
dijital pinlerine hiçbir hoparlör çıkışı bağlanmaz. AUX/kablo kesimi onaylı ayrı
şema olmadan yapılmaz. İlk G1/G2 için PAM8403/exciter gerekmez.
