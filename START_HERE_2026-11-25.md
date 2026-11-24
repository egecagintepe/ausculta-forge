# START HERE — AuscultaForge 25 November 2026 Lab Session

**Primary Goal (P0):** Execute the Week 9 Physical Phantom Feasibility Gate: Play known CirCor recording `40058_AV.wav` through PC audio out $\rightarrow$ PAM8403 amplifier $\rightarrow$ 12 $\Omega$ exciter $\rightarrow$ 3D transfer plate $\rightarrow$ fully cured silicone phantom $\rightarrow$ dual-head stethoscope chestpiece $\rightarrow$ sealed acoustic cavity $\rightarrow$ INMP441 MEMS microphone $\rightarrow$ ESP32-S3 $\rightarrow$ USB CDC serial stream $\rightarrow$ PC host analyzer $\rightarrow$ timestamped, signed evidence ZIP.

---

## 1. Project & Git Baseline
- **Active Branch:** `feature/rev04-evidence-integration` (PR #36, clean against `origin/main`).
- **Single Entry Point:** `.\tools\hardware\run_lab_phantom_workflow.ps1`.
- **Reference Stimulus:** `data/raw/week6_real_pcg_20261026/circor/40058_AV.wav` (SHA-256: `108df8f77491a5706209aa5b467ed10ac43f2a0b847801fe666ba8146dcbf8e8`).
- **Pre-Verified Status:** 35/35 Python unit tests passing (anti-false-pass, content hash check, silence rejection, playback abort tracking, 256-sample drain). Frontend TypeScript build passing (`tsc --noEmit`, `vite build`).

---

## 2. Ozan's REV04 Technical & Procurement Plan
The engineering baseline incorporates Ozan's finalized Week 09 REV04 deliverables:
- **Technical Specification:** `W09_B_system-design-technical-specification_REV04_2026-11-20.docx` (38 pages, REV04-QA).
- **Procurement BOM & Test Matrix:** `W09_B_procurement-bom-test_REV04_2026-11-20.xlsx` (17 sheets, revision 04-QA).
  - Plaket structure: Explicitly separated B-01a (main acquisition board) and B-01b (power/filter board); 3 prototype boards in total.
  - Exciter impedance: 12 $\Omega$ impedance acoustic exciter.
  - Overall budget: 4,246.21 TL with confirmed order status (`Satın_Alma` and `Test_Matrisi!I14`).
- **QA Verification Record:** `AuscultaForge_W09_REV04_QA_2026-11-20.md`.

---

## 3. Team Roles & Responsibilities

| Member | Primary Domain | Physical & Software Responsibilities |
| :--- | :--- | :--- |
| **Kaan** | Mechanics & Acoustic Phantom | • Inspect RTV-2 silicone cure state before powering.<br>• If tacky, apply compliant elastomer backup.<br>• Secure transfer plate, phantom, and chestpiece with airtight acoustic seal.<br>• Ensure INMP441 sound port is never blocked or contaminated with silicone. |
| **Ozan** | Electrical & Instrumentation | • Connect independent regulated **5 V** DC power to PAM8403.<br>• **CRITICAL:** PAM8403 uses Bridge-Tied Load (BTL) output — **NEVER** connect `OUT+` or `OUT-` to `GND`.<br>• Measure ESP32-S3 3.3V rail with DMM ($3.14\text{--}3.46\text{ V}$) before recording.<br>• Start PAM8403 gain potentiometer at minimum and adjust to avoid clipping ($< 0.05\%$). |
| **Ege** | Host Orchestration & Software | • Run single launch command on lab laptop.<br>• Manage automated USB CDC port discovery (zero manual typing).<br>• Verify SHA-256 data integrity for quiet baseline and captured PCG.<br>• Inspect automated SNR ($\ge 12\text{ dB}$) and S1/S2 acoustic metrics.<br>• Package signed evidence ZIP for supervisor submission. |

---

## 4. Before Powering Anything (5-Minute Safety Gate)
1. **RTV-2 Cure Check (Kaan):** Inspect the 23 Nov Borcam silicone specimen. If tacky or uncured, **DO NOT USE IT** (not even with a film on top). Switch to the cured backup elastomer and record the substitution.
2. **Mechanical Acoustic Coupling (Kaan):** Exciter $\rightarrow$ plate $\rightarrow$ phantom $\rightarrow$ chestpiece $\rightarrow$ sealed cavity $\rightarrow$ INMP441. Keep microphone sound port open and dry.
3. **Electrical Safety & BTL Isolation (Ozan):**
   - Independent regulated 5V power for PAM8403.
   - Multimeter probe: ESP32-S3 3.3V rail must be $3.30 \pm 0.16\text{ V}$.
   - PAM8403 volume knob turned to minimum.
4. **Firmware Policy:** Do **NOT** reflash ESP32-S3 firmware before P0. The known-good G2 binary is already loaded.

---

## 5. Single Launch Command (Ege — Lab Laptop)
```powershell
# Pre-Lab Verification (runs offline, no hardware or sound required):
.\tools\hardware\run_lab_phantom_workflow.ps1 -SetupOnly

# Software Simulation Smoke Check:
.\tools\hardware\run_lab_phantom_workflow.ps1 -Simulate

# LIVE Physical Phantom Experiment (when hardware is connected):
.\tools\hardware\run_lab_phantom_workflow.ps1
```
The automated script executes:
1. Dynamic ESP32-S3 USB CDC discovery (`VID 0x303A`).
2. 10-second quiet baseline recording & SHA-256 verification (operator ensures room silence).
3. Low-volume calibration tone (-18 dBFS, 120 Hz) playback.
4. Operator physical confirmation (power, BTL isolation, exciter vibration).
5. Synchronized `40058_AV.wav` playback and live INMP441 acquisition.
6. Automated acceptance analysis (clipping $<0.05\%$, SNR $\ge 12\text{ dB}$, S1/S2 energy ratio).
7. Evidence packaging into `data/reports/lab_returns/AuscultaForge_Return_*.zip`.

---

## 6. Open Physical Checks & Acceptance Thresholds
- [ ] Silicone specimen fully cured (Shore A 15-25) OR certified elastomer substitute used.
- [ ] PAM8403 power isolated; BTL terminals completely floating with respect to ground.
- [ ] ESP32-S3 3.3V rail measured: $3.14\text{--}3.46\text{ V}$.
- [ ] Background noise floor: $< 0.005\text{ FS RMS}$ during quiet baseline.
- [ ] Live capture clipping: $< 0.05\%$ samples above $0.98\text{ FS}$.
- [ ] Acoustic SNR: $\ge 12.0\text{ dB}$ relative to quiet baseline.
- [ ] S1/S2 low-frequency band energy: $\ge 60.0\%$ in $20\text{--}200\text{ Hz}$.

---

## 7. Key Documents & Runbooks
- Operator Run Sheet (TR): [`docs/engineering/hardware/LAB_RUN_SHEET_2026-11-25.md`](docs/engineering/hardware/LAB_RUN_SHEET_2026-11-25.md)
- Supervisor Status Brief (EN): [`docs/engineering/hardware/SUPERVISOR_STATUS_BRIEF_2026-11-25.md`](docs/engineering/hardware/SUPERVISOR_STATUS_BRIEF_2026-11-25.md)
- Final Pre-Lab Acceptance Audit: [`docs/engineering/hardware/FINAL_PRELAB_ACCEPTANCE_2026-11-24.md`](docs/engineering/hardware/FINAL_PRELAB_ACCEPTANCE_2026-11-24.md)
- Measurement Plan: [`docs/engineering/hardware/W10_LAB_MEASUREMENT_PLAN_2026-11-25.md`](docs/engineering/hardware/W10_LAB_MEASUREMENT_PLAN_2026-11-25.md)
- Phantom Fabrication Log: [`docs/engineering/hardware/PHANTOM_FABRICATION_LOG_2026-11-23.md`](docs/engineering/hardware/PHANTOM_FABRICATION_LOG_2026-11-23.md)
