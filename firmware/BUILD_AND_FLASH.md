# Build and flash the morning release

Read [START_HERE_TOMORROW](../docs/engineering/hardware/START_HERE_TOMORROW.md).
Use the repository root in an exported **ESP-IDF 5.5.1** PowerShell. No global
tool installation is performed by these commands.

```powershell
idf.py --version
.\.venv\Scripts\python.exe tools/hardware/bringup.py doctor
.\.venv\Scripts\python.exe tools/hardware/bringup.py build
```

The builder genuinely runs idf.py reconfigure/build (or first-time set-target
esp32s3/build) and requires exit zero before generating
`firmware/build/release/firmware_build_manifest.json`. The log is
`firmware/build/release-build-output.txt`. Binaries, sdkconfig, partition table,
project_description.json and flasher_args.json stay local. Offsets:
bootloader 0, partitions 0x8000, factory application 0x10000. Never use the
separate I2S compile-check directory for flashing.

The manifest records source commit/dirty state, compiler, versions, config and
lock hashes, artifact hashes, configured memory and available source modes.
Review `source_modes: [1]` for first G1. The target is 16 MB DIO/80 MHz flash,
octal 8 MB/80 MHz PSRAM; actual capacity/boot remains a physical gate.
This factory-only partition layout replaces partition metadata/application;
flashing is not an erase-all operation but can render incompatible old data unusable.

Only after the board inspection, close the selected port's monitors and run:

```powershell
.\.venv\Scripts\python.exe tools/hardware/bringup.py identify --port COM7
.\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port COM7
```

COM7 is an example to replace. Explicit port typing authorizes ROM queries;
`FLASH COM7` separately authorizes write after module/power review. The workflow
checks ESP32-S3/16 MB and stable MAC, validates all artifact hashes/offsets, then
checks identity/hashes again immediately before write. No eFuses, secure boot,
flash encryption, erase_flash or force are used. ROM queries may reset the device;
never probe another person's bridge. A busy port fails with access details.

Post-flash: passive `watch --seconds 30`, selected UART `boot-log` if physically
confirmed, then selected application CDC `hello`, then `g1`. Logs never share
binary CDC: UART0 is the firmware console. Native USB may change COM/VID/PID
between ROM and application. Board connector routing must be physically reviewed.
Recovery is the inspected BOOT/RESET route; save errors before retrying.
