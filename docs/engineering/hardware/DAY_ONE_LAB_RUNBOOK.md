# Day-one laboratory runbook — Ege and Kaan

**PHYSICAL_HARDWARE_BRINGUP: NOT_EXECUTED. Physical G1: PENDING.**
Bring the purchased board, a known USB data cable, multimeter, soldered INMP441
headers, breadboard/jumpers and photographs. Keep the microphone disconnected for
the first G1. Ege operates software; Kaan checks power/assembly. Ozan can peer-review.

## One-page quickstart — exact beginner actions

1. Photograph both board sides, module marking, connectors and button labels.
   Open Windows Start, type **Device Manager**, open **Ports (COM & LPT)**. Connect
   one cable to one inspected connector; note which port appears. Do not attach
   both connectors until power routing is known. Compare the
   [board dossier](BOARD_DOSSIER_DSTK22852.md).
2. Open PowerShell in `C:\Dev\Antigravity\bitirme\ausculta-forge`. Run:
   ```powershell
   .\tools\hardware\windows_preflight.ps1 -Output .\experiments\hardware\preflight.json
   ```
   This scans only; it never opens COM ports. NOT_DETECTED is useful information,
   not a damaged-board diagnosis. Verify the cable has data lines yourself.
3. Open the pinned **ESP-IDF 5.5.1** shell. If using this workstation's local
   installed toolchain, paste this session-only setup (no system PATH changes):
   ```powershell
   Set-Location C:\Dev\Antigravity\bitirme\ausculta-forge
   $env:IDF_TOOLS_PATH = Join-Path (Get-Location) 'firmware/build/idf-tools'
   $env:IDF_PYTHON_ENV_PATH = Join-Path $env:IDF_TOOLS_PATH 'python_env/idf5.5_py3.11_env'
   $env:PATH = 'C:\Users\egeca\AppData\Local\Programs\Python\Python311;' + $env:PATH
   . ./firmware/build/esp-idf-v5.5.1/export.ps1
   .\.venv\Scripts\python.exe tools/hardware/preflight.py --json
   .\.venv\Scripts\python.exe tools/hardware/bringup.py build
   ```
   Another PC must install IDF using the preceding
   [Windows guide](FIRST_PHYSICAL_USB_BRINGUP_GUIDE.md); local ignored build/tool
   folders are not distributed by Git. Stop on any build failure.
4. With the actual programming port identified, substitute its COM number:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port COM_VERIFIED
   ```
   Type the selected port only after checking PCB/connector. The tool reads ROM
   chip/flash identity, validates image hashes, then separately asks you to type
   `FLASH COM_VERIFIED`. That second confirmation is the only write authorization.
   A successful flash is still **not a verified boot or G1 pass**.
5. Restart normally. The native USB port can disappear and return as another COM
   number. Rescan Device Manager. Close any monitor on the data port. Do not reuse
   a ROM COM number blindly. Firmware UART logs should show Canonical B 1.1.0,
   pending physical gates and health counters; debug is UART0, never binary CDC.
6. Launch the existing AuscultaForge Desktop. Device Center → Scan USB → select
   the inspected **application CDC** → Connect & HELLO. The firmware version and
   handshake verification appear. “PORT DETECTED” is not firmware verification.
   Select deterministic G1 and Start. The Desktop requests STOP at 480000 samples;
   require STOP_ACK and the full acceptance result. Export auditable G1 evidence.
7. Alternatively, with Desktop disconnected so it releases the port:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port COM_DATA_VERIFIED
   ```
   Confirm the inspected port. This physical-only command rejects simulation,
   runs the production engine and saves even failing acceptance evidence under
   `experiments/hardware/<UTC_session>/`. Never run two readers on one COM port.
8. Only after a complete physical G1 pass, follow
   [INMP441 assembly and qualification](INMP441_FIRST_ACQUISITION.md). Confirm 3.3 V
   with a meter, ground, soldering, pin labels and slot selection before enabling
   the reviewed I2S profile. Build/confirm-flash that separate configuration.
   In Desktop use live source 0, start recording, capture a short genuine raw WAV,
   stop recording and acquisition, then reopen the raw session for waveform/PSD.
   Source 0 is disabled in the stable default G1 build.

## Engineering appendix — what each gate actually proves

| Gate | Required evidence | Does not prove |
| --- | --- | --- |
| G0 board identification | Actual PCB/module photos, selected connector, ROM ESP32-S3 / 16 MB flash, power review | USB enumeration alone is not firmware |
| G1A boot | Successful pinned build + explicit flash log + actual boot/UART log | Compilation does not establish boot/PSRAM health |
| G1B handshake | HELLO nonce, version, profiles/encoding/rate/frame capability checks and START/STOP | HELLO is compatibility, not cryptographic firmware authenticity |
| G1C deterministic USB | 480000 samples, 1875 normal frames, independent sample/hash/CRC/index/sequence/timestamp and final telemetry checks | Synthesized timestamps do not calibrate an acoustic sample clock |
| G2 microphone | Measured supply, clocks, real source-0 signal varying with physical sound, raw WAV and metadata | Clapping/voice is not low-frequency PCG validation |
| G3 acoustic characterization | Quiet baseline vs documented excitation, PSD, DC/RMS/clipping, uncertainty | No clinical conclusion or automatic model validity |

The acceptance report separates observed host data, firmware reports, estimates,
unavailable measurements and simulation. A real USB port is required to label a
pass physical. Every failure reason remains in the bundle. The required device
totals are generated=fully_queued=480000, dropped=0, frames=1875,
audio_bytes_queued=2002500, zero DMA/ring/timeout/disconnect/error fields, correct
session and normal/host stop reason. Partial writes are retries, not automatic
loss. CRC-valid data must also match the normative formula bit for bit.

Host receipt from START to last AUDIO is checked against a coarse 9..15-second
window on physical runs; first/last arrival rate is reported separately. This
detects obvious burst delivery, not ppm clock accuracy. Synthetic timestamp formula
and ordering are checked independently. USB AUDIO rate is nominally 200250 B/s,
excluding STATUS/control and transport overhead.

UART health logs expose application queue occupancy, internal heap and task stack
watermark once per second. Save the actual logs; the protocol does not invent new
wire fields for these values. The host report labels unavailable MCU measurements
accordingly. Check idle/task watchdog messages during repeated sessions. Report
CPU/queue behavior from actual runs, not a nominal 48000 constant.

Keep raw and processed files separate. The host routes decoded signed samples
through the existing DeviceRuntime/StreamManager → raw recorder/stateful DSP →
display decimation/Live Workspace → offline scientific analysis. Source provenance,
sample rate, recorder count and recording integrity must agree on reopening.
Use Butterworth/notch/Welch controls on derived data; preserve the raw file/hash.
MurmurMIL has not been validated for this sensor domain; do not run predictions
automatically or interpret connectivity tests clinically.

## Advanced commands and failure recovery

Readiness without sending any serial bytes:
```powershell
.\.venv\Scripts\python.exe tools/hardware/bringup.py
.\.venv\Scripts\python.exe tools/hardware/preflight.py --json --output experiments/hardware/preflight.json
```

Explicit read-only ROM identity or application HELLO, after inspecting the port:
```powershell
.\.venv\Scripts\python.exe tools/hardware/bringup.py identify --port COM_ROM_VERIFIED
.\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port COM_DATA_VERIFIED
```
ROM identity queries may reset the board into download mode but do not write
firmware. The wizard never erases flash or writes eFuses/security settings.

| Failure | Next useful action |
| --- | --- |
| No enumeration | Change known data cable/USB port; inspect correct connector in Device Manager, no damaged-board claim |
| Busy/access denied | Close only the application/monitor owning that exact port; no global process kill |
| Build failed | Read firmware/build/release-build-output.txt; do not flash |
| Flash failed | Preserve first-flash.txt; hold verified BOOT, press/release RESET, release BOOT; rediscover ROM port, identify again |
| No application CDC after boot | Watch for re-enumeration, inspect UART boot/PHY selection and power; use ROM recovery route |
| HELLO timeout / nonce/version error | Check selected CDC, firmware version, DTR and connector; save Flight Recorder; reconnect without simulator fallback |
| CRC/gap/duplicate/value mismatch | Save failure bundle and first index/expected/actual; inspect scheduling, queues, cable and power |
| Missing STOP_ACK | INCOMPLETE/FAIL; preserve trailing data and logs, never fabricate final counters |
| Bandwidth insufficient | Measure queues and task health; do not reduce 48 kHz or change the canonical profile |
| Unplug/suspend/device restart | Preserve interrupted recording; rescan, HELLO and start a fresh session |
| Microphone zeros | Check 3.3 V/GND, clocks, SD, L/R slot and 24-bit alignment before claiming usable acquisition |
| Noise/clipping | Keep original WAV; report an engineering hypothesis and uncertainty, not a medical finding |

## Evidence checklist before any green physical gate

- [ ] Actual board/connector/power identity recorded by Ege and Kaan.
- [ ] Pinned build manifest, source commit/dirty state, config/lock and binary hashes.
- [ ] Explicit flash authorization and actual flash/boot logs; no assumed PSRAM test.
- [ ] Physical-only HELLO/START/AUDIO/STOP run; no fallback adapter.
- [ ] All mandatory G1 report gates PASS, exact counts, zero unexplained faults.
- [ ] Export contains session/board/build/enumeration, protocol, integrity,
      telemetry, timing, Flight Recorder JSONL, advisor-readable report and hashes.
- [ ] Repeat run/reconnect creates fresh session; preserve failure evidence too.
- [ ] G2 wiring/clock/signal and G3 acoustic evidence evaluated separately.
