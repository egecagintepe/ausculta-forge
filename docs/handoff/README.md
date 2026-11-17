# AuscultaForge — Hardware Integration Handoff (2026-11-17 / 2026-11-18)

Bu klasör, 18 Kasım 2026 Çarşamba günü **Kaan** (Modül A — Donanım) ve **Ozan** (Modül B — Gömülü & CLI) tarafından Ege olmadan yürütülecek fiziksel entegrasyon için tam, emniyet kilitli devir paketidir.

## Handoff Belgeleri (Sırayla Okuyun)

| Belge | Kime / Amacı |
| :--- | :--- |
| [START_HERE_2026-11-18.md](START_HERE_2026-11-18.md) | **Kaan & Ozan Başlangıç Rehberi (Türkçe):** 1 sayfalık adım adım komutlar, rol dağılımı ve örnek çıktılar. |
| [AGENT_WEDNESDAY_2026-11-18.md](AGENT_WEDNESDAY_2026-11-18.md) | **Çarşamba Antigravity Ajan Görevi:** Kendi ajanınıza vereceğiniz bağımsız operasyon talimatı (H0 $\to$ G1 $\to$ G2, tek seferlik fotoğraf/ölçüm talebi, PR). |
| [HARDWARE_GATES_AND_ROLLBACK.md](HARDWARE_GATES_AND_ROLLBACK.md) | **Elektriksel Güvenlik & G1 Rollback:** 3.3V ölçüm sınırı, 5V yasağı, pin kısıtları, PAM8403 BTL uyarısı, durdurma kuralları ve acil G1 geri dönüşü. |
| [RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md](RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md) | **Sürüm, Hash ve Kanıt İndeksi:** Commit SHA, binary SHA-256 doğrulama tabloları, güncel test sonuçları, SDK `ldgen.py` notu ve açık fiziksel kapılar. |

## İlgili Araçlar ve Sürüm Paketleri

- **Tek Komut Çarşamba Otonom Orchestrator:** [`tools/hardware/wednesday_lab.py`](../../tools/hardware/wednesday_lab.py) *(preflight, USB keşfi, HELLO, devam edilebilir G1, H0/G2 kapısı, sessiz/uyaranlı G2 WAV kaydı, qualify karşılaştırma, kanıt ZIP'i ve opsiyonel GitHub yüklemesi; Device Center içinde de `Wednesday Lab Mode` kartı vardır)*
- **Windows Otomasyon & Teslim Betikleri (Git Gerekmez):** [`scripts/handoff/windows_setup.ps1`](../../scripts/handoff/windows_setup.ps1) *(Python/Node yoksa kullanıcı kapsamlı kurar; G2 adayı varsa ESP-IDF indirmez)* | [`scripts/handoff/windows_preflight.ps1`](../../scripts/handoff/windows_preflight.ps1) | [`scripts/handoff/pack_wednesday_results.ps1`](../../scripts/handoff/pack_wednesday_results.ps1) | [`tools/hardware/bringup.py`](../../tools/hardware/bringup.py) | [`tools/hardware/pack_lab_return.py`](../../tools/hardware/pack_lab_return.py)
- **Hazırlanan Binary Paketleri:**
  - G1 Rollback (Değiştirilemez): [`firmware/g1_rollback_backup/firmware_build_manifest.json`](../../firmware/g1_rollback_backup/firmware_build_manifest.json)
  - G1 Staged Release (2026-11-17): [`firmware/releases/g1_release_20261117/firmware_build_manifest.json`](../../firmware/releases/g1_release_20261117/firmware_build_manifest.json)
  - G2 Candidate (Yetkilendirme Bekliyor): [`firmware/releases/g2_candidate_20261117/firmware_build_manifest.json`](../../firmware/releases/g2_candidate_20261117/firmware_build_manifest.json)
- **Mühendislik Donanım Kontrol Listeleri:** [INMP441 First Acquisition](../engineering/hardware/INMP441_FIRST_ACQUISITION.md) | [Preliminary Pin Plan](../engineering/hardware/PRELIMINARY_PIN_PLAN.md) | [Physical Inspection Checklist](../engineering/hardware/PHYSICAL_INSPECTION_CHECKLIST.md) | [Windows Laptop Setup](../engineering/hardware/WINDOWS_LAPTOP_SETUP.md)
- **Dönem İlerleme Raporu (As-Of 2026-11-17):** [PROGRESS_ASOF_2026-11-17.md](../sdp/PROGRESS_ASOF_2026-11-17.md)
