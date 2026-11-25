# AuscultaForge — 25 Kasım 2026 Laboratuvar Uygulama Föyü (Lab Run Sheet)

**Tarih:** 25 Kasım 2026 Çarşamba Sabahı  
**Ders:** EEE 495 / SDP4 — Akıllı Dijital Stetoskop  
**Öncelik:** P0 — Hafta 9 Fiziksel Fantom S1/S2 Kabul Kapısı  

---

## 1. Zorunlu Fiziksel Zincir ve Mekanik Kurallar

Deney düzeneği **kesinlikle** aşağıdaki zincir sırasıyla kurulacaktır:

`PC Ses Çıkışı -> PAM8403 Amplifikatör -> 30 mm / 12 Ω Exciter -> Titreşim Aktarım Plakası -> Tam Kürlenmiş Uyumlu Fantom -> Stetoskop Göğüs Parçası (Chestpiece) -> Sızdırmaz Akustik Boşluk -> INMP441 MEMS Mikrofon -> ESP32-S3 -> USB CDC -> Host PC`

> [!CAUTION]
> **MEKANİK VE KİMYASAL YASAKLAR:**
> 1. **MEMS mikrofonu (INMP441) ASLA doğrudan silikon üzerine koymayın ve mikrofonun alt akustik deliğini tıkamayın!** Mikrofon, stetoskop başlığına bağlı sızdırmaz akustik boşluk içinde yer almalıdır.
> 2. **Kısmen kürlenmiş veya yapışkan RTV-2 silikonu — üzerine koruyucu ped koyarak bile — KESİNLİKLE kullanmayın!** Kürlenme kontrolünden geçemezse RTV-2 örneğini kenara ayırın; yerine **ayrı, tamamen kürlenmiş uyumlu bir elastomer/ped** kullanın ve notlara malzeme değişikliğini yazın. Doku eşdeğerliği iddiasında bulunmayın.

---

## 2. Elektriksel Güvenlik ve BTL İzolasyon Kuralları

- **Bağımsız Besleme:** PAM8403 amplifikatörü **bağımsız regüle 5 V** kaynakla (USB powerbank veya izole 5 V DC kaynak), INMP441 ise ESP32-S3 **3.3 V** regüle rayından ($3.14\text{ V} \le V_{\text{DD}} \le 3.46\text{ V}$) beslenecektir. Şebeke (220 V) bağlantısı kesinlikle yasaktır.
- **BTL Çıkış Uyarısı (PAM8403):** PAM8403 köprü (BTL) çıkışlıdır. **Hoparlör/exciter çıkış uçlarından (OUT+ veya OUT-) hiçbirini ASLA toprağa (GND) bağlamayın!** Kısa devre amplifikatörü yakar.
- **Ses Seviyesi:** Deneye PAM8403 potansiyometresi en kısık konumdayken başlayın; `clipping_detected = True` veya `near_clipping > %0.05` görülürse derhal kısın.
- **İnsan Denek Yasağı:** Hiçbir aşamada (ekip üyeleri dahil) insandan kayıt alınmayacaktır.

---

## 3. Ekip Rolleri ve Envanter Ayrımı

| Operatör | Modül | Sorumluluk |
|---|---|---|
| **Ünal Kaan Öztürk** | **Modül A** | Fantom kürlenme kontrolü, mekanik zincir (exciter → plaka → fantom → chestpiece → akustik kavite → INMP441), 100g/200g yükleme ve ortam izolasyonu. |
| **Özgür Ozan Yıldız** | **Modül B** | Multimetre ile 5V ve 3.3V ray doğrulaması, PAM8403 BTL çıkış kontrolü, USB CDC/ROM port tespiti, potansiyometre kazanç takibi. |
| **Ege Çağın Tepe** | **Modül C** | Host laptop çalıştırma (`run_lab_phantom_workflow.ps1` / CLI), sessiz taban kaydı, S1/S2 ve SNR rapor doğrulaması, kanıt paketleme. |

*Envanter Notu:* Sipariş edilen veya eksik olan fiziksel bileşenler (ör. stetoskop başlığı veya kürlenmiş silikon) laboratuvar masasında fiziksel olarak doğrulanana kadar "varsayılan hazır" kabul edilmez; eksik parça durumunda keşifsel uyarım/yedek materyal not edilir.

---

## 4. Doğrulanmış ve Çalıştırılabilir Laboratuvar Komutları

### Seçenek A: Tek Komutla Etkileşimli Laboratuvar İş Akışı (Önerilen)
```powershell
cd c:\Dev\Antigravity\bitirme\ausculta-forge
.\tools\hardware\run_lab_phantom_workflow.ps1
```
*(Bu script sırasıyla: port taraması, 10s sessiz taban kaydı, -18 dBFS kalibrasyon tonu, operatör onayı, senkronize PCG deneyi ve kanıt ZIP paketlemesini yürütür.)*

### Seçenek B: Adım Adım Manuel CLI Komutları
1. **USB CDC Port Tespiti:**
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/run_phantom_pcg_experiment.py --discover-ports
   ```
2. **10s Sessiz Taban Kaydı (Exciter kapalı, oda sessiz):**
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/run_phantom_pcg_experiment.py --quiet-baseline-only --port COMxx --operator "Kaan_Ozan_Ege" --notes "Step1_Quiet_Baseline"
   ```
   *(Çıktıdaki `raw_wav_path` yolunu kopyalayın!)*
3. **Düşük Seviyeli Kalibrasyon Tonu (-18 dBFS, 120 Hz):**
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/run_phantom_pcg_experiment.py --play-calibration-tone
   ```
4. **Senkronize Fiziksel Fantom Deneyi (Sessiz Referans + Ses + Operatör Onayı Zorunlu):**
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/run_phantom_pcg_experiment.py --port COMxx --reference data/raw/week6_real_pcg_20261026/circor/40058_AV.wav --quiet-session <ADIM_2_RAW_WAV_YOLU> --play-audio --verify-audio-routing --operator "Kaan_Ozan_Ege" --notes "W10_P0_Physical_Phantom_Trial1"
   ```
5. **Kanıt Paketleme (Tüm `experiments/phantom/` ve `sessions/` verileri dahil):**
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/pack_lab_return.py --operator "Kaan_Ozan_Ege" --notes "25_Nov_Lab_Return"
   ```

---

## 5. P0 Hata Kurtarma ve Firmware Geri Dönüş (Rollback) Prosedürü

- **P0 Başarısızlık Kurtarma:**
  - *Düşük SNR ($<12\text{ dB}$):* Chestpiece sızdırmazlığını ve exciter temasını kontrol edin; PAM8403 potunu hafifçe açın.
  - *Kırpılma ($>\%0.05$):* PAM8403 potunu hemen kısın.
  - *USB Hatası:* Başka seri port programı (Arduino/PuTTY) açıksa kapatın, kabloyu çıkarıp takın.
- **Bilinen Çalışan G2 Firmware Geri Dönüşü (Sadece Gerekirse):**
  - Mevcut çalışan G2 adayı (`firmware/releases/g2_candidate_20261117`) üzerinde hiçbir değişiklik yapılmamıştır; **P0 öncesinde karta yeni firmware yüklemeyin.**
  - Kartta sorun olursa orijinal ikili dosyalar `firmware/releases/g2_candidate_20261117/` altındadır (`bootloader.bin` @ `0x0`, `partition-table.bin` @ `0x8000`, `ausculta_g1.bin` @ `0x10000`).
