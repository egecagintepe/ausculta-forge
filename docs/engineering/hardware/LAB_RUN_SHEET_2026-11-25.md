# AuscultaForge — 25 Kasım 2026 Çarşamba Laboratuvar Uygulama Föyü (Lab Run Sheet)

**Tarih:** 25 Kasım 2026 Çarşamba Sabahı  
**Ders:** EEE 495 / SDP4 — Akıllı Dijital Stetoskop  
**Öncelik:** P0 — Fiziksel Hafta 9 Fantom S1/S2 Kabul Kapısı (Haftalık Akademik İlerleme)  
**Dil:** Türkçe (Laboratuvarda operatörlerin doğrudan ve hatasız uygulaması için)

---

## 1. Ekip Rol Dağılımı ve Görevler

| Operatör | Modül | Laboratuvar Sorumluluğu |
|---|---|---|
| **Ünal Kaan Öztürk** | **Modül A (Akustik / Donanım)** | Fantom ve uyarım mekanik düzeneği. Borcam RTV-2 silikon örneğinin yatay konumlandırılması, 30 mm exciter'ın alt tabana merkezlenmesi, INMP441 / stetoskop gövdesinin üst yüzeye 100g/200g kontrollü yükle yerleştirilmesi, hava sızıntısı ve masa titreşim izolasyonunun sağlanması. |
| **Özgür Ozan Yıldız** | **Modül B (Gömülü Sistem / Ölçüm)** | Elektriksel güvenlik, kablolama ve voltaj kontrolü. Multimetre ile 3.3V besleme rayı doğrulaması (3.15–3.45 V), PAM8403 potansiyometre ses seviyesi takibi, COM port (USB CDC vs ROM Boot) ayrımı, clipping ve near-clipping gözlemi. |
| **Ege Çağın Tepe** | **Modül C (Yazılım / Analiz)** | Host bilgisayar çalıştırma ve test otomasyonu. `run_phantom_pcg_experiment.py` komutlarının icrası, sessiz referans (quiet) oturumu alma, S1/S2 korelasyon çıktılarının analizi, hash doğrulaması ve kanıt paketleme. |

---

## 2. Laboratuvara Getirilecek Malzeme Kontrol Listesi (Bring-List)

- [ ] **ESP32-S3 Geliştirme Kartı:** Üzerinde test edilmiş G2 firmware adayı (`g2_candidate_20261117`) yüklü kart.
- [ ] **INMP441 MEMS Mikrofon Modülü:** 6 pinli jumper kabloları lehimlenmiş (VDD, GND, SD, WS, SCK, L/R).
- [ ] **PAM8403 Ses Amplifikatörü + 30 mm Exciter (12 $\Omega$):** Lehimlenmiş, 3.5 mm TRS giriş kablosu hazır.
- [ ] **Fantom Örneği:** 23 Kasım'da dökülen 12 cm çapında, ~10 mm et kalınlığındaki Borcam RTV-2 silikon örneği.
- [ ] **Yedek Uyumluluk Pedi (Fallback Pad):** Silikon henüz tam kürlenmemişse (yapışkansa) araya konulacak kuru temiz silikon ped / ince film bariyer.
- [ ] **Stetoskop Başlığı / Bağlayıcı Halka:** INMP441 akustik giriş deliğini merkezleyen mekanik kılıf.
- [ ] **Kalibre / Doğrulanmış Multimetre:** 3.3V rayı ve besleme gerilimini ölçmek için.
- [ ] **Test Ağırlıkları:** 100 g ve 200 g standart yükler (aşırı basmayı engellemek için).
- [ ] **USB Kabloları:** 2 adet kaliteli USB Type-C data kablosu (sadece şarj değil, veri hatları tam).
- [ ] **Laboratuvar Laptopu:** Python 3.12, Git repo, CirCor referans sesleri (`data/raw/week6_real_pcg_20261026/circor/40058_AV.wav`).

---

## 3. Elektriksel Güvenlik ve Kesin Durdurma (STOP) Kriterleri

> [!CAUTION]
> **KESİN KURAL:** Sistem yalnızca bilgisayar USB portu veya taşınabilir 5V batarya ile beslenecektir. Şebekeye (220V priz) doğrudan veya topraksız izolesiz adaptörle ASLA bağlantı yapılmayacaktır. İnsan (öğrenci dahil) denek kaydı kesinlikle YASAKTIR; tüm testler fantom üzerinde yapılacaktır.

### DERHAL DURDURMA KRİTERLERİ (STOP GATES):
1. **Voltaj Aşımı:** Multimetre ölçümünde ESP32-S3 / INMP441 3.3V pini **$> 3.46\text{ V}$** veya **$< 3.14\text{ V}$** ise sistemi DERHAL kapatın (LDO arızası riski).
2. **Kırpılma / Aşırı Doyum:** Yazılım çıktısında `clipping_detected = True` veya `near_clipping_fraction > 0.05%` (örneğin $> %0.05$) görülürse PAM8403 kazancını (potansiyometreyi) derhal kısın.
3. **Sıfır Sessizlik / Hat Boşluğu:** Sessiz ortam ölçümünde RMS sıfır veya $\le 10^{-6}$ çıkarsa (`INCONCLUSIVE_QUIET_ZERO_OR_INVALID`), I2S hattı bağlı değildir veya mikrofon sessiz dijital çıktı veriyordur; deneyi durdurun.
4. **Paket Kaybı:** CRC hatası ($>0$) veya sequence gap ($>0$) tespit edilirse USB kablosunu ve bağlantı temaslarını kontrol edin.

---

## 4. Adım Adım Deney Akışı ve Kesin Komutlar

### Hazırlık: Sanal Ortam ve Port Tespiti
Laptop üzerinde terminal açıp repo dizinine girin:
```powershell
cd c:\Dev\Antigravity\bitirme\ausculta-forge
.\.venv\Scripts\Activate.ps1
```
ESP32-S3'ü bağlayın ve portu bulun:
```powershell
python -m serial.tools.list_ports
```
*(Örnek olarak USB CDC portunun `COM3` olduğunu varsayalım. Kendi portunuzu yazın!)*

---

### ADIM 1: Sessiz Taban Ölçümü (Quiet Baseline — ŞART!)
Exciter kapalı, laboratuvar sessizken 10 saniyelik ortam gürültüsü profilini alın:
```powershell
python tools/hardware/run_phantom_pcg_experiment.py --port COM3 --reference data/raw/week6_real_pcg_20261026/circor/40058_AV.wav --operator "Kaan_Ozan_Ege" --notes "Step1_Quiet_Baseline_Ambient" --quiet-baseline-only
```
- Bu işlem sonucunda oturum klasöründe oluşan `raw.wav` dosyasının tam yolunu not edin (örn: `experiments/sessions/session_20261125_XXXXXX/raw.wav`).

---

### ADIM 2: Ses Çıkış ve Güvenli Seviye Doğrulaması
Laptop kulaklık/line-out çıkışını PAM8403'e bağlayın. PAM8403 ses düğmesini en kısık seviyeden başlatıp çok hafif açın:
```powershell
python tools/hardware/run_phantom_pcg_experiment.py --verify-audio-routing
```
- Operatör (Kaan & Ozan), exciter'dan gelen test sesinin (120 Hz) aşırı distorsiyonsuz ve çok düşük titreşimle duyulduğunu teyit eder.

---

### ADIM 3: Fiziksel Fantom Uyarım ve S1/S2 Kayıt Oturumu (P0 Kapısı)
1. Exciter'ı Borcam silikon örneğin altına temas ettirin.
2. INMP441 sensörünü silikonun üst merkezine yerleştirin (üzerine 100g test kütlesi koyun).
3. Komutu Adım 1'de aldığınız `--quiet-session` WAV yolu ile çalıştırın:
```powershell
python tools/hardware/run_phantom_pcg_experiment.py --port COM3 --reference data/raw/week6_real_pcg_20261026/circor/40058_AV.wav --quiet-session experiments/sessions/session_20261125_XXXXXX/raw.wav --play-audio --operator "Kaan_Ozan_Ege" --notes "Step3_Phantom_40058_100g_Load"
```

---

## 5. Beklenen Çıktılar ve Karar Matrisi

| Durum Çıktısı | Anlamı | Yapılacak İşlem |
|---|---|---|
| **`PHYSICAL_VERIFIED_PASS`** | SNR $\ge 12\text{ dB}$, Korelasyon $\ge 0.70$, S1/S2 tepe eşleşmesi $\ge \%70$, sıfır CRC/kayıp. | **P0 Başarılı.** Ekran görüntüsü alın, klasörü koruyun, Adım 4'e geçin. |
| **`INCONCLUSIVE_LOW_SNR`** | Aktif sinyal sessiz ortamdan yeterince ayrışmıyor ($< 12\text{ dB}$). | PAM8403 potunu milimetrik açın, sensörün silikona tam temas ettiğinden emin olun. |
| **`INCONCLUSIVE_CLIPPING`** | Sinyal kırpılıyor ($> \%0.05$ tepe doyumda). | PAM8403 potunu kısın, tekrar edin. |
| **`INCONCLUSIVE_POOR_MATCH`** | S1/S2 ritim tepe eşleşmesi yetersiz ($< \%70$). | Akustik sızıntıyı ve ortam konuşmalarını engelleyin, kütleyi 200g yapıp tekrarlayın. |

---

## 6. Acil Durum / Fallback Protokolü (Silikon Kürlenmediyse)

Eğer 23 Kasım'da dökülen RTV-2 silikon sabah kontrolünde hâlâ yapışkan veya tam katılaşmamışsa:
1. Silikonu zorlamayın, Borcam içinden çıkarmayın.
2. Silikonun üst yüzeyine laboratuvarda temin edilen **kuru medikal silikon levha / compliant pad** yerleştirin.
3. Notlara açıkça `--notes "Fallback_Compliant_Pad_Used_Due_To_Tacky_RTV2"` yazın.
4. Bu durum hocanın yönergesine uygun geçerli bir mühendislik adaptasyonudur; asla kürlenmiş gibi sahte beyanda bulunmayın.

---

## 7. Laboratuvar Sonu Kanıt Paketleme

Tüm oturumlar tamamlandığında, tek komutla tüm verileri doğrulanmış ZIP haline getirin:
```powershell
python tools/hardware/pack_lab_return.py --operator "Kaan_Ozan_Ege" --notes "25_Nov_Physical_Lab_Complete"
```
Üretilen `AuscultaForge_Lab_Return_Kaan_Ozan_Ege_*.zip` dosyasını flash belleğe veya ortak alana aktarın.
