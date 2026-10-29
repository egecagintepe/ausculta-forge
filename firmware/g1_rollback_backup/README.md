# Verified G1 Firmware Rollback Backup

This directory is an **isolated, immutable backup** of the physically verified G1 firmware release (`v1.1.0`, commit `3df4ba8ccbdf2e4d3695399a1c315df4c0d0e475`).
It is decoupled from `firmware/build/release/` so that building or compiling new G2 firmware will never overwrite or invalidate these files.

## Verified Hashes & Inventory

| File | Relative Offset | SHA-256 Hash |
|---|---|---|
| `bootloader/bootloader.bin` | `0x0` | `2796dbba8a3e3dca0bc6588985caaadb234b3c12a721e15a6500d4798ea9807d` |
| `partition_table/partition-table.bin` | `0x8000` | `73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501` |
| `auscultaforge_g1.bin` | `0x10000` | `9ebe95852d92959bf581fbe7fe6da7df8dc3bc745075428e8f57a3726a5ce0b1` |
| `sdkconfig` | Config | `5c137ae2416c5e356a5c6e0488c5b41ae9a194b77a9f4f0bd233054bd364332b` |
| `dependencies.lock` | Component lock | `618443a9d9b1ffd85d4920b41211b6712d1c16887c7c93ed807e9127acbfb330` |

## How to Rollback to G1

If any G2 hardware or firmware experiment fails or locks up:
1. Disconnect the microphone and peripheral wiring with power removed.
2. Put the ESP32-S3 into ROM Bootloader mode (Hold `BOOT` button $\rightarrow$ Press and release `RESET` $\rightarrow$ Release `BOOT`).
3. Identify the port and flash using this immutable manifest:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port COM_ROM --manifest firmware/g1_rollback_backup/firmware_build_manifest.json
   ```
4. Enter `FLASH COM_ROM` to authorize.
5. Reconnect to the new application CDC port and verify with:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port COM_CDC
   .\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port COM_CDC
   ```
