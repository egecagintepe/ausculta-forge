# START HERE — AuscultaForge 25 November 2026 Lab Session

**Primary Goal (P0):** Execute the Week 9 Physical Phantom Feasibility Gate (`40058_AV.wav` played through PAM8403 $\rightarrow$ exciter $\rightarrow$ transfer plate $\rightarrow$ fully cured phantom $\rightarrow$ chestpiece $\rightarrow$ sealed cavity $\rightarrow$ INMP441 $\rightarrow$ ESP32-S3 $\rightarrow$ USB CDC $\rightarrow$ host).

---

## 1. Before Powering Anything (5-Minute Safety Gate)
1. **RTV-2 Cure Check (Kaan):** Inspect the 23 Nov Borcam silicone. If tacky/uncured, **DO NOT USE IT** (not even with a pad on top). Switch to a separate, fully cured compliant elastomer/pad and note the substitution.
2. **Mechanical Chain (Kaan):** Exciter $\rightarrow$ transfer plate $\rightarrow$ cured phantom $\rightarrow$ chestpiece $\rightarrow$ sealed cavity $\rightarrow$ INMP441. **Never** place the MEMS mic directly on silicone or block its port.
3. **Electrical Safety (Ozan):**
   - Independent regulated **5 V** for PAM8403 (never connect `OUT+` or `OUT-` to `GND` — BTL output!).
   - Verify ESP32-S3 **3.3 V** rail ($3.14\text{--}3.46\text{ V}$) with multimeter before starting.
   - Start PAM8403 potentiometer at **minimum**.

---

## 2. Single Launch Command (Ege — Lab Laptop)
```powershell
cd c:\Dev\Antigravity\bitirme\ausculta-forge
.\tools\hardware\run_lab_phantom_workflow.ps1
```
*(Runs port discovery $\rightarrow$ 10s quiet baseline $\rightarrow$ -18 dBFS calibration tone $\rightarrow$ explicit operator routing confirmation $\rightarrow$ synchronized PCG phantom trial $\rightarrow$ ZIP evidence packaging.)*

---

## 3. Emergency Recovery & Rollback
- **Backend / UI Restart (if needed):**
  - Backend: `.\.venv\Scripts\python.exe -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000`
  - Frontend: `cd software/frontend; npm run dev`
- **P0 Failure Recovery:**
  - Clipping (`> 0.05%`): Turn down PAM8403 pot immediately.
  - Low SNR (`< 12 dB`): Check chestpiece acoustic seal and exciter contact; increase pot slightly.
  - USB/COM Error: Close Arduino/PuTTY/WebSerial tabs; replug USB-C data cable; re-run `--discover-ports`.
- **Firmware Policy:** Do **NOT** flash the ESP32-S3 before P0. Known-good G2 binaries are preserved in `firmware/releases/g2_candidate_20261117/`.

---

## 4. Key Documents
- Operator Run Sheet (TR): [`LAB_RUN_SHEET_2026-11-25.md`](LAB_RUN_SHEET_2026-11-25.md)
- Supervisor Brief (EN): [`SUPERVISOR_STATUS_BRIEF_2026-11-25.md`](SUPERVISOR_STATUS_BRIEF_2026-11-25.md)
- Pre-Lab Acceptance Audit: [`FINAL_PRELAB_ACCEPTANCE_2026-11-24.md`](FINAL_PRELAB_ACCEPTANCE_2026-11-24.md)
