# AuscultaForge — Windows Lab Laptop Single Execution Prompt
*(25 November 2026 Laboratory Session / 25 Kasım 2026 Laboratuvar Oturumu)*

> **Usage:** Copy and paste the entire block below directly into Antigravity on the lab laptop.
> **Kullanım:** Aşağıdaki metin bloğunun tamamını kopyalayıp laboratuvar laptopundaki Antigravity sohbetine yapıştırın.

---

```markdown
Sen AuscultaForge projesinin 25 Kasım 2026 fiziksel laboratuvar oturumunu yöneten otonom yapay zeka asistanısın.

Repo kök dizinindesin. Proje aktif olarak `feature/rev04-evidence-integration` branch'indedir (PR #36).
Tüm ön hazırlık, testler ve otomasyon scriptleri tamamlanmıştır.

Laboratuvar oturumunda görevimiz: Week 9 Fiziksel Fantom S1/S2 Ses İletim Kapısını (P0) başarıyla icra etmek, doğrulamak ve kanıt paketini (ZIP) üretmektir.

Çalışma prensipleri ve rol ayrımı:
1. Sen (Antigravity): Ortam kontrolünü, sanal ortam kurulumunu, port keşfini, terminal komutlarını, SHA-256 doğrulamasını, analiz metriklerini ve ZIP kanıt paketlemesini yöneteceksin. Kullanıcıya asla rastgele COM portu yazdırmayacaksın.
2. İnsan Ekip (Kaan, Ozan, Ege): Yalnızca fiziksel bench doğrulamalarını yapacak (silikon kürlenme kontrolü, bağımsız 5V PAM8403 beslemesi, multimetre 3.3V ölçümü, sessiz oda ortamı ve titreşim hissi).

Lütfen sırasıyla aşağıdaki iki aşamayı uygula:

### AŞAMA 1: ÇEVRİMDIŞI ORTAM VE TEST DOĞRULAMASI (Ön Kontrol)
1. PowerShell terminalinde ortamı doğrula:
   `powershell -ExecutionPolicy Bypass -File .\tools\hardware\run_lab_phantom_workflow.ps1 -SetupOnly`
   (Eğer .venv yoksa otomatik bootstrap eder; Python bağımlılıklarını ve 35/35 birim testini denetler.)
2. Simülasyon smoke check çalıştır:
   `powershell -ExecutionPolicy Bypass -File .\tools\hardware\run_lab_phantom_workflow.ps1 -Simulate`
3. Aşama 1 sonuçlarını kısa bir özetle bildir ve fiziksel donanım aşamasına geçmeye hazır olduğunu belirt.

### AŞAMA 2: CANLI FİZİKSEL FANTOM DENEYİ (P0 Gate)
Fiziksel donanım bağlandığında ekiple şu kontrolleri teyit et ve canlı iş akışını başlat:
- Kaan: RTV-2 silikon kürlendi mi? (Yapışkansa yedek elastomer kullanıldı mı?) Mikrofon portu açık mı?
- Ozan: PAM8403 bağımsız 5V beslemede mi? OUT+ / OUT- kesinlikle GND'ye bağlı DEĞİL mi (BTL çıkış)? Multimetre ile ESP32-S3 3.3V rayı (3.14 - 3.46 V) doğrulandı mı? Potansiyometre minimumda mı?
- Canlı iş akışı komutunu çalıştır:
   `powershell -ExecutionPolicy Bypass -File .\tools\hardware\run_lab_phantom_workflow.ps1`
   Bu komut:
   a. ESP32-S3 USB CDC (0x303A) portunu otomatik bulur.
   b. 10 saniyelik sessiz taban kaydını (quiet baseline) alır ve SHA-256 hesaplar.
   c. -18 dBFS kalibrasyon tonu çalar ve operatörden "EVET" fiziksel teyidi bekler.
   d. CirCor `40058_AV.wav` referans sesini PAM8403 üzerinden çalarak eşzamanlı INMP441 kaydını alır.
   e. Kırpılma (<0.05%), SNR (>=12 dB) ve S1/S2 spektral enerjisini doğrular.
   f. Tüm raporları ve WAV dosyalarını zaman damgalı ZIP olarak paketler.
4. Çıkan test sonuçlarını (PASS / FAILED), SNR değerini, kırpılma oranını ve üretilen ZIP dosyasının SHA-256 değerini ekrana yaz.
```
