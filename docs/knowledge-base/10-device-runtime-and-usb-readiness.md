# 10 — Cihaz Çalışma Zamanı Temeli ve USB Hazırlığı (Device Runtime Foundation & USB Readiness)

## Bu nedir?

Bu doküman, AuscultaForge projesinde fiziksel ESP32-S3 donanımının bağlanmasına yönelik **Cihaz Çalışma Zamanı Temeli (Device Runtime Foundation)** mimarisini açıklar.

Bu mimari fazının temel ilkesi:
> **"Fiziksel donanım henüz mevcut değilken varmış gibi davranmamak (No Fake Hardware Masquerade); ancak donanım takıldığı anda sisteme tam entegre olacak donanım-hazır (hardware-ready) soyutlama katmanını şimdiden tamamlamak."**

Uygulama artık başlangıçta sahte bir canlı cihaz akışıyla başlamaz. Donanım bağlı değilken gerçek sistem durumu dürüstçe `NO DEVICE CONNECTED / WAITING FOR AUSCULTAFORGE DEVICE` olarak bildirilir.

---

## 1. Cihaz Yaşam Döngüsü Durum Makinesi (Device Lifecycle State Machine)

Fiziksel bir medikal/akustik cihazın ana bilgisayara bağlanması, el sıkışması, akış başlatması ve olası bağlantı kopmalarını yönetmesi için açık bir durum makinesi uygulanmıştır (`DeviceState`):

```text
       ┌──────────┐
       │  ABSENT  │ ◄────────────────────────┐
       └────┬─────┘                          │
            │ attach candidate               │ disconnect / reset
            ▼                                │
      ┌───────────┐                          │
      │ DETECTED  │ ─────────────────────────┤
      └─────┬─────┘                          │
            │ attach transport               │
            ▼                                │
      ┌───────────┐                          │
      │  OPENING  │ ──(open failed)──► ERROR ┘
      └─────┬─────┘
            │ transport opened
            ▼
     ┌─────────────┐
     │ HANDSHAKING │ ──(incompatible caps)──► INCOMPATIBLE
     └──────┬──────┘
            │ valid caps negotiated
            ▼
        ┌───────┐
        │ READY │ ◄────────────────────────┐
        └───┬───┘                          │
            │ start_streaming              │ stop_streaming
            ▼                              │
      ┌───────────┐                        │
      │ STREAMING │ ───────────────────────┘
      └─────┬─────┘
            │ physical link dropped
            ▼
     ┌─────────────┐
     │ INTERRUPTED │ ──(candidate reappears)──► DETECTED
     └─────────────┘
```

### Durumların Tanımları

1. **`ABSENT`:** Sistemde AuscultaForge donanım adayı algılanmamıştır. Varsayılan başlangıç durumudur.
2. **`DETECTED`:** İşletim sistemi veya discovery katmanı uyumlu bir USB adayı görmüştür; henüz transport açılmamıştır.
3. **`OPENING`:** Cihaz dosya tanıtıcısı / USB uç noktası açılmaktadır.
4. **`HANDSHAKING`:** Transport açılmıştır; protokol sürümü, örnekleme frekansı ve kanal yetenekleri el sıkışması yapılmaktadır.
5. **`READY`:** El sıkışması doğrulanmış, cihaz parametreleri onaylanmış ve veri akışına hazır duruma gelmiştir.
6. **`STREAMING`:** Cihazdan aktif olarak akustik paketler akmaktadır.
7. **`INTERRUPTED`:** Akış sırasında fiziksel kablo çıkmış veya bağlantı beklenmedik biçimde kopmuştur.
8. **`ERROR`:** Transport açma veya G/Ç hatası meydana gelmiştir.
9. **`INCOMPATIBLE`:** Donanım el sıkışmasında desteklenmeyen protokol sürümü, geçersiz örnekleme hızı veya çoklu kanal bildirmiştir.

Geçersiz durum geçişleri (örneğin `ABSENT` durumundan doğrudan `STREAMING` durumuna atlama) çekirdek katmanda `InvalidStateTransitionError` ile kesin olarak reddedilir.

---

## 2. Sıcak Tak-Çıkar (Hot-Plug) ve Donanım Keşif Soyutlaması

Hot-plug mekanizması, `DeviceDiscoveryProvider` soyut arayüzü ile işletim sistemi olaylarından soyutlanmıştır.

- **Üretim Davranışı (`PendingDescriptorDiscoveryProvider`):** 
  Ekip 26 Eylül 2026 kararıyla ESP32-S3 Yerel USB (Native USB) mimarisini seçmiş; ancak USB sınıfı (CDC-ACM vs Vendor Bulk) ve VID/PID henüz dondurulmamıştır. Bu nedenle üretim keşif sağlayıcısı sisteme sahte cihaz raporlamaz; dürüstçe `Hardware discovery configuration pending Phase-1 USB descriptor decision` raporlar.
- **Gelecek Entegrasyonu:**
  USB VID/PID tanımlandığında, yalnızca keşif filtresi kuralı eklenecek; DSP boru hattı, UI ve durum makinesi tek bir satır dahi değişmeyecektir.

---

## 3. Taşıma Katmanı Soyutlaması (`DeviceTransport`)

Donanım taşıma katmanı bir Python protokolü / soyut sınıfı olarak tanımlanmıştır:
```python
class DeviceTransport(Protocol):
    def open(self) -> None: ...
    def close(self) -> None: ...
    def is_connected(self) -> bool: ...
    def read(self, max_bytes: int = 4096, timeout_s: float = 1.0) -> bytes: ...
    def write_control(self, payload: bytes) -> None: ...
```

### CDC-ACM vs Vendor Bulk Kararı Neden Bilinçli Olarak Ertelendi?

1. **İkili Veri vs Metin İletişimi:** CDC-ACM (Sanal Seri Port) işletim sistemlerinde ek sürücü istemeden açılır; ancak işletim sistemi seri port tamponlarında (line buffering, parity, baudrate simülasyonu) akustik veri için gereksiz yük oluşturabilir.
2. **Vendor Bulk Transfer:** Doğrudan WinUSB / libusb uç noktası üzerinden çalışır, sıfır seri ek yükü ve deterministik transfer sunar; ancak Windows tarafında sürücü yükleme (INF / WinUSB WCID) gerektirir.
3. **Mühendislik İlkesi:** Donanım benchmark testleri tamamlanmadan yazılımda aceleyle bir USB sınıfına kilitlenmek mimari borç yaratır. Bu nedenle transport soyutlaması oluşturulmuş, somut sürücü seçimi donanım test kapısına bırakılmıştır.

---

## 4. El Sıkışması ve Donanım Yetenekleri Modeli (`DeviceCapabilities`)

El sıkışması mantığı ikili bayt formatından bağımsızdır. `DeviceCapabilities` modeli semantik olarak doğrulanır:
- **`protocol_version`:** `"1.0"` olmalıdır (farklı sürümler reddedilir).
- **`sample_rate_hz`:** Yalnızca onaylanmış akustik hızlar kabul edilir (`2000`, `4000`, `8000 Hz`).
- **`sample_format`:** `"float32"` veya `"int16"`.
- **`channels`:** Faz-1 için kesinlikle mono (`1`). Stereo veya çok kanallı talepler reddedilir.

---

## 5. Semantik Paket Katmanı (`DeviceSamplePacket`) vs İkili Tel Kodlama

Gelecekte ESP32-S3'ten akacak paketlerin mantıksal yapısı belirlenmiştir:
- Senkronizasyon (Sync)
- Sıra Numarası (Sequence Number)
- Zaman Damgası (Timestamp)
- Örnek Yükü (Sample Payload)
- Durum / Hata Bayrakları (Status / Error Flags)
- CRC Denetimi (CRC Check)

**Bilinmeyen bilinmeyen kalır:** Bayt genişlikleri, endian sırası, CRC polinomu ve bayt çerçeveleme henüz dondurulmadığı için uydurma ikili bayt kodlaması yapılmamıştır. Bunun yerine semantik model (`DeviceSamplePacket`) ve test edilmiş `packet_to_sample_block()` adaptörü tamamlanmıştır.

İkili kodlayıcı/kod çözücü (wire codec) dondurulduğunda araya yalnızca bir bayt ayrıştırıcı eklenecek, mevcut DSP boru hattı doğrudan çalışacaktır.

---

## 6. Sıra Numarası, Zaman Damgası ve CRC'nin Rolü

Fiziksel USB bağlantısında elektriksel parazitler veya işletim sistemi zamanlayıcı gecikmeleri paket kaybına neden olabilir. `DeviceIntegrityStats` çalışma zamanında aşağıdaki sayaçları izler:
- **`sequence_gaps`:** Sıra numarası atlaması (paket kaybı).
- **`repeated_packets`:** Tekrarlanan sıra numarası.
- **`out_of_order_packets`:** Sırasız gelen paketler.
- **`crc_failures`:** Veri bozulması.
- **`timestamp_regressions`:** Zaman damgası gerilemesi.

---

## 7. Bağlantı Kopması ve Yeniden Bağlanma (Disconnect / Reconnect)

1. **Akış Sırasında Kablo Çıkarsa:**
   - Cihaz durumu `STREAMING` -> `INTERRUPTED` olur.
   - UI anında gerçek kesilme durumunu yansıtır.
2. **Kayıt Sırasında Kablo Çıkarsa:**
   - Kayıt sessizce devam etmez veya askıda kalmaz.
   - Oturum derhal sonlandırılır, tamamlanmamış kayıt dürüstçe `termination_reason: "device_disconnected"` metaverisi ile mühürlenir.
3. **Yeniden Bağlantı:**
   - Cihaz tekrar takıldığında `DETECTED -> HANDSHAKING -> READY` döngüsünden geçer.
   - Kesilen kayıt otomatik olarak devam ettirilmez (kullanıcının açık onayı gerekir).

---

## 8. Testlerde Neden Test Çiftleri (Fakes) Kullanılır?

Üretim kullanıcı arayüzünde sahte donanım göstermek yasaktır; ancak durum makinesini, el sıkışmayı, CRC kontrollerini ve kablo kopma senaryolarını test etmek için otomatik testlerde `InMemoryFakeTransport` ve `FakeDiscoveryProvider` gibi test çiftleri kullanılır.

Bu çiftler yalnızca `software/tests/` altında yaşar ve üretim koduna sızmaz. Bu sayede donanım laboratuvarda fiziksel olarak üretilmeden önce masaüstü uygulamasının tüm yaşam döngüsü yüzde yüz test kapsamıyla garanti altına alınır.

---

## 9. 30 Saniyelik Bitirme Savunması Açıklaması

> *"AuscultaForge masaüstü uygulaması, ESP32-S3 donanımına tam hazır bir durum makinesi ve transport soyutlaması üzerine kurulmuştur. Henüz donanım üretilmediği için sistemde sahte bir cihaz takılıymış gibi davranmıyoruz; sistem dürüstçe 'No Device' durumunda bekler. Donanımın USB sınıfı ve paket çerçeveleme parametreleri donanım test kapısında kesinleştiğinde, çekirdek mimariyi ve DSP boru hattını değiştirmeden sadece transport sürücüsünü devreye alacağız. Tüm hata, kopma ve el sıkışma senaryoları otomatik testlerle kanıtlanmıştır."*
