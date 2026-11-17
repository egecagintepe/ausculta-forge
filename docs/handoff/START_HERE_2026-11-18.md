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

> `docs/handoff/AGENT_WEDNESDAY_2026-11-18.md dosyasını baştan sona oku ve kurulum ile Çarşamba lab akışını tools/hardware/wednesday_lab.py üzerinden sırayla yönet. Fiziksel fotoğraf ve multimetre ölçümlerini bizden tek seferde iste; insan onayı olmadan kesinlikle flash/reset/BOOT yapma.`

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

## ADIM 3 — Tek Komutluk Otonom Lab Çalıştırma (`wednesday_lab.py`)

Artık preflight, USB keşfi, `HELLO`, G1 (`480.000` örnek), H0/G2 kapı denetimi ve teslim ZIP oluşturma **tek komutla** yürür ve durumu `experiments/hardware/wednesday_20261118_state.json` dosyasına kaydeder (`<COM_CDC>` boş bırakılırsa yalnızca tek Espressif portu varsa otomatik seçer):

```powershell
# 1. Aşama: Preflight + USB keşfi + HELLO + G1 testi + H0/G2 kapısı + Kanıt ZIP'i
.\.venv\Scripts\python.exe tools/hardware/wednesday_lab.py --skip-g2-captures
```

**Başarı Kriteri:** `g1_regression` için **`PASSED`** (ve `480000` örnek, `0` kayıp), ardından `g2_physical_gate` adımında fotoğraf/multimetre onay kapısı ve ekranda hazır **teslim `.zip` dosya yolu**. *(Manuel tekil kontrol gerekirse `bringup.py hello` / `bringup.py g1` de kullanılabilir.)*

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
6. **G2 Sonrası Otonom G1 + 10 sn Sessiz + 10 sn Uyaranlı G2 Kaydı ve Karşılaştırma:**
   - Flash bitince `RESET` butonuna basın, yeni `<COM_CDC>` portunu bulun (gerekirse `--port <COM_CDC>` verin).
   - Aşağıdaki tek komutu çalıştırın; tamamlanmış G1 aşamasını algılayıp **10 s sessiz ortam (`g2_quiet_capture`)** ve **10 s test uyaranı (`g2_stimulus_capture`)** `source_mode=0` WAV kayıtlarını otomatik alır, dijital sıfır/sessizlik varsa sahte PASS vermez, `wednesday_g2_comparison.json` / `.md` üretir ve tek teslim `.zip` dosyasını çıkarır:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/wednesday_lab.py --assume-g2-flashed
   ```
   *(İsterseniz tarayıcıda canlı dalga/spektrogram ve `Wednesday Lab Mode` kartı için `.\scripts\dev.ps1` $\to$ `http://127.0.0.1:3000` açıp Device Center üzerinden **Build Return ZIP** de kullanabilirsiniz; CLI çalışırken tarayıcı bağlantısını kapalı tutun.)*

---

## ADIM 5 — Tüm Kanıtları Tek Teslim ZIP'i Olarak Ege'ye Gönderme (**GitHub'a Push Gerekmez**)

Testler bitince (veya herhangi bir aşamada hata kanıtı topladıktan sonra) çektiğiniz fotoğrafları mümkünse `experiments/hardware/photos/` klasörüne kopyalayın ve tek komutu çalıştırın:

```powershell
.\scripts\handoff\pack_wednesday_results.ps1 -Operator "Kaan_Ozan" -Notes "18 Kasim Carşamba G1/G2 lab oturumu"
```

Bu komut mevcut tüm `experiments/hardware/`, `experiments/sessions/` (`raw.wav` + `session.json`), `g2_physical_attestation.json`, güncellenmiş `docs/sdp/` tabloları ve uygulama loglarını **hiçbir sonucu değiştirmeden** tek bir SHA-256 doğrulamalı `.zip` paketinde toplar ve dosya yolunu ekrana yazar. Oluşan tek `.zip` dosyasını Ege'ye gönderin — Git/GitHub işlemi yapmanıza gerek yoktur.
