# Fiziksel onay listesi — H0 ve mikrofon öncesi

Bu form boş bir plan; hiçbir kutu geliştirme bilgisayarında tamamlanmış sayılmaz.
Ege kanıt dosyasını, Kaan fiziksel incelemeyi birlikte kaydeder; Ozan uygunken kontrol eder.

- [ ] Ön/arka fotoğraf; ürün poşeti/fatura DSTK22852, gerçek module N16R8, PCB revizyonu.
- [ ] USB konnektör etiketleri; native19/20 ve harici UART köprüsünün gerçek güzergâhı.
- [ ] Köprü IC yazısı, Windows VID/PID/seri/COM; yalnız tek kabloyla çıkar/tak ilişkisi.
- [ ] BOOT/RESET etiketleri; ROM ESP32-S3 ve16MB; kararlı MAC. PSRAM ayrı boot loguyla.
- [ ] İki güç kaynağı/backfeed riski; ilk deney tek USB, aksesuarlar ayrık.
- [ ] UART boot logu, reset/brownout/PSRAM hatası yok; source1 varsayılan.
- [ ] Fiziksel HELLO ve tam G1 kanıtları kaydedildi; simülasyonla karıştırılmadı.
- [ ] Mikrofon breakout ön/arka, tüm gerçek pin etiketleri, alt akustik açıklık.
- [ ] Header lehimleri, lehim köprüsü/soğuk lehim, doğru yön; uygun lehim aracı mevcut.
- [ ] Güç kesikken GND ve her sinyal sürekliliği; VDD-GND kısa devre yok.
- [ ] Mikrofon ayrıyken ölçülmüş3.3V; ölçü aleti ve belirsizliği kaydedildi; tekrar enerji kesildi.
- [ ] Gerçek header konumları fotoğrafta işaretli; PROVISIONAL4/5/6 fiziksel plana onaylandı/değiştirildi.
- [ ] L/R=GND ve sol slot; WS/BCLK/SD yönleri; GPIO19/20 ve bellek/strap pinleri kullanılmıyor.
- [ ] Source0 için yeni manifest/profile incelendi ve ayrı flash onayı verildi.

Kart fotoğrafına gerçek kablo/header konumlarını çizin; genel DevKitC pin sırasından
breadboard deliği saymayın. Tarih, operatör, ölçüm sonuçları ve açık kalan maddeleri
`experiments/hardware/` içindeki fiziksel kanıt klasörüne yazın. Eksik güvenlik
maddesi varsa mikrofon bağlamayın; yalnız yazılım/USB hata kanıtı toplayın.
