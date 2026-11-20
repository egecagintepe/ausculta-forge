# Module B -- Embedded Acquisition and Data Path
## Submission Folder -- Week 9

| Field | Value |
|---|---|
| **Owner** | Ozan |
| **Module** | B -- Embedded Acquisition and Data Path |
| **Week** | 9 (16–22 Kasım 2026) |
| **Lab Date** | 18 Kasım 2026 |
| **Deliverable** | [W09_B_continuity-clipping-verification.md](W09_B_continuity-clipping-verification.md); [Word REV04](W09_B_system-design-technical-specification_REV04_2026-11-20.docx); [Excel REV04](W09_B_procurement-bom-test_REV04_2026-11-20.xlsx) |
| **Status** | **COMPLETED (Electrical Continuity, Flashing & Zero-Loss Acquisition)** |

## Summary of Completed Work
On 18 November 2026, Ozan conducted the electrical pre-power continuity checks, measured the 3.3V rail (3.28V measured with Agilent U1232A, attested), flashed the ESP32-S3 firmware with SHA-256 verification, and executed the physical G1 pre/post and G2 acquisition tests. Zero in-stream packet or sample loss was achieved across 1.92M samples. Clipping and telemetry metrics were investigated in depth.

## Key Evidence References
- Attestation: `experiments/hardware/team_2026-11-18/g2_physical_attestation.json`
- Flashing: `experiments/hardware/team_2026-11-18/first_flash_log.md`
- G1 Pre/Post Reports: `experiments/hardware/team_2026-11-18/g1_pre_acceptance_report.md`, `g1_post_acceptance_report.md`

## Week 09 REV04 dosyaları (20 Kasım 2026)

- [W09_B_system-design-technical-specification_REV04_2026-11-20.docx](W09_B_system-design-technical-specification_REV04_2026-11-20.docx) — 38 sayfalık sistem tasarımı, G1/G2 gerçek laboratuvar kanıtı ve açık test kapıları
- [W09_B_procurement-bom-test_REV04_2026-11-20.xlsx](W09_B_procurement-bom-test_REV04_2026-11-20.xlsx) — 17 sekme; tedarik, BOM, Week 09 durumu ve test matrisi
- [AuscultaForge_W09_REV04_QA_2026-11-20.md](AuscultaForge_W09_REV04_QA_2026-11-20.md) — satın alma belirsizlikleri, veri bütünlüğü ve kalan işler

**Önemli:** Resmî Week 09 fantom S1/S2 kapısı PENDING'dir. Dört ayrı 10 saniyelik G2 kaydı, kesintisiz 30 dakika testi değildir. 4.246,21 TL toplam geçicidir (90 TL plaket tahmini + 633 TL ürün ekran fiyatları fatura teyidi bekler).
