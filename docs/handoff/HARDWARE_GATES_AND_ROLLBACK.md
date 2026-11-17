# Fiziksel Donanım Kapıları, Emniyet Kuralları ve G1 Geri Dönüş (Rollback)

- **Hedef Tarih:** 18 Kasım 2026 Çarşamba
- **Sorumlular:** Kaan (Modül A — Fiziksel Montaj & Ölçüm), Ozan (Modül B — Gömülü & CLI Operasyonu)
- **Ana Referanslar:** [INMP441 First Acquisition](../engineering/hardware/INMP441_FIRST_ACQUISITION.md) | [Preliminary Pin Plan](../engineering/hardware/PRELIMINARY_PIN_PLAN.md) | [Physical Inspection Checklist](../engineering/hardware/PHYSICAL_INSPECTION_CHECKLIST.md) | [Board Dossier (DSTK22852 / YD-ESP32-23)](../engineering/hardware/BOARD_DOSSIER_DSTK22852.md)

---

## 1. H0 Fiziksel İnceleme Kapısı (Elektrik Vermeden Önce)

Mikrofonu bağlamadan ve cihaza flash atmadan önce **tüm maddeler fiziksel olarak doğrulanmalıdır**:

1. **Çift Taraflı Fotoğraf Kanıtı:**
   - ESP32-S3 kartının (`YD-ESP32-23`, `N16R8`) **ön ve arka yüzü**, silkscreen pin yazıları okunacak şekilde fotoğraflanmalıdır.
   - INMP441 breakout kartının **ön ve arka yüzü** (`VDD/VCC`, `GND`, `SCK`, `WS`, `SD`, `L/R` etiketleri ve alt akustik deliği) fotoğraflanmalıdır.
   - İki farklı kart veya jenerik DevKitC şeması üzerinden pin sayımı **yapmayın**; elinizdeki PCB üzerindeki gerçek yazıları okuyun.
2. **Tek USB Kablosu ve Port Ayrımı Kuralı:**
   - Kart üzerinde iki USB-C konnektörü varsa (`USB` = Native OTG GPIO 19/20, `UART/COM` = harici köprü/UART0), ilk bağlantıyı **yalnızca tek veri kablosuyla** yapın.
   - İki kabloyu aynı anda takmayın (backfeed / çift besleme riski).
   - Port tespiti için **kabloyu çıkarıp takarak** Device Manager / `list_ports` üzerindeki değişikliği gözlemleyin. `COM10` geçici bir Windows port numarasıdır; **asla sabit `COM10` varsaymayın**.
   - **Tek Sahip Kuralı (Single Port Owner):** Aynı anda yalnızca **bir** program COM portunu açabilir. Backend (`uvicorn` `:8000`) veya başka bir seri monitör (PuTTY, IDF monitor, Arduino IDE) portu tutarken CLI komutu çalıştırmayın.
3. **Lehimleme ve Alt Akustik Delik Kontrolü:**
   - Gevşek / lehimsiz header pinlerini breadboard veya ESP32 deliklerine sıkıştırarak test yapmayın (sahte sıfır, kesinti veya kısa devre riski).
   - INMP441 alt yüzündeki küçük **akustik giriş deliğini (port)** asla lehim artığı, sıcak silikon veya bant ile kapatmayın.

---

## 2. Elektriksel Güvenlik ve Pin Kuralları

### 2.1 Besleme ve Multimetre Kapısı (ŞART)

| Kontrol | Zorunlu Koşul | Yasak / Tehlike |
| :--- | :--- | :--- |
| **INMP441 Besleme (VDD)** | Yalnızca ESP32 regüle **`3V3`** çıkışı (`3.15 V .. 3.45 V` ölçülmüş) | **ASLA `5V` / `VBUS` / `VIN` BAĞLAMAYIN!** INMP441 maksimum sınırı `3.63 V`'tur; 5V sensörü kalıcı olarak yakar. |
| **Güçsüz Kısa Devre Testi** | USB çekiliyken multimetre direnç/bızzır ile `VDD–GND` kısa devre yok; her pin kendi hedefiyle sürekli | Kısa devre veya soğuk lehim köprüsü varken USB takmayın. |
| **İki Aşamalı Güç Testi** | Önce mikrofon **AYRIYKEN** ESP32 USB'den beslenir, `3V3` pini ölçülür; **ardından USB tekrar çıkarılır**, güçsüzken kablolama tamamlanır | Enerji altındayken jumper söküp takmayın. |
| **Slot Seçimi (`L/R`)** | **`L/R -> GND`** (Sol kanal — G2 candidate firmware varsayılanı) | `L/R` ucunu boş (floating) bırakmayın. `3.3V`'a bağlarsanız sol slotta yalnız sıfır gelir (`CONFIG_AF_I2S_RIGHT_SLOT=y` ile yeniden derleme gerekir). |

### 2.2 Geçici (Provisional) G2 Pin Planı ve Yasaklı Pinler

> [!IMPORTANT]
> Aşağıdaki `GPIO 4 / 5 / 6` ataması yazılım ve G2 candidate derlemesi için hazırlanmış **geçici plandır**. Kaan elindeki gerçek PCB üzerinde çakışma/eksik pin görmedikçe geçerlidir; farklı pin seçilirse firmware `idf.py menuconfig` + `bringup.py build` ile yeniden derlenmelidir.

| INMP441 Pini | ESP32-S3 GPIO | Yön | Durum |
| :--- | :--- | :--- | :--- |
| `VDD` / `VCC` | `3V3` | Güç (3.3 V) | Zorunlu — Ölçüm onayı şart |
| `GND` | `GND` | Ortak Toprak | Zorunlu — Süreklilik onayı şart |
| `SCK` / `BCLK` | **`GPIO 4`** | ESP32 $\to$ Mic (3.072 MHz) | Provisional (`CONFIG_AF_I2S_BCLK=4`) |
| `WS` / `LRCLK` | **`GPIO 5`** | ESP32 $\to$ Mic (48 kHz) | Provisional (`CONFIG_AF_I2S_WS=5`) |
| `SD` / `DOUT` | **`GPIO 6`** | Mic $\to$ ESP32 | Provisional (`CONFIG_AF_I2S_DIN=6`) |
| `L/R` | **`GND`** | Slot Seçimi (Sol) | Zorunlu (`CONFIG_AF_I2S_RIGHT_SLOT` kapalı) |

**Kesinlikle Yasak / Rezerve GPIO'lar (`i2s_source.c` `safe_pin()` tarafından da bloklanır):**
- **`GPIO 19 / 20`:** Native USB D- / D+ (`usb_transport.c`) — mikrofon bağlanırsa USB bağlantısı kopar!
- **`GPIO 26..37`:** N16R8 dahili Flash ve Octal PSRAM (35..37 dahil) — kullanılırsa kart çöker/kilitlenir.
- **`GPIO 0 / 3 / 45 / 46`:** Boot & Strapping pinleri.
- **`GPIO 43 / 44`:** UART0 donanım konsolu / kurtarma log hattı.
- **`GPIO 38 / 47 / 48`:** Kart üstü RGB LED / revizyona bağlı hatlar.

---

## 3. PAM8403 Amplifikatör ve Akustik Fantom Güvenliği (Ayrı Deney)

- İlk G1 ve G2 mikrofon doğrulama testleri için **PAM8403 veya 12-ohm exciter BAĞLAMAYIN**. Önce mikrofon tek başına doğrulanır.
- Fantom testine geçildiğinde:
  1. **PAM8403 BTL Çıkış Uyarısı:** PAM8403 hoparlör çıkışı Bridge-Tied Load (BTL) yapıdadır; **negatif hoparlör çıkışını (`OUT-`) ASLA ortak toprağa (`GND`) veya topraklı osiloskop probu şase klipsine bağlamayın** (amplifikatörü kısa devre eder).
  2. Hiçbir amplifikatör / hoparlör / PC kulaklık çıkışını INMP441 dijital I²S pinlerine (`GPIO 4/5/6`) bağlamayın.
  3. **İnsan / Hasta Kaydı Yasağı:** Bu sistem sertifikalı tıbbi cihaz değildir. Proje kapsamında **hiçbir insandan veya hastadan ses kaydı alınmaz**; fiziksel testler yalnızca kontrollü ses uyaranı ve akustik fantom üzerinden yapılır.

---

## 4. `BOOT` / `RESET` Modu ve G2 Yetkilendirme Kapıları

- Firmware flash işlemi veya ROM kimlik sorgusu yalnız **Ege veya Çarşamba lab operatörünün açık onayı** ile çalıştırılır.
- **Manuel ROM Bootloader Modu** (yalnızca flash komutu istendiğinde):
  1. Kart üzerindeki etiketli `BOOT` butonunu basılı tutun.
  2. `BOOT` basılıyken `RST` (`RESET`) butonuna kısa basın ve bırakın.
  3. `BOOT` butonunu bırakın. Windows'ta cihaz USB JTAG/ROM COM portuna geçer (Native CDC portu geçici olarak kaybolabilir).
- **`g2_compile_check` YASAĞI:** [`firmware/build/g2_compile_check/`](../../firmware/build/g2_compile_check/) yalnızca derleme kontrolü içindir ve **`bringup.py` tarafından flash edilmesi kilitlenmiştir**.
- **G2 Aday Yetkilendirme (`authorize-g2`):** Staged G2 aday paketi ([`firmware/releases/g2_candidate_20261117/`](../../firmware/releases/g2_candidate_20261117/firmware_build_manifest.json)) başlangıçta `PREPARED_NOT_AUTHORIZED_FOR_FLASH` durumundadır. Gerçek 3.3V ölçümü ve pin onayı girilmeden flash engellidir.

---

## 5. Durdurma Kuralları (STOP-WORK)

Aşağıdaki durumlardan biri oluşursa **deneyi derhal durdurun**, USB kablosunu çıkarın ve kanıtı (log/fotoğraf) koruyun:
1. Kart, regülatör veya INMP441'de olağandışı ısınma / koku görülmesi.
2. `3V3` hattının `3.15 V .. 3.45 V` dışında ölçülmesi veya `VDD–GND` arasında kısa devre saptanması.
3. G1 regresyonunda `CRC error`, `sequence gap` veya `sample_value_error > 0` alınması.
4. G2 canlı kayıtta (`source_mode=0`) yalnızca sıfır (`constant_zero: true`) gelmesi (kablonun yerinden çıkarılması, L/R yanlış slotu veya saat eksikliği şüphesi — güç kesilip tekrar ölçüm yapılmalıdır).

---

## 6. Zorunlu G1 Geri Dönüş (Rollback) Prosedürü

G2 donanım veya firmware denemesi başarısız olursa, takılı kalırsa veya stabil G1 referansına dönmek gerekirse **değiştirilemez (immutable) G1 yedeğine** dönün:

1. ESP32-S3 USB kablosunu çıkarın. Güçsüzken INMP441 jumper kablolarını ayırın.
2. USB kablosunu tekrar takın ve kartı ROM Bootloader moduna alın (`BOOT` basılı tut $\to$ `RESET` bas-bırak $\to$ `BOOT` bırak).
3. Aktif ROM COM portunu kontrol edin:
   ```powershell
   .\.venv\Scripts\python.exe -m serial.tools.list_ports
   ```
4. Değiştirilemez G1 yedeğiyle flash başlatın (`<COM_ROM>` yerine gördüğünüz portu yazın):
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port <COM_ROM> --manifest firmware/g1_rollback_backup/firmware_build_manifest.json
   ```
5. Ekranda hash ve MAC doğrulaması göründüğünde onay için tam olarak **`FLASH <COM_ROM>`** yazın.
6. Flash sonrası `RESET` butonuna basın, yeni oluşan CDC COM portunu okuyun ve G1 doğrulamasını çalıştırın:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port <COM_CDC>
   .\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port <COM_CDC> --manifest firmware/g1_rollback_backup/firmware_build_manifest.json
   ```
   *(Detaylı yedek envanteri: [`firmware/g1_rollback_backup/README.md`](../../firmware/g1_rollback_backup/README.md))*
