# Staged G2 INMP441 Candidate Package (2026-11-17)

- **Status:** **`PREPARED_NOT_AUTHORIZED_FOR_FLASH`**
- **Source Modes:** `[1, 0]` (Deterministic G1 + Live I²S INMP441)
- **Candidate Pin Profile (Provisional):** `BCLK=GPIO4`, `WS=GPIO5`, `DIN=GPIO6`, `L/R=GND` (`left` slot), 48 kHz Philips I²S stereo-32 slot (24-bit signed mono left extraction)
- **ESP-IDF / Toolchain:** `v5.5.1` / `xtensa-esp-elf-gcc 14.2.0`

## Authorization Gate Required Before Flash

`tools/hardware/bringup.py flash` will **reject** this package until the operator completes:
1. Double-sided PCB/breakout photo verification and power-off `VDD-GND` short check.
2. Live ESP32 `3V3` rail multimeter measurement (`3.15 V .. 3.45 V` with mic disconnected).
3. Confirmation of physical pins matching `BCLK=4, WS=5, DIN=6, L/R=GND` via:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py authorize-g2 --bclk 4 --ws 5 --din 6 --slot left --vdd-volts <MEASURED_VDD> --operator "<NAME>" --multimeter "<METER_ID>"
   ```
   *(If actual PCB wiring uses different GPIOs or Right slot, do NOT use this binary; reconfigure via `idf.py menuconfig` and rebuild with `bringup.py build`.)*

## SHA-256 Inventory

| File | Offset / Role | SHA-256 |
| --- | --- | --- |
| `bootloader/bootloader.bin` | `0x0` | `28e9a026860d4b75c1573dacdf89570770186435983156b3347a107925e6dbe0` |
| `partition_table/partition-table.bin` | `0x8000` | `73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501` |
| `auscultaforge_g1.bin` | `0x10000` (294,880 B) | `22af47eef7a4a51765254a1144627bf44b39c53dfab8b8ce13f18a10ebd67dbb` |
| `sdkconfig` | Build configuration | `fc56de3b431da13d219b1a1a99acc783834760ab8fb59283eb78ab0a60f1ef71` |
| `dependencies.lock` | Component lock | `618443a9d9b1ffd85d4920b41211b6712d1c16887c7c93ed807e9127acbfb330` |
