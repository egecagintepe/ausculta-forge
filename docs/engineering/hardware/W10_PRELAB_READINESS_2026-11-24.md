# AuscultaForge — Week 10 Pre-Lab Readiness & Catch-Up Matrix

**Preparation Date:** 2026-11-24 (Tuesday)  
**Scheduled Physical Lab:** 2026-11-25 (Wednesday Morning)  
**Target Repository:** `egecagintepe/ausculta-forge`  
**Course:** EEE 495 / SDP4 — Smart Digital Stethoscope  
**Authors:** Ünal Kaan Öztürk (A), Özgür Ozan Yıldız (B), Ege Çağın Tepe (C)

---

## 1. Overall Readiness Verdict for 25 November 2026

### **VERDICT: GO (CONDITIONAL ON PHYSICAL PREREQUISITES)**

| Area | Readiness Status | Condition / Blocker to Resolve on Arrival |
|---|---|---|
| **Software & Test Pipeline** | **GO (VERIFIED)** | 20/20 regression tests passing (`pytest` suite clean). Zero coordinate double-shift, zero synthetic SNR. |
| **Firmware Integrity** | **GO (VERIFIED)** | Working G2 candidate (`g2_candidate_20261117`) preserved untouched on the physical board. |
| **Git & Document Provenance** | **GO (VERIFIED)** | PR #36 cleanly reconciled with `origin/main` (zero merge conflicts). Canonical 38-page DOCX & 17-sheet XLSX preserved. |
| **3.3V Power Rail Safety** | **CONDITIONAL** | Multimeter check must verify $3.14\text{ V} \le V_{\text{DD}} \le 3.46\text{ V}$ before INMP441 acquisition begins. |
| **Acoustic Silicone Phantom** | **CONDITIONAL** | Curing status of 23 Nov RTV-2 sample was tacky on 24 Nov morning. Fallback compliant pad must be inspected. |
| **Gain / Headroom Setup** | **CONDITIONAL** | PAM8403 pot must start at minimum and advance slowly to keep near-clipping $< 0.05\%$. |

---

## 2. Weeks 05–10 Comprehensive Catch-Up Matrix

| Week & Milestone | Planned Requirement (`SDP4_Digital_Stethoscope_Plan_EN.docx`) | Software Verification Status | Physical Hardware Evidence | Current Academic Status |
|---|---|---|---|---|
| **W05: Transducer Characterisation** | $20\text{--}500\text{ Hz}$ frequency response, transducer baseline. | **VERIFIED:** $H_1(f)$ Welch estimator and coherence $\gamma^2(f)$ implemented. | **BASELINE PROVEN:** 18 Nov G2 physical sessions (Runs 1–4, 1.92M samples). | **VERIFIED BASELINE / PHYSICAL SWEEP PENDING (25 Nov)** |
| **W06: SNR & Interference** | Active/quiet SNR, 50 Hz mains harmonic isolation. | **VERIFIED:** `evaluate_quiet_baseline_snr` requires physical quiet session; rejects sub-noise. | **BASELINE PROVEN:** Run 1 ($23.2\text{ dB}$ ratio), Run 4 ($8.0\text{ dB}$ ratio). | **VERIFIED BASELINE / PHYSICAL UPDATE PENDING (25 Nov)** |
| **W07: Acoustic Phantom** | Silicone tissue phantom, acoustic coupling. | **VERIFIED:** Specimen log and physical dimensions documented. | **PREPARED:** 12 cm Borcam RTV-2 sample poured 23 Nov (~10 mm depth); cure in progress. | **FABRICATED / PHYSICAL VERIFICATION PENDING (25 Nov)** |
| **W08: Continuous Streaming** | Packet drop accounting, 30-minute endurance stability. | **VERIFIED:** Incremental streaming writer & accounting self-test passed (0 drops, 0 gaps). | **NOT_EXECUTED:** Preserved G2 release; endurance candidate isolated to avoid flash risk. | **SOFTWARE CANDIDATE READY / HARDWARE NOT_EXECUTED** |
| **W09: PCG Feasibility (P0 Gate)** | Physical CirCor playback through phantom into INMP441; S1/S2 matching. | **VERIFIED:** One-to-one envelope peak matcher with $0.0\text{ ms}$ delay contract. | **SCHEDULED (P0):** Primary objective for 25 November morning lab session. | **SOFTWARE PIPELINE TESTED / PHYSICAL P0 GATE ACTIVE** |
| **W10: Transducer Comparison** | Comparative transducer characterisation, digital filter presets. | **VERIFIED:** 4th-order Butterworth causal filters (`bell`, `diaphragm`) unit-tested. | **SCHEDULED:** Comparative runs scheduled immediately following P0 gate. | **SOFTWARE READY / PHYSICAL MEASUREMENT PENDING** |

---

## 3. Tomorrow's Exact First 3 Actions & Single Launch Command

### Action 1: Hardware Bring-Up & Power Rail Verification (Ozan)
Connect ESP32-S3 to lab laptop USB port. Before running software, measure voltage between INMP441 `VDD` and `GND` pins with multimeter. Confirm $3.14\text{ V} \le V \le 3.46\text{ V}$.

### Action 2: Phantom Inspection & Fallback Pad Placement (Kaan)
Inspect the 12 cm Borcam RTV-2 silicone sample. If surface is tacky, place the dry compliant medical silicone pad over the surface. Align 30 mm $12\ \Omega$ exciter underneath the center; place INMP441 on top with 100 g mass.

### Action 3: Single Master Launch Command on Lab Laptop (Ege)
Open PowerShell terminal, activate virtual environment, and execute the automated phantom protocol:
```powershell
cd c:\Dev\Antigravity\bitirme\ausculta-forge
.\.venv\Scripts\python.exe tools/hardware/run_phantom_pcg_experiment.py --port COM3 --reference data/raw/week6_real_pcg_20261026/circor/40058_AV.wav --play-audio --verify-audio-routing --operator "Kaan_Ozan_Ege" --notes "W10_P0_Physical_Phantom_Trial1"
```
*(Note: Replace `COM3` with the actual USB CDC COM port reported by `python -m serial.tools.list_ports`).*

---

## 4. Fallback Protocols for Anticipated Bench Failures

1. **Uncured / Tacky Silicone:** Do not peel or deform specimen. Place dry compliant silicone barrier pad on top. Annotate run notes: `--notes "Fallback_Compliant_Pad_Used"`.
2. **Clipping / Saturation ($> 0.05\%$ near-clipping or peak $> 0.98\text{ FS}$):** Reduce PAM8403 potentiometer gain immediately. Re-run session until `clipping_detected = False`.
3. **Low Active-to-Quiet Ratio ($< 12\text{ dB}$):** Ensure INMP441 bottom acoustic port is not sealed against plastic housing and exciter is firmly contacting the Borcam bottom. Slightly increase PAM8403 gain.
4. **USB Disconnect / Serial Port Error:** Check USB Type-C cable integrity. Ensure no competing serial terminals (e.g. PuTTY, Arduino IDE, Chrome WebSerial) are holding the COM port open.
