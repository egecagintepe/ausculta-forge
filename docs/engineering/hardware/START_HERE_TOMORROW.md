# Yarın buradan başla — Ege ve Kaan

**Durum: yazılım doğrulaması ayrı, fiziksel kabul bekliyor. Mikrofonu ilk başta bağlamayın.**
Laptop, ESP32-S3, veri taşıyan USB kablosu ve kart fotoğrafı için telefon getirin.
G2 için ayrıca INMP441, sağlam/lehimli başlıklar, jumper ve multimetre gerekir.
Teslim alınan parçaları birlikte sayın; sipariş verilmesi teslim alındığını göstermez.

1. VS Code'da klonladığınız **ausculta-forge kök klasörünü** açın. İçinde `firmware`,
   `software`, `tools` görünmeli. Terminal → New Terminal → **PowerShell** seçin.
   İlk komut (kart takılı olmadan da çalışır):
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py doctor
   ```
   `.venv` yoksa önce [laptop kurulumu](WINDOWS_LAPTOP_SETUP.md). `USB_CDC_HOST` ve
   `DESKTOP_BACKEND: READY` beklenir. Derleme için `ESP_IDF: READY` de gerekir;
   değilse **ESP-IDF 5.5.1 PowerShell** açın. `BOARD_ATTACHED: NOT_DETECTED` normaldir.
2. Kartın iki yüzünü, N16R8 yazısını, düğme ve USB etiketlerini fotoğraflayın.
   [Fiziksel kontrol listesini](PHYSICAL_INSPECTION_CHECKLIST.md) tamamlayın.
   **Hangi USB-C'nin UART, hangisinin GPIO19/20 native USB olduğu henüz kesin değil.**
   Tek kablo kullanın; pin/konnektör tahmini yapmayın. Mikrofon ve PAM8403 takılı olmasın.
3. Windows Aygıt Yöneticisi → Bağlantı Noktaları (COM ve LPT), gerekirse Diğer
   Aygıtlar'ı açın. Takmadan/çıkardıktan sonra değişen COM ve donanım kimliklerini
   kaydedin. Bu, firmware doğrulaması değildir. Otomatik port seçimi yoktur:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py watch --seconds 30
   ```
4. IDF 5.5.1 ortamında, yine repo kökünde, derleyin:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py build
   ```
   `COMPILED_BUT_NOT_FLASHED` ve `firmware/build/release/firmware_build_manifest.json`
   oluşmalı. ESP32-S3 / 16 MB ROM kimliğini seçtiğiniz portta doğrulayın.
   Aşağıda **COM7 yalnız örnektir; gerçek portunuzla değiştirin**:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py identify --port COM7
   .\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port COM7
   ```
   `COM7` yazmanız ROM sorgusunu, **`FLASH COM7` yazmanız firmware yazmayı** onaylar.
   Kart/power kontrolü tamamlanmadan onay vermeyin. Başka seri monitör açık olmasın.
5. Flash sonrasında COM değişebilir. `watch` ile yeniden bakın. UART debug
   konnektörü fiziksel olarak doğrulanmışsa yalnız o portta boot kaydı alın:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py boot-log --port COM7 --output experiments/hardware/day01-boot.txt
   ```
   `UART COM7` onayından sonra RESET'e basın. `Canonical B 1.1.0 ready; I2S supported=0`
   ve heap/stack health satırları beklenir; PSRAM ve reset hatalarını da inceleyin.
   **Bu monitör binary CDC için değildir.** UART erişilemiyorsa boot gate'i eksik bırakın.
6. Veri konnektörünü seçin; monitör kapalıyken gerçek **yeni CDC COM** ile çalıştırın:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port COM8
   .\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port COM8
   ```
   HELLO: `FIRMWARE HANDSHAKE VERIFIED`. G1: yalnız **`PHYSICAL_G1_PASSED`**, 480000
   örnek, 1875 frame, sıfır hata ve final STOP_ACK gerçek geçiştir. Bir PASS sözcüğü
   veya `SOFTWARE_SIMULATION_PASS` fiziksel geçiş değildir. CLI portu sonunda bırakır.
7. Masaüstü için [geliştirici açılışını](WINDOWS_LAPTOP_SETUP.md#uygulamayı-aç)
   kullanın. Device Center → Scan Ports → gerçek portu seç → Connect/HELLO → source 1
   → Start. Hedefte otomatik STOP olur; Export G1 Evidence ZIP'i kaydedin. CLI ve
   masaüstünü aynı portta eşzamanlı çalıştırmayın. Live Workspace kaydı ayrıca
   başlatılır; STOP aktif kaydı sonlandırır. Kapatmadan önce STOP ve Disconnect kullanın.

**Dosyalar:** CLI kanıtları `experiments/hardware/<UTC_benzersiz>/`; flash/kimlik
`firmware/build/release/first-flash.txt`, `board_identity.json`; geliştirme WAV'ları
`experiments/sessions/<session_id>/raw.wav` ve `session.json`. Flight Recorder:
`%APPDATA%/AuscultaForge/logs/`. Paketli uygulama kayıtları `%APPDATA%/AuscultaForge/sessions/`.

**Takılırsanız:** çalıştırdığınız komut, tam terminal çıktısı, Aygıt Yöneticisi
ekran görüntüsü/donanım kimliği, iki yüz kart fotoğrafı ve oluşan kanıt ZIP'ini
gönderin. `first-flash.txt`, boot kaydı ve başarısız G1 raporunu silmeyin. Paylaşmadan
önce kullanıcı adı/dosya yolları/USB seri numarası ve kayıtların mahremiyetini kontrol edin.

**Windows görmüyorsa:** veri kablosu/tek konnektör kontrolü → donanım kimliği →
doğrulanmış üretici sürücüsünü elle kurma kararı. **Flash başarısızsa:** hatayı saklayın,
etiketi doğrulanmış BOOT'u tut → RESET bas/bırak → BOOT bırak → tekrar tara/identify.
Erase/eFuse kullanmayın. [Hata rehberi](DAY_ONE_LAB_RUNBOOK.md#advanced-commands-and-failure-recovery).

**Mikrofon:** ancak kararlı fiziksel G1, ölçülmüş 3.3 V, ortak GND, doğru lehim/pin
ve [G2 planı](INMP441_FIRST_ACQUISITION.md) sonrası; source 0 ayrıca onaylanmış
I2S profili derle/flash gerektirir. 5 V yasak. İlk gün G1 başarısı yeterli bir hedeftir.
