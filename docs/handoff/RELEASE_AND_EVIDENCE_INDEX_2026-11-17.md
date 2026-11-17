# Release, Binary Hashes & Evidence Index (As-Of 2026-11-17)

- **Repository:** `https://github.com/egecagintepe/ausculta-forge`
- **Base Commit Before Handoff Staging:** `319fcc59be0177bf45d5266025344d31e4e9a9c2` (`main`)
- **Pinned Toolchain:** ESP-IDF `v5.5.1` | Compiler `xtensa-esp-elf-gcc 14.2.0` | `esp_tinyusb 2.2.0` | `tinyusb 0.19.0~3` | Python `3.11.9` | Node `v24.15.0` | WinLibs MinGW GCC `16.2.0`

---

## 1. Staged Firmware Releases & SHA-256 Verification Inventory

| Package Path | Status | `source_modes` | File (`flash` offset) | Size | SHA-256 |
| :--- | :--- | :---: | :--- | :---: | :--- |
| [`firmware/g1_rollback_backup/`](../../firmware/g1_rollback_backup/README.md) | `COMPILED_BUT_NOT_FLASHED` *(Immutable 2026-10-23 Rollback)* | `[1]` | `auscultaforge_g1.bin` (`0x10000`)<br>`bootloader/bootloader.bin` (`0x0`)<br>`partition_table/partition-table.bin` (`0x8000`)<br>`sdkconfig` | 268,112 B<br>21,056 B<br>3,072 B | `9ebe95852d92959bf581fbe7fe6da7df8dc3bc745075428e8f57a3726a5ce0b1`<br>`2796dbba8a3e3dca0bc6588985caaadb234b3c12a721e15a6500d4798ea9807d`<br>`73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501`<br>`5c137ae2416c5e356a5c6e0488c5b41ae9a194b77a9f4f0bd233054bd364332b` |
| [`firmware/releases/g1_release_20261117/`](../../firmware/releases/g1_release_20261117/README.md) | `COMPILED_BUT_NOT_FLASHED` *(Verified 2026-11-17)* | `[1]` | `auscultaforge_g1.bin` (`0x10000`)<br>`bootloader/bootloader.bin` (`0x0`)<br>`partition_table/partition-table.bin` (`0x8000`)<br>`sdkconfig` | 268,112 B<br>21,056 B<br>3,072 B | `bd48630874e531f2d761ed0e39f27c90d5d7271223a6566acbf1bc620b919837`<br>`52db976aa3d20ab4c1f112832f1c74fa5c591fc1d887c6498a236aaa4f6d5dfd`<br>`73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501`<br>`5c137ae2416c5e356a5c6e0488c5b41ae9a194b77a9f4f0bd233054bd364332b` |
| [`firmware/releases/g2_candidate_20261117/`](../../firmware/releases/g2_candidate_20261117/README.md) | **`PREPARED_NOT_AUTHORIZED_FOR_FLASH`** *(Provisional BCLK=4, WS=5, DIN=6, L/R=GND)* | `[1, 0]` | `auscultaforge_g1.bin` (`0x10000`)<br>`bootloader/bootloader.bin` (`0x0`)<br>`partition_table/partition-table.bin` (`0x8000`)<br>`sdkconfig` | 294,880 B<br>21,056 B<br>3,072 B | `22af47eef7a4a51765254a1144627bf44b39c53dfab8b8ce13f18a10ebd67dbb`<br>`28e9a026860d4b75c1573dacdf89570770186435983156b3347a107925e6dbe0`<br>`73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501`<br>`fc56de3b431da13d219b1a1a99acc783834760ab8fb59283eb78ab0a60f1ef71` |
| `firmware/build/g2_compile_check/` | **DO_NOT_FLASH** *(Local compile cache only; blocked by `bringup.py`)* | `[1, 0]` | — | 294,880 B | Matches staged candidate source build; never distribute directly without release manifest. |

> [!NOTE]
> **`dependencies.lock` SHA-256:** `618443a9d9b1ffd85d4920b41211b6712d1c16887c7c93ed807e9127acbfb330`
>
> **Firmware Session Limit Disclosure:** [`firmware/components/g1/include/g1.h`](../../firmware/components/g1/include/g1.h#L6) sets `G1_TARGET_SAMPLES = 480000U` (`10.0 s` at `48 kHz`), and `g1_tick()` enforces a `40 s` hard session timeout (`firmware/components/g1/g1.c:192`). No 30-minute physical hardware endurance run has been executed.

---

## 2. Software, Build & Hardware Verification Matrix

### A. Verified Automated Suites (Executed 2026-11-17)

| Suite / Command | Result | Exact Counts / Notes |
| :--- | :---: | :--- |
| `.\.venv\Scripts\python.exe -m pytest firmware/tests -v` | **PASS** | **16 passed** (`13.41 s`) — compiles C (`bridge.c`, `g1.c`, `acquisition.c`, `packet_framing.c`) via WinLibs GCC `16.2.0` into `g1.dll`. Covers G1 FSM, I²S 24-in-32 sign extension, overflow counters, stop races. |
| `.\.venv\Scripts\python.exe -m pytest tools/protocol_lab/python -v` | **PASS** | **59 passed, 1 skipped** (`9.81 s`) — skip is `test_c_executable_to_python_decoder_parity` (`g1_sim_runner.exe` not precompiled in `tools/protocol_lab/c/`). |
| `.\.venv\Scripts\python.exe -m pytest software/tests -q` | **PASS** | **587 passed, 4 skipped** (`63.87 s`) — skips are optional gitignored datasets (`data/external`, `AUSCULTA_PCG_MANIFEST`) and `golden_generator.exe`. Includes `authorize-g2` gate tests, `GITHUB_DOWNLOAD_ZIP` fallback tests, and controlled artifact benchmark (`100%` / `5/5`). |
| `Push-Location software/frontend; npm.cmd run lint; npm.cmd test; npm.cmd run build; Pop-Location` | **PASS** | TypeScript `tsc --noEmit`: `0` errors; **9 `tsx` test suites passed**; `vite build` succeeded (`3.93 s`). |
| ESP-IDF v5.5.1 G1 Release Build (`C:\pcg_starter`) | **PASS** | Exit code `0`, `268,112 B` app binary, manifest verified. |
| ESP-IDF v5.5.1 Separate G2 Compile-Check Build | **PASS** | Exit code `0` (`-B build/g2_compile_check`), `firmware/sdkconfig` cleanly restored to G1 afterward. |
| `.\scripts\handoff\windows_preflight.ps1` | **PASS** | Verified Python `3.11.9` `.venv`, `esptool 5.6.0`, `Node v24.15.0`, WinLibs GCC `16.2.0`, `GIT_CLONE`/`GITHUB_DOWNLOAD_ZIP` detection, and SHA-256 of all 3 manifests. |
| [`pack_wednesday_results.ps1`](../../scripts/handoff/pack_wednesday_results.ps1) / [`pack_lab_return.py`](../../tools/hardware/pack_lab_return.py) | **PASS** | Dry-run smoke check packaged `120` files (`3,022,607` bytes, SHA-256 `a7b545b8bd997f86f69b2c93c30a72d59d5685792ae6b442d6c5dd57cf89330a`) read-only without Git. |

### B. Historical vs. Today's Physical Hardware Status

| Hardware Event | Date | Status | Recorded Outcome & Boundary |
| :--- | :--- | :---: | :--- |
| **Today's Physical USB / ESP32 Hardware Test** | 2026-11-17 | **`NOT_EXECUTED`** | Board physically unplugged during Tuesday handoff preparation; zero flash/reset/ROM operations performed. |
| **Previous Session COM10 Physical G1 Bringup & Device Center Flow** *(Historical Reference)* | 2026-11-16 | `PASS (Historical)` | Tracked summary: [`laptop_20261116_g1_and_wav_summary.json`](../../firmware/evidence/laptop_20261116_g1_and_wav_summary.json). `ESP32-S3 (UID: 0xb1aa7cc4)`, `COM10` (`VID:303A PID:4001`). Bringup G1: `480,000` samples, `1,875` frames, `0` drops. Device Center WAV: `194,304` samples, `4.048 s`, `48 kHz` `physical_deterministic_g1`. |
| **Week-6 Physical G1 Sprint** *(Historical Reference)* | 2026-10-26 | `PASS (Historical)` | Recorded in [`W06_C_spectrogram-recording-metadata.md`](../sdp/week-06/submissions/module-c-ege/W06_C_spectrogram-recording-metadata.md) and [`WEEK6_SPRINT_REPORT.md`](../engineering/release/WEEK6_SPRINT_REPORT.md). |
| **Physical INMP441 G2 Acquisition** | Pending | **`NOT_EXECUTED`** | INMP441 not yet soldered/wired; scheduled for Wednesday 2026-11-18 by Kaan & Ozan after H0 checks. |
| **Physical Acoustic Phantom G3 (H1/Coherence/S1-S2/30-min)** | Pending | **`NOT_EXECUTED`** | Phantom & PAM8403 assembly not yet completed physically. |

---

## 3. Reproducing Builds & Known Environment Notes

1. **Path Space / Turkish Character Guard (`C:\pcg_starter`):**
   - ESP-IDF's Windows `ccache` and PE wrapper (`idf.py.exe`) fail on spaces/non-ASCII paths like `C:\Users\Ege Çağın\...`. Always build firmware from an ASCII, space-free path (`C:\pcg_starter` NTFS junction) with `--no-ccache`.
   - On Ege's laptop, `C:\esp\.espressif\python_env\idf5.5_py3.13_env` uses Python `3.13.2` whereas `.venv` uses `3.11.9`. Prepend `C:\esp\.espressif\python_env\idf5.5_py3.13_env\Scripts` to `$env:Path` before dot-sourcing `C:\esp\esp-idf-v5.5.1\export.ps1`, OR use the ESP-IDF v5.5.1 PowerShell Desktop shortcut.
2. **SDK `ldgen.py` Local Patch Audit (Technical Debt Notice):**
   - File: `C:\esp\esp-idf-v5.5.1\tools\ldgen\ldgen.py:131` (explains `ESP-IDF v5.5.1-dirty`).
   - Change present: `.decode(errors='replace')` on `objdump -h` subprocess output to prevent `UnicodeDecodeError` when `LC_ALL='C'` runs under Turkish Windows codepage with non-ASCII paths.
   - Clean team solution: Clone/run via `C:\pcg_starter` (pure ASCII path) so teammates do **NOT** need to patch their SDK.
3. **Post-Push GitHub Verification URLs (Check After Ege Approves Commit & Push):**
   - `https://github.com/egecagintepe/ausculta-forge/blob/main/docs/handoff/README.md`
   - `https://github.com/egecagintepe/ausculta-forge/blob/main/docs/handoff/START_HERE_2026-11-18.md`
   - `https://github.com/egecagintepe/ausculta-forge/blob/main/docs/handoff/AGENT_WEDNESDAY_2026-11-18.md`
   - `https://github.com/egecagintepe/ausculta-forge/blob/main/docs/handoff/HARDWARE_GATES_AND_ROLLBACK.md`
   - `https://github.com/egecagintepe/ausculta-forge/blob/main/docs/handoff/RELEASE_AND_EVIDENCE_INDEX_2026-11-17.md`
   - `https://github.com/egecagintepe/ausculta-forge/blob/main/docs/sdp/PROGRESS_ASOF_2026-11-17.md`
