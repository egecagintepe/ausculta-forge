# 03 â€” CanlÄ± AkÄ±ÅŸ Mimarisi ve Kayan Pencere Tamponu (Rolling Buffer)

## Bu nedir?

CanlÄ± akÄ±ÅŸ mimarisi, sÃ¼rekli gelen ses verisinin parÃ§a parÃ§a (bloklar halinde) sisteme kabul edilmesi ve son $N$ saniyelik geÃ§miÅŸin (Ã¶r. son 5 saniye) analiz ve gÃ¶rselleÅŸtirme iÃ§in bellekte kayan bir pencere (rolling buffer) iÃ§inde canlÄ± tutulmasÄ±dÄ±r.

---

## Blok TabanlÄ± AkÄ±ÅŸ (Block/Chunk-Based Streaming)

### Neden Tek Tek Ã–rnek (Sample-by-Sample) DeÄŸil?
Dijital ses iÅŸlemede iki uÃ§ yaklaÅŸÄ±m vardÄ±r:
1. **Tek Ã–rnek (Sample-by-sample):** Her Ã¶rnek iÃ§in bir kesme veya Python fonksiyon Ã§aÄŸrÄ±sÄ± yapÄ±lÄ±r. Saniyede 2000 kez Ã§aÄŸrÄ± yapmak CPU baÄŸlam deÄŸiÅŸtirme (context-switch) ve yorumlayÄ±cÄ± (interpreter) ek yÃ¼kÃ¼ doÄŸurur.
2. **Toplu Veri (Batch):** KaydÄ±n tamamÄ± (Ã¶r. 30 saniye) bittikten sonra iÅŸlenir. CanlÄ± izleme ve eÅŸzamanlÄ± gÃ¶rselleÅŸtirme yapÄ±lamaz.

**AuscultaForge Ã‡Ã¶zÃ¼mÃ¼:** Veriler 256 Ã¶rneklik sabit bloklar halinde akar.
- $f_s = 2000\text{ Hz}$ iÃ§in blok sÃ¼resi: $\frac{256}{2000} = 128\text{ ms}$.
- $f_s = 4000\text{ Hz}$ iÃ§in blok sÃ¼resi: $\frac{256}{4000} = 64\text{ ms}$.

> [!NOTE]
> **Gecikme (Latency) Analizi:** 128 ms'lik blok sÃ¼resi uÃ§tan uca gecikmenin tek belirleyicisi deÄŸildir; gecikmeye doÄŸrudan katkÄ± saÄŸlayan temel bileÅŸenlerden biridir. Toplam uÃ§tan uca gecikme; sensÃ¶r edinimi, iletim (transport/UART), tamponlama, DSP filtreleme hesaplama sÃ¼resi ve kullanÄ±cÄ± arayÃ¼zÃ¼ (UI) Ã§izim gecikmelerinin toplamÄ±ndan oluÅŸur. 256 Ã¶rneklik bloklama, Python ve NumPy vektÃ¶rel iÅŸlemlerine yÃ¼ksek hesaplama verimliliÄŸi sunarken gecikmeyi kabul edilebilir sÄ±nÄ±rlar iÃ§inde tutmak iÃ§in seÃ§ilmiÅŸ bir mÃ¼hendislik takasÄ±dÄ±r (trade-off).

---

## SÄ±ra NumaralarÄ± ve Zaman DamgalarÄ±

Her `SampleBlock` iki kritik metaveri taÅŸÄ±r:
1. **`sequence` (SÄ±ra NumarasÄ±):** $0, 1, 2, \dots$ ÅŸeklinde artan tamsayÄ±dÄ±r. Projemizde akÄ±ÅŸ sÄ±rasÄ±nda kaybolan, yinelenen veya sÄ±rasÄ± bozulan bloklarÄ± tespit etmek iÃ§in kullanÄ±lan birincil aÃ§Ä±k (explicit) denetim mekanizmasÄ±dÄ±r.
2. **`timestamp_s` (Zaman DamgasÄ±):** BloÄŸun baÅŸlangÄ±Ã§ zamanÄ±dÄ±r. Zaman damgalarÄ± saat kaymasÄ±nÄ± (drift) tek baÅŸÄ±na engellemez; ancak zamanlama analizi yapmayÄ±, donanÄ±m-yazÄ±lÄ±m saat kaymalarÄ±nÄ± tespit etmeyi (drift detection), zamansal hizalamayÄ± ve Ã§oklu modalite (Ã¶r. ileride olasÄ± EKG entegrasyonu) iÃ§in senkronizasyonu mÃ¼mkÃ¼n kÄ±lar.

---

## Kayan Pencere Tamponu: `RollingBuffer`

[`software/pcg_core/buffers.py`](../../software/pcg_core/buffers.py) sÄ±nÄ±fÄ± sabit sÃ¼reli bir FIFO (First-In-First-Out) bellek alanÄ± yÃ¶netir.

```text
Kapasite: 5.0 saniye (fs=2000 Hz => 10,000 Ã¶rnek)

[â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Eski Ã–rnekler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€]
                       â”‚
                       â”‚ Yeni blok gelir (+256 Ã¶rnek)
                       â–¼
[â”€â”€ En Eski 256 AtÄ±lÄ±r â”€â”€][â”€â”€ KaydÄ±rÄ±lÄ±r â”€â”€][â”€â”€ Yeni 256 Eklenir â”€â”€]
```

### Algoritmik Ã–zellikler
- **BitiÅŸik Bellek ve KaydÄ±rma (Contiguous In-Place Shift):** RollingBuffer, klasik bir dairesel/halka tampon (ring buffer) olarak DEÄÄ°L, yeni bloklar geldikÃ§e veriyi dizi iÃ§inde sola kaydÄ±ran (in-place shift) bitiÅŸik bir tampon olarak uygulanmÄ±ÅŸtÄ±r. TÃ¼keticiler (get_samples() veya get_view()) daima kronolojik sÄ±rada tek parÃ§a bir 1D NumPy dizisi alÄ±r; halka tamponlardaki gibi indeks sarma (wrap-around) veya iki parÃ§alÄ± dilimleme hesaplamalarÄ±na gerek kalmaz.
- **Dinamik Kapasite BaÅŸlatma:** Tampon yaratÄ±lÄ±rken $f_s$ bilinmiyorsa, gelen ilk `SampleBlock`'un frekansÄ±na gÃ¶re $N = \text{int}(\text{capacity\_seconds} \times f_s)$ olarak boyutlandÄ±rÄ±lÄ±r.
- **Frekans DeÄŸiÅŸimi UyarlamasÄ±:** AkÄ±ÅŸ ortasÄ±nda mikrodenetleyici Ã¶rnekleme frekansÄ±nÄ± deÄŸiÅŸtirirse `reset_sample_rate()` ile tampon gÃ¼venle yeniden Ã¶lÃ§eklendirilir.

---

## Neden Bu TasarÄ±m SeÃ§ildi? Hangi Problemleri Ã–nlÃ¼yor?

- **Bellek ÅiÅŸmesini (Memory Leak) Ã–nler:** SÃ¼rekli Ã§alÄ±ÅŸan bir canlÄ± sinyal edinim sisteminde ses dizisi sÄ±nÄ±rsÄ±z bÃ¼yÃ¼yemez; `RollingBuffer` bellek kullanÄ±mÄ±nÄ± sabit (birkaÃ§ yÃ¼z kilobayt) tutar.
- **CanlÄ± Metrik TutarlÄ±lÄ±ÄŸÄ±:** RMS, tepe genlik ve frekans daÄŸÄ±lÄ±mÄ± tÃ¼m kaydÄ±n ortalamasÄ± yerine, incelenen test sinyalinin *son birkaÃ§ saniyelik* anlÄ±k akustik davranÄ±ÅŸÄ±nÄ± yansÄ±tÄ±r.

---

## Ä°lgili Dosyalar ve Testler

- Tampon uygulamasÄ±: [`software/pcg_core/buffers.py`](../../software/pcg_core/buffers.py)
- AkÄ±ÅŸ motoru: [`software/pcg_core/streaming.py`](../../software/pcg_core/streaming.py#L208-L270)
- CanlÄ± CLI gÃ¶sterimi: [`software/pcg_core/stream_demo.py`](../../software/pcg_core/stream_demo.py)
- Testler: [`software/tests/test_streaming.py`](../../software/tests/test_streaming.py#L56-L95)

---

## Sunumda / Savunmada 30 Saniyelik AÃ§Ä±klama

> *"GerÃ§ek zamanlÄ± kalp sesi simÃ¼lasyonunda veriyi 256 Ã¶rneklik bloklar halinde iÅŸliyoruz; bu blok sÃ¼resi (2000 Hz'de 128 ms), uÃ§tan uca gecikmeyi dÃ¼ÅŸÃ¼k tutarken NumPy iÅŸlemlerinde yÃ¼ksek hesaplama verimliliÄŸi saÄŸlar. `RollingBuffer` yapÄ±mÄ±z ise bellekte sinyalin son 5 saniyelik geÃ§miÅŸini kayan bir pencere iÃ§inde tutar. Yeni bloklar geldikÃ§e en eskiler atÄ±lÄ±r; bÃ¶ylece bellek sabit kalÄ±rken sisteme ve gelecekteki kullanÄ±cÄ± arayÃ¼zÃ¼ne anlÄ±k gÃ¼ncellenen RMS ve spektrum bilgisi sunulur."*
