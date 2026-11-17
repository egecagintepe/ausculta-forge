# AuscultaForge — Agent Execution Specification (Wednesday, 2026-11-18 Lab Handoff)

This document is an **independent, system-agnostic operational instruction** for the Antigravity coding agent assisting **Kaan** (Module A — Hardware & Measurement) and **Ozan** (Module B — Embedded & CLI Operation) on Wednesday, 2026-11-18, while **Ege** (Module C / Software Architect) is unavailable.

Read [README.md](README.md), [HARDWARE_GATES_AND_ROLLBACK.md](HARDWARE_GATES_AND_ROLLBACK.md), [START_HERE_2026-11-18.md](START_HERE_2026-11-18.md), and [RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md](RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md) before running any hardware command.

---

## 0. Non-Negotiable Safety & Integrity Rules

1. **Git-Free Operation & Zero Personal Credentials:** Assume Kaan and Ozan may have extracted the repository from a **GitHub Download ZIP** without `git` installed and will **NOT** push to GitHub. NEVER require GitHub authentication, passwords, or Personal Access Tokens from Ege, Kaan, or Ozan. At the end of the session, package all evidence into a single local return `.zip` file using `scripts/handoff/pack_wednesday_results.ps1`.
2. **Zero Unverified Hardware Commands:**
   - NEVER flash, erase flash, toggle `BOOT/RESET`, or run ROM `esptool` write commands without explicit, step-by-step confirmation from the human operators.
   - NEVER use or copy [`firmware/build/g2_compile_check/`](../../firmware/build/g2_compile_check/) for flashing. `bringup.py` will block it.
   - NEVER flash [`firmware/releases/g2_candidate_20261117/`](../../firmware/releases/g2_candidate_20261117/firmware_build_manifest.json) until Phase 2 (Physical Inspection & Multimeter) passes AND `bringup.py authorize-g2` has been explicitly executed by the operators.
   - NEVER touch [`firmware/g1_rollback_backup/`](../../firmware/g1_rollback_backup/) files (read-only rollback asset).
3. **Truthfulness & Provenance:**
   - Never hardcode `COM10` or any prior port number from Ege's laptop; discover ports fresh via USB plug/unplug observation (`python -m serial.tools.list_ports`).
   - Enforce single-owner serial port discipline: close Device Center / stop `uvicorn` before running `bringup.py`, and close CLI before opening Device Center.
   - Never synthesize fake microphone audio when `source_mode=0` fails or reads all zeros (`constant_zero: true`). Digital silence means investigate VDD, GND, slot L/R, WS/BCLK/SD, or soldering.
   - Never record human/patient heart sounds; use quiet room ambient + controlled speaker/clap test excitation only. Keep PAM8403 out of G1/G2 unless separately wired under BTL safety rules.
   - Do not claim 30-minute physical endurance `PASS` from 10-second (`480,000` sample) bounded runs (`G1_TARGET_SAMPLES = 480000U`).
4. **Stop Immediately On Any Fault:** If any rail reads outside `[3.15, 3.45] V`, a short circuit is found, G1 fails, or unexpected heat/reset occurs, **STOP**, ask the operator to unplug USB, preserve all logs, and follow rollback rules if needed.

---

## Phase 1 — Folder Verification & Environment Preflight (Supports Download ZIP Without Git)

1. Verify the opened folder contains `docs/handoff/`, `software/`, `firmware/releases/`, and `tools/hardware/`. Check whether the folder path contains spaces or Turkish characters — if planning to run ESP-IDF builds (Case B), ensure work runs via an ASCII space-free path such as `C:\pcg_starter` (`windows_setup.ps1` offers to create an NTFS junction cleanly). Do **NOT** fail if `.git` is absent (GitHub Download ZIP mode is fully supported). If `.git` IS present and `git` is installed, inspect `git status` and `git rev-parse HEAD`.
2. Run setup if `.venv` or `node_modules` is missing, then run passive preflight (`-Json -Output`):
   ```powershell
   .\scripts\handoff\windows_setup.ps1
   .\scripts\handoff\windows_preflight.ps1 -Json -Output experiments/hardware/preflight_20261118.json
   ```
3. Verify all three manifests in the preflight output show `"hashes_verified": true` (note: preflight uses `firmware/releases/g1_release_20261117/` and `firmware/releases/g2_candidate_20261117/` transparently without requiring a local `firmware/build/` directory):
   - `firmware/g1_rollback_backup/firmware_build_manifest.json` (`COMPILED_BUT_NOT_FLASHED`)
   - `firmware/releases/g1_release_20261117/firmware_build_manifest.json` (`COMPILED_BUT_NOT_FLASHED`)
   - `firmware/releases/g2_candidate_20261117/firmware_build_manifest.json` (`PREPARED_NOT_AUTHORIZED_FOR_FLASH`)
4. Inspect [`firmware/main/Kconfig.projbuild`](../../firmware/main/Kconfig.projbuild), [`firmware/main/i2s_source.c`](../../firmware/main/i2s_source.c), and [`tools/hardware/bringup.py`](../../tools/hardware/bringup.py) so you understand the pin checks (`safe_pin()`), slot selection, and G2 authorization workflow.

---

## Phase 2 — Consolidated One-Shot Request for Operator Photos & Measurements (Gate H0)

Ask Kaan and Ozan **in a single, clear message** for all required physical inputs before proceeding to wiring/G2:

> **Copy-paste / present this checklist once to Kaan & Ozan:**
> 1. **Photos (upload/attach now):**
>    - Top and bottom of the **ESP32-S3 board** (`YD-ESP32-23` / `N16R8`) with all GPIO header silkscreen labels legible.
>    - Top and bottom of the **INMP441 breakout** showing all 6 header solder joints (`VDD`, `GND`, `SCK`, `WS`, `SD`, `L/R`) and confirming the bottom acoustic port hole is completely unobstructed.
> 2. **USB Port & Cable Identification (with microphone DISCONNECTED):**
>    - Confirm only **ONE** USB data cable is plugged into the board (`USB` native OTG port vs `UART` bridge port).
>    - Run `.\.venv\Scripts\python.exe -m serial.tools.list_ports` before and after plugging in the board, and tell me the newly appeared Espressif COM port name (e.g., `COM7`).
> 3. **Multimeter Measurement Table (record values & multimeter model):**
>    - **ESP32 `3V3` – `GND` voltage** (measured while powered via single USB cable, mic **unplugged**): `_____ V` (Multimeter ID: `_____`).
>    - *(After unplugging USB)* **Power-off resistance / continuity checks:**
>      - INMP441 `VDD` – `GND` (no short): `_____ Ohm / Open`
>      - Continuity for each wired line: `VDD->3V3`, `GND->GND`, `SCK->GPIO?`, `WS->GPIO?`, `SD->GPIO?`, `L/R->GND` (`LEFT slot`).
>    - **Confirm exact GPIO numbers** matching your actual PCB silkscreen (provisional baseline is `BCLK=4, WS=5, DIN=6, L/R=GND`).

Do **NOT** approve G2 wiring or flashing until the photos clearly show clean solder joints, no `GPIO 19/20/26..37/0/3/45/46/43/44` conflicts, unobstructed bottom acoustic port, and measured VDD within `3.15 .. 3.45 V`.

---

## Phase 3 — Verify Existing G1 on Team Laptop (Gate G1)

With the microphone still disconnected (or safe if not wired yet) and only **one** owner opening `<COM_CDC>`:

1. Run HELLO & G1 regression against the staged G1 manifest (do **NOT** flash yet — test the firmware already on the chip first):
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port <COM_CDC>
   .\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port <COM_CDC> --manifest firmware/releases/g1_release_20261117/firmware_build_manifest.json
   ```
   *(If the chip firmware matches `v1.1.0`, this executes without writing flash. Note that `physical_g1` checks `reported == firmware_version`; if the board has an earlier G1 or fails HELLO, inspect the error before touching flash.)*
2. Confirm output prints `PHYSICAL_G1_PASSED` and saves a new bundle under `experiments/hardware/<timestamp>_<id>/`. Inspect `acceptance_report.md` and `g1_protocol_summary.json` to confirm `480000` samples, `0` dropped samples, `0` CRC errors.

---

## Phase 4 — G2 Physical Authorization, Flash & G1 Regression Check

Proceed **only** after Phase 2 (photos + 3.3V + continuity verified) AND Phase 3 (`PHYSICAL_G1_PASSED`):

1. Ensure USB is **unplugged** while connecting wires, then verify power-off `VDD–GND` has no short circuit, then plug in the single USB cable.
2. **Branch on confirmed pins (`BCLK`, `WS`, `DIN`, `L/R` slot):**
   - **Case A — Confirmed pins match `BCLK=4, WS=5, DIN=6, slot=left`:**
     Run the interactive physical attestation gate on the staged G2 candidate (requires operator typed confirmation):
     ```powershell
     .\.venv\Scripts\python.exe tools/hardware/bringup.py authorize-g2 --manifest firmware/releases/g2_candidate_20261117/firmware_build_manifest.json --bclk 4 --ws 5 --din 6 --slot left --vdd-volts <MEASURED_VDD> --operator "<Kaan & Ozan>" --multimeter "<MULTIMETER_ID>"
     ```
     Select manifest path: `firmware/releases/g2_candidate_20261117/firmware_build_manifest.json`.
   - **Case B — Operators had to change GPIOs (e.g. due to PCB header layout) OR choose to build locally from source:**
     Verify ESP-IDF v5.5.1 is active (via `C:\pcg_starter` ASCII junction), set confirmed pins in `idf.py menuconfig` under `AuscultaForge board profile`, run `.\.venv\Scripts\python.exe tools/hardware/bringup.py build`, verify `source_modes: [1, 0]` in `firmware/build/release/firmware_build_manifest.json`, and use that manifest for flashing. *(Remember to save a backup of the G1 `sdkconfig` and never overwrite `firmware/g1_rollback_backup/`.)*
3. **Human-Gated ROM Flash:**
   Instruct Kaan/Ozan to put ESP32-S3 into ROM Bootloader mode (`BOOT` hold $\to$ `RESET` press-release $\to$ `BOOT` release), find `<COM_ROM>` via `list_ports`, and run:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py flash --port <COM_ROM> --manifest <AUTHORIZED_G2_MANIFEST>
   ```
   Wait for the human operator to verify chip MAC + hashes and type `FLASH <COM_ROM>`.
4. **Post-Flash Reboot & G1 Fallback Regression:**
   Press `RESET` on the board, rescan COM ports to get `<COM_CDC>` (port number may change after switching from ROM to CDC), verify `hello`, and verify deterministic `source_mode=1` G1 STILL passes after enabling I²S:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py hello --port <COM_CDC>
   .\.venv\Scripts\python.exe tools/hardware/bringup.py g1 --port <COM_CDC> --manifest <AUTHORIZED_G2_MANIFEST>
   ```

---

## Phase 5 — Live INMP441 (`source_mode=0`) Acquisition & Qualification (Gate G2)

1. Confirm CLI is completely finished (COM port is closed). Launch desktop app:
   ```powershell
   .\scripts\dev.ps1
   ```
2. Open `http://127.0.0.1:3000` in browser $\to$ **Device Center**:
   - Click `Scan USB` $\to$ select `<COM_CDC>` $\to$ click `Connect & HELLO`.
   - Switch Mode to **`Live microphone (Mode 0)`**.
   - Click `Start Acquisition`. Immediately switch to **Live Workspace** and click **Record** for **10 seconds** in **quiet room background** (`g2-quiet`), then click **Stop** (note the saved `session_id`).
   - Run a second fresh **10-second** session (`g2-stimulus`) while producing a clear controlled sound near the INMP441 acoustic port (e.g., hand clap at 20 cm or phone 100 Hz tone).
   - Disconnect cleanly in Device Center before touching CLI tools.
3. Run offline mathematical qualification on both recorded WAVs:
   ```powershell
   .\.venv\Scripts\python.exe tools/hardware/bringup.py qualify --session experiments/sessions/<QUIET_SESSION_ID> --output experiments/hardware/g2-quiet-qualify.json
   .\.venv\Scripts\python.exe tools/hardware/bringup.py qualify --session experiments/sessions/<STIM_SESSION_ID> --output experiments/hardware/g2-stimulus-qualify.json
   ```
4. **Acceptance Audit (strictly compare outputs):**
   - Check `constant_zero == false` and `constant_signal == false` on both sessions.
   - Check `rms_fs` and `peak_fs` of `g2-stimulus-qualify.json` are clearly higher than `g2-quiet-qualify.json`.
   - Check `saturation_fraction == 0.0` (no clipping) or adjust speaker/mic distance if clipping occurs.
   - Check Device Center telemetry / Flight Recorder logs for `0` DMA overflows and `0` ring overflows.
   - **Failure / Rollback Rule:** If `constant_zero == true` after checking wiring/slot/3.3V, or if `source_mode=0` crashes USB/ESP32, record the failure JSON/logs in `experiments/hardware/`, stop testing, and if a clean G1 state is required execute the rollback command from [HARDWARE_GATES_AND_ROLLBACK.md](HARDWARE_GATES_AND_ROLLBACK.md#6-zorunlu-g1-geri-dönüş-rollback-prosedürü).

---

## Phase 6 — Evidence Recording & Verified Return ZIP Packaging (No Git Required)

1. Copy any operator PCB/breakout photos into `experiments/hardware/photos/` (or keep their folder path ready for `--extra-dir`).
2. Fill in ONLY genuinely observed measurements into the blank Wednesday 2026-11-18 measurement table in [`docs/sdp/SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md`](../sdp/SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md) and [`docs/sdp/week-09/`](../sdp/week-09/) (`module-a-kaan` / `module-b-ozan`) — include multimeter ID, measured `3V3`, photo filenames, G1 bundle directory, `qualify` JSON outputs, and `session_id`s. Leave failed or unrun items honestly marked `FAIL` / `NOT_EXECUTED`.
3. Run the automated verification suite to confirm software integrity remains intact:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest software/tests tools/protocol_lab/python -q
   ```
4. Build the read-only, SHA-256 verified return ZIP archive for Ege (never alter any WAV or raw JSON file):
   ```powershell
   .\scripts\handoff\pack_wednesday_results.ps1 -Operator "Kaan_Ozan" -Notes "2026-11-18 Lab Integration Return"
   ```
   *(If photos are in a separate folder outside the repo, pass `-PhotosDir "<path_to_photos>"`.)*
5. Inspect the JSON output of `pack_lab_return.py` (`RETURN_PACKAGE_MANIFEST.json`) to confirm `gate_evidence_summary` lists the generated G1 bundle(s), `g2_physical_attestation.json` (if authorized), recorded sessions, and `qualify` reports. Present the final `.zip` file path, size, and SHA-256 to Kaan & Ozan so they can send it directly to Ege.
