# Çarşamba 18 Kasım — Başlangıç Rehberi (Kaan & Ozan)

- **Amaç:** Ege olmadan 18 Kasım Çarşamba günü mevcut çalışan G1 ESP32-S3 sistemini kendi bilgisayarınızda doğrulamak, ardından fiziksel güvenlik kapılarını geçerek ilk INMP441 (G2) kaydını güvenli şekilde almaktır.
- **Bu rehberin detaylı emniyet kuralları:** [HARDWARE_GATES_AND_ROLLBACK.md](HARDWARE_GATES_AND_ROLLBACK.md)

---

## İki Kişilik Görev Dağılımı

| Rol | Sorumlu | Görevler |
| :--- | :--- | :--- |
| **Modül A — Donanım & Ölçüm Lideri** | **Kaan** | Kart/mikrofon ön-arka fotoğrafları, lehimleme kalitesi kontrolü, güçsüz süreklilik/kısa devre ölçümü, 3.3V multimetre ölçümü, pin doğrulaması, fiziksel uyaran. |
| **Modül B — Bilgisayar & Ajan Operatörü** | **Ozan** | GitHub'dan projeyi **Download ZIP** ile indirip klasöre açma (**Git gerekmez**), Antigravity ajanına [AGENT_WEDNESDAY_2026-11-18.md](AGENT_WEDNESDAY_2026-11-18.md) görevini verme, PowerShell & Device Center'ı yönetme ve bitişte tek teslim `.zip` dosyasını Ege'ye gönderme. |

> [!CAUTION]
> **ALTIN KURAL:** Aynı anda yalnızca **TEK** program (ya CLI aracı ya Backend `:8000`) COM portuna bağlanabilir. CLI çalıştırırken tarayıcı Device Center'dan **Disconnect** yapın veya Backend'i durdurun. Önceki `COM10` numarası kalıcı değildir; her bağlantıda portu yeniden tespit edin!

---

## ADIM 0 — Kendi Antigravity Ajanınızı Başlatın

Bilgisayarınızda Antigravity'yi açın ve ajana tam olarak şu komutu verin:

> `docs/handoff/AGENT_WEDNESDAY_2026-11-18.md dosyasını baştan sona oku ve oradaki H0 -> G1 -> G2 adımlarını sırayla uygula. Bizden istediğin tüm fotoğraf ve multimetre ölçümlerini tek seferde iste; fiziksel onaysız flash/reset/BOOT yapma.`

---

## ADIM 1 — GitHub'dan İndirme ve Tek Seferlik Kurulum (**Git Gerekmez**)

### Seçenek A — Önerilen: Git Kullanmadan Doğrudan ZIP İndirme
1. Tarayıcıdan `https://github.com/egecagintepe/ausculta-forge` sayfasına gidin.
2. Yeşil **`Code`** butonuna tıklayın $\to$ **`Download ZIP`** seçin.
3. İndirilen ZIP dosyasını sağ tıklayıp **Ayıkla / Extract** diyerek boşluksuz ve Türkçe karaktersiz **`C:\pcg_starter`** klasörüne çıkartın *(içinde `docs\handoff\` doğrudan görünsün; `C:\pcg_starter\ausculta-forge-main\` şeklinde iç içe kaldıysa içindeki dosyaları `C:\pcg_starter` altına taşıyın)*.
4. Antigravity uygulamasında bu klasörü (`C:\pcg_starter`) açın.

*(Seçenek B — Git yüklüyse: `git clone https://github.com/egecagintepe/ausculta-forge.git C:\pcg_starter`)*

Ardından PowerShell'de `C:\pcg_starter` içine girip otomatik kurulum ve ön kontrolü çalıştırın:

```powershell
cd C:\pcg_starter

# 1. Ortamı otomatik kurun (.venv, Python paketleri, esptool, frontend):
.\scripts\handoff\windows_setup.ps1

# 2. Salt-okunur ön kontrol (cihaza dokunmaz, binary hash'lerini doğrular):
.\scripts\handoff\windows_preflight.ps1
```

**Beklenen Örnek Çıktı (`Download ZIP` modunda dahi çalışır):**
```text
Repo Root    : C:\pcg_starter
Mode / HEAD  : GITHUB_DOWNLOAD_ZIP | <guncel_sha> (branch: NONE (ZIP), dirty: False)
Python       : 3.11.x (venv=True, modules_ok=True)
Frontend     : Node=v22.x (ok=True), node_modules=True
Manifests    :
  - G1 Rollback Backup : hashes_ok=True | status=COMPILED_BUT_NOT_FLASHED
  - G1 Staged Release  : present=True | hashes_ok=True | status=COMPILED_BUT_NOT_FLASHED
  - G2 Staged Candidate: present=True | hashes_ok=True | status=PREPARED_NOT_AUTHORIZED_FOR_FLASH
ESP32 Ports  : NONE_DETECTED (veya takılıysa COMx)
```

---

## ADIM 2 — Fiziksel Fotoğraf ve Multimetre Kapısı (H0 — MİKROFON TAKILMADAN)

Mikrofonu kablolamadan ve flash atmadan önce Kaan şu ölçümleri yapar:
1. ESP32-S3 ön/arka yüz ve INMP441 ön/arka yüz fotoğraflarını çekin (pin yazıları net okunmalı).
2. Güç kablosu **çıkarılmışken** INMP441 header lehimlerini kontrol edin (`VDD–GND` arasında kısa devre **OLMAMALI**, alt mikrofon deliği açık olmalı).
3. Tek USB veri kablosunu ESP32'ye takın (mikrofon **ayrıyken**). Multimetre ile ESP32 `3V3` – `GND` arasını ölçün (beklenen: **3.25V – 3.35V**, **ASLA 5V kullanmayın**).
4. ESP32 üzerindeki aktif CDC portunu tespit edin:
   ```powershell
   .\.venv\Scripts\python.exe -m serial.tools.list_ports
   ```
   *(Kabloyu çıkarıp tekrar takarak yeni gelen Espressif `VID:303A PID:4001` port numarasını not edin — örneğin `COM7` veya `COM10`.)*

---

## ADIM 3 — Mevcut G1 Regresyon Kanıtı (Firmware Değiştirmeden)

Karttaki mevcut G1 firmware'inin bilgisayarınızda hatasız çalıştığını doğrulayın (`<COM_CDC>` yerine kendi portunuzu yazın):

```powershell
# 1. El sıkışma (HELLO):
.\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port <COM_CDC>

# 2. Tam G1 480.000 örnek testi (Staged G1 manifest ile):
.\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port <COM_CDC> --manifest firmware/releases/g1_release_20261117/firmware_build_manifest.json
```
*(Port sorulursa güvenlik onayı için `<COM_CDC>` yazıp Enter'a basın.)*

**Başarı Kriteri:** Ekranda **`PHYSICAL_G1_PASSED`** çıktısı ve `0 dropped_samples`, `480000` örnek.

---

## ADIM 4 — Yalnızca Onaylı G2 Aşaması (INMP441 Bağlantısı & Canlı Kayıt)

> [!WARNING]
> Bu adıma **YALNIZCA** Adım 2'deki 3.3V ölçümü tamamlandıysa, Adım 3 **`PHYSICAL_G1_PASSED`** verdiyse ve lehimli bağlantılar onaylandıysa geçin!

1. **Enerjiyi Kesin:** USB kablosunu çıkarın.
2. **Kablolama (Provisional Plan):**
   - `VDD` $\to$ `3V3` *(Ölçülmüş 3.3V)*
   - `GND` $\to$ `GND`
   - `SCK / BCLK` $\to$ `GPIO 4`
   - `WS / LRCLK` $\to$ `GPIO 5`
   - `SD / DOUT` $\to$ `GPIO 6`
   - `L/R` $\to$ `GND` *(Sol slot seçimi)*
3. **Güçsüz Kısa Devre Kontrolü:** USB takmadan multimetre ile `VDD–GND` kısa devre olmadığını doğrulayın.
4. **G2 Aday Paketini Yetkilendirin** *(pinler 4/5/6 dışında bir GPIO'ya takıldıysa `authorize-g2` izin vermez; bu durumda ESP-IDF ile `menuconfig` $\to$ `bringup.py build` gerekir)*:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py authorize-g2 --bclk 4 --ws 5 --din 6 --slot left --vdd-volts <OLCULEN_VOLT> --operator "Kaan & Ozan" --multimeter "<OLCU_ALETI>"
   ```
5. **Kartı ROM Bootloader Moduna Alıp Flash Atın:**
   - `BOOT` basılı tut $\to$ `RESET` bas-bırak $\to$ `BOOT` bırak $\to$ yeni `<COM_ROM>` portunu `list_ports` ile bulun.
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port <COM_ROM> --manifest firmware/releases/g2_candidate_20261117/firmware_build_manifest.json
   ```
6. **G2 Sonrası Kontrol ve İlk Kayıt:**
   - Flash bitince `RESET` butonuna basın, yeni `<COM_CDC>` portunu bulun.
   - Önce G1 regresyonunun hâlâ geçtiğini doğrulayın: `bringup.py g1 --port <COM_CDC> --manifest firmware/releases/g2_candidate_20261117/firmware_build_manifest.json`.
   - Ardından uygulamayı açın: `.\scripts\dev.ps1` $\to$ Tarayıcıda `http://127.0.0.1:3000`.
   - **Device Center:** `<COM_CDC>` seç $\to$ **Connect & HELLO** $\to$ **Live microphone (Mode 0)** seç $\to$ **Start Acquisition** $\to$ Live Workspace'de **Record** ile 10 saniye **sessiz oda** kaydı, ardından yeni bir 10 saniye **kontrollü test sesi (alkış/ton)** kaydı alın.
   - İki WAV oturumunu da doğrulayın:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py qualify --session experiments/sessions/<SESSION_ID> --output experiments/hardware/g2-quiet.json
   ```
   *(Sorun çıkarsa panik yapmayın: [HARDWARE_GATES_AND_ROLLBACK.md](HARDWARE_GATES_AND_ROLLBACK.md#6-zorunlu-g1-geri-dönüş-rollback-prosedürü) ile 2 dakikada G1'e dönülür.)*

---

## ADIM 5 — Tüm Kanıtları Tek Teslim ZIP'i Olarak Ege'ye Gönderme (**GitHub'a Push Gerekmez**)

Testler bitince (veya herhangi bir aşamada hata kanıtı topladıktan sonra) çektiğiniz fotoğrafları mümkünse `experiments/hardware/photos/` klasörüne kopyalayın ve tek komutu çalıştırın:

```powershell
.\scripts\handoff\pack_wednesday_results.ps1 -Operator "Kaan_Ozan" -Notes "18 Kasim Carşamba G1/G2 lab oturumu"
```

Bu komut mevcut tüm `experiments/hardware/`, `experiments/sessions/` (`raw.wav` + `session.json`), `g2_physical_attestation.json`, güncellenmiş `docs/sdp/` tabloları ve uygulama loglarını **hiçbir sonucu değiştirmeden** tek bir SHA-256 doğrulamalı `.zip` paketinde toplar ve dosya yolunu ekrana yazar. Oluşan tek `.zip` dosyasını Ege'ye gönderin — Git/GitHub işlemi yapmanıza gerek yoktur.
