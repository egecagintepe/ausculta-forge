# Windows laptop kurulumu

Bu bilgisayarda kurulu araçlar laptopunuza taşınmaz. Komutları klonladığınız repo
kökünde PowerShell'de çalıştırın. Kurulum komutları kullanıcı tarafından çalıştırılır;
checker sürücü, PATH, kayıt defteri veya sistem ayarı değiştirmez.

## Python ve frontend

Git ve Python 3.11+ gerekir; bu RC'nin temiz ortam denemesi Python 3.11 kullanır.
PyTorch donanım/DSP için zorunlu değildir. İlk kez:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r software/requirements.txt -e ./software
.\.venv\Scripts\python.exe tools/hardware/preflight.py --json
```

Gereken çekirdek paketler: numpy/scipy, PyWavelets, pyserial, FastAPI/uvicorn,
websockets ve multipart. Test araçları requirements içinde bulunur. Checker eksikleri
`MISSING`, mevcut kontrolleri `READY`, fiziksel/sistem incelemesini
`MANUAL_ACTION_REQUIRED` olarak yazar. `python -S tools/hardware/preflight.py --json`
bağımlılık yokken bile açıklayıcı rapor verir. `.venv` varsa:

```powershell
.\tools\hardware\windows_preflight.ps1 -Json
```

Node sürümünü `node --version` ile kontrol edin. Bu frontend'in kurulu
`@vitejs/plugin-react` engine aralığı **^20.19.0 veya >=22.12.0**; Node 22.12+
uyumlu LTS kurulumu kullanın. README'deki eski Node 18 tabanı geçerli değildir.

```powershell
Push-Location software/frontend
npm ci
npm test
npm run lint
npm run build
Pop-Location
```

PowerShell npm.ps1 çalıştırma politikası engelinde `npm.cmd` kullanın; sistem
execution policy'sini değiştirmek gerekmez. Host helper'ları tırnaklı mutlak
yolları destekler; ESP-IDF/Python SDK kurulumuna ilişkin boşluk kısıtları ayrıdır.

## ESP-IDF

Sabit sürüm **5.5.1**, hedef **esp32s3**, esp_tinyusb 2.2.0 / tinyusb 0.19.0~3.
[Sürüme ait resmi Windows kurulumu](https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32s3/get-started/windows-setup.html)
ile kurun; kurucu açılışında ESP-IDF PowerShell ortamını seçin. EIM kullanıyorsanız
kurulum listesinin tam 5.5.1'i sunduğunu doğrulayın; daha yeni IDF seçmeyin.
SDK/Python kurulum yolu kısa, ASCII ve boşluksuz olsun; bu upstream kısıtıdır.
Mevcut SDK için kendi kurulumunuzdaki `export.ps1` dosyasını dot-source edin.
`IDF_TOOLS_PATH` özel seçildiyse aynı kullanıcıya ait araç dizinine işaret etmelidir.

```powershell
idf.py --version
.\.venv\Scripts\python.exe tools/hardware/bringup.py doctor
.\.venv\Scripts\python.exe tools/hardware/bringup.py build
```

Yerel `firmware/build/esp-idf-v5.5.1` geliştirme önbelleği Git'te bulunmaz; laptopta
varmış gibi davranmayın. Binary'ler klonla gelmez: yerelde build komutu çalıştırın.
Alternatif bir release paketi taşınıyorsa dosya hash'leri ve manifestteki yerel
build_directory doğrulanmalıdır; başka bilgisayarın mutlak yolunu kullanmayın.

## Uygulamayı aç

En erişilebilir yol: repo + iki PowerShell terminali. İlk terminal repo kökünde:

```powershell
.\.venv\Scripts\python.exe -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000
```

İkinci terminal repo kökünden:

```powershell
Set-Location software/frontend
npm run dev
```

Tarayıcıda `http://127.0.0.1:3000` açın. Device Center kullanılır; backend 8000'e
bağlanır. `--reload` kullanmayın: USB sahibi tek süreç olmalıdır. Kapatma:
STOP → Disconnect → iki terminalde Ctrl+C. Kayıtlar repo `experiments/sessions/`,
kanıt ZIP'i tarayıcı indirmeleri; Flight Recorder `%APPDATA%/AuscultaForge/logs/`.
Port 8000 doluysa kendi önceki backend'inizi kapatın; bilinmeyen süreci öldürmeyin.

Tauri geliştirme penceresi için Rust/MSVC Windows build tools ve WebView2 gerekir.
`npm run tauri dev` kendi Python backend'ini başlatır; ayrıca 8000 backend açmayın.
`npm run build` tek başına kurulabilir Windows uygulaması değildir.

Paketleme: `.venv/Scripts/python.exe software/build_desktop_backend.py` →
`software/dist_backend/auscultaforge-backend/` → frontend içinde
`npm run tauri build`. Kaynak helper CLI/ESP-IDF uygulama paketine gömülmez;
flash/preflight repo üzerinden yürür. Release binary global Python'a geri düşmez.
Kurulum ve interaktif paketli pencere testi durumunu
[güncel rapordan](../release/MORNING_RELEASE_REPORT.md) okuyun; backend smoke
testini tüm kurulum deneyimiyle eşitlemeyin.

Model kurmak isteğe bağlıdır; USB açılışında otomatik eğitim/tahmin yapılmaz.
Frozen MurmurMIL'in mevcut araştırma manifest/hash/aynı-kişi ve kalibrasyonsuz-skor
uyarıları geçerlidir. Yeni mikrofon alanında dış doğrulama yoktur.
