# AuscultaForge — Academic Defense Quick Reference Cheatsheet
**Document ID:** `AF-DEFENSE-QUICK-REF-V01`  
**Classification:** `EXAM_CHEATSHEET`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Key Engineering Constants & Numbers

| Parameter | Exact Value | Derivation / Physical Significance |
|---|---|---|
| **Sampling Rate ($f_s$)** | **$48,000 \text{ Hz}$** ($48.000 \text{ kHz}$) | Continuous hardware baseline; $48\times$ oversampling of $500\text{ Hz}$ PCG. |
| **I2S Bit Clock ($f_{\text{SCK}}$)** | **$3,072,000 \text{ Hz}$** ($3.072 \text{ MHz}$) | $f_{\text{SCK}} = 2 \times 32 \text{ bits/slot} \times 48,000 \text{ Hz}$. |
| **Block Size ($N_{\text{block}}$)** | **$512 \text{ samples}$** | $\Delta t = 512 / 48000 = 10.6667 \text{ ms}$; block rate is $93.75 \text{ Hz}$. |
| **Block Payload Size** | **$2,048 \text{ bytes}$** | $512 \text{ samples} \times 4 \text{ bytes/sample}$ (`S32_LE` container). |
| **Raw Audio Bitrate** | **$1.536 \text{ Mbps}$** | $48,000 \text{ samples/s} \times 32 \text{ bits/sample}$ (consumes $\approx 16\%$ of Full-Speed USB). |
| **Cardiac Bandwidth** | **$20\text{--}500\text{ Hz}$** | $S_1$ ($20\text{--}150\text{ Hz}$), $S_2$ ($50\text{--}250\text{ Hz}$), murmurs ($100\text{--}400\text{ Hz}$). |
| **Spectral Bin Width ($\Delta f$)** | **$11.71875 \text{ Hz}$** | $\Delta f = f_s / N_{\text{FFT}} = 48,000 / 4,096$. |
| **Display Decimation** | **$\le 600 \text{ points}$** | Peak-preserving min/max envelope points pushed at $30\text{--}60\text{ Hz}$. |
| **Rolling Buffer Capacity** | **$240,000 \text{ samples}$** | $5.0 \text{ seconds} \times 48,000 \text{ Hz}$ ($\approx 1.92 \text{ MB}$ in memory). |
| **Registered API Routes** | **57 routes** | Programmatically verified in `create_app()`. |
| **Automated Test Count** | **394 pytest tests** | Across 37 test modules (16.42s execution time). |

---

## 2. Essential Mathematical Formulas

### 1. SISO $H_1(f)$ Transfer Function Estimator
$$\hat{H}_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$$
*(Assumes observation noise $v[n]$ is concentrated on output microphone; cancels noise when $S_{xv} = 0$).*

### 2. Magnitude-Squared Coherence
$$\gamma_{xy}^2(f) = \frac{|S_{xy}(f)|^2}{S_{xx}(f) S_{yy}(f)}, \quad 0 \le \gamma_{xy}^2(f) \le 1$$
*($1.0 = \text{ideal linear noiseless transmission}$; $< 0.6 = \text{noise, distortion, or clock drift}$).*

### 3. Teager-Kaiser Energy Operator (TKEO)
$$\Psi[x[n]] = x^2[n] - x[n-1]x[n+1] \approx A^2 \omega_0^2$$
*(Proportional to amplitude squared AND frequency squared; sensitive to murmurs).*

### 4. Least-Squares Path Gain
$$\hat{g}_{\text{LS}} = \frac{\sum_{n=0}^{N-1} x[n] y_{\text{aligned}}[n]}{\sum_{n=0}^{N-1} x^2[n]}$$

### 5. Theoretical SQNR
$$\text{SQNR} \approx 6.02 \times B + 1.76 \ \text{dB} \quad (\approx 146.2 \text{ dB for 24 bits})$$

---

## 3. Hardware Pinout & Wiring Quick Reference

| Transducer Signal | INMP441 Header Pin | ESP32-S3 DevKit Pin | Hardware Role |
|---|---|---|---|
| **Power Supply** | `VDD` | `3V3` ($3.3 \text{ V}$) | Direct 3.3V rail from on-board LDO regulator. |
| **Ground** | `GND` | `GND` | Common ground return. |
| **Channel Select** | `L/R` | `GND` | Tied to Ground for Left Channel output. |
| **Bit Clock** | `SCK` | `GPIO 4` | $3.072 \text{ MHz}$ continuous I2S serial clock. |
| **Word Select** | `WS` | `GPIO 5` | $48.0 \text{ kHz}$ frame synchronization clock. |
| **Serial Data** | `SD` | `GPIO 6` | Serial PCM data stream from microphone to MCU. |
| **Native USB D-** | `USB_DM` | `GPIO 19` | On-chip USB OTG Full-Speed physical transceiver. |
| **Native USB D+** | `USB_DP` | `GPIO 20` | On-chip USB OTG Full-Speed physical transceiver. |

---

## 4. Key Execution Commands (Windows PowerShell)

```powershell
# 1. Activate Virtual Environment
.\.venv\Scripts\Activate.ps1

# 2. Run Central Pytest Test Suite (394 tests)
.\.venv\Scripts\pytest.exe

# 3. Launch Backend Bridge Server
python -m pcg_app.server --host 127.0.0.1 --port 8000

# 4. Launch React Desktop UI
cd software/frontend; npm run dev

# 5. Run Frontend Verification (Lint, Unit Tests, Build)
cd software/frontend; npm run lint; npm test; npm run build
```

---

## 5. Golden Rules for Oral Exam Defense

1. **Acknowledge Hardware Status:** Always state that DirencNet hardware arrived in Week 04 and bench measurements are scheduled for Week 05. **Never claim physical hardware PASS results that were simulated.**
2. **Defend Module Ownership:** Be proud of Module C! You built the host runtime, 394 automated tests, 57 API endpoints, lossless WAV + SHA-256 recording, peak decimation, SISO system ID, and Springer LR-HSMM lab. Give full credit to Kaan for acoustics (Module A) and Ozan for firmware (Module B).
3. **No Clinical Diagnosis:** The project evaluates **acoustic engineering metrology only**. No human trials, no medical diagnoses.
