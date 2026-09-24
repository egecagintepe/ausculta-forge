# AuscultaForge: MCU ↔ PC Yazılım Arayüzü — Taslak

Bu belge wire/serial protokolü değildir. Kaan ile karar verilmeden byte-level
format KİLİTLENMEYECEK.

PC yazılımının ihtiyaç duyduğu kavramsal bilgi:

| Alan | Amaç |
|---|---|
| sequence | Kayıp / sıra bozulması tespiti |
| timestamp | Zamanlama ve gecikme analizi |
| sample_rate_hz | DSP pipeline yapılandırması |
| samples[] | PCG örnekleri |
| device_status | Opsiyonel tanılama bilgisi |
| flags | Overflow vb. olaylar |

## İlk prensipler

- UI, seri port/Wi-Fi kodunu doğrudan bilmemeli.
- Donanımdan gelen veri önce `SampleBlock` nesnesine dönüştürülmeli.
- Aynı DSP kodu Mock, WAV, USB veya Wi-Fi kaynağında çalışmalı.
- Gerçek wire format; ESP32-S3, örnek genişliği ve aktarım yöntemi netleşince
  Kaan ile birlikte belirlenecek.
