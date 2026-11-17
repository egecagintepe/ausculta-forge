# Staged G1 Release Package (2026-11-17)

- **Status:** `COMPILED_BUT_NOT_FLASHED`
- **Source Modes:** `[1]` (Deterministic G1 generator only; `source_mode=0` intentionally disabled)
- **ESP-IDF / Toolchain:** `v5.5.1` / `xtensa-esp-elf-gcc 14.2.0`
- **Target:** `esp32s3` (16 MB Flash DIO 80 MHz, 8 MB Octal PSRAM)

## SHA-256 Inventory

| File | Offset / Role | SHA-256 |
| --- | --- | --- |
| `bootloader/bootloader.bin` | `0x0` | `52db976aa3d20ab4c1f112832f1c74fa5c591fc1d887c6498a236aaa4f6d5dfd` |
| `partition_table/partition-table.bin` | `0x8000` | `73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501` |
| `auscultaforge_g1.bin` | `0x10000` (268,112 B) | `bd48630874e531f2d761ed0e39f27c90d5d7271223a6566acbf1bc620b919837` |
| `sdkconfig` | Build configuration | `5c137ae2416c5e356a5c6e0488c5b41ae9a194b77a9f4f0bd233054bd364332b` |
| `dependencies.lock` | Component lock | `618443a9d9b1ffd85d4920b41211b6712d1c16887c7c93ed807e9127acbfb330` |

*Note:* The earlier physically verified immutable rollback release remains untouched in `../../g1_rollback_backup/`.
