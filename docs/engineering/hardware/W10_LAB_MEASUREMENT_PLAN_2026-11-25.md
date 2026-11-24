# AuscultaForge — Week 10 Laboratory Metrology and Measurement Plan

**Document Date:** 2026-11-25  
**Course:** EEE 495 / SDP4 — Smart Digital Stethoscope  
**Author:** AuscultaForge Engineering Team (Kaan, Ozan, Ege)  
**Status:** Approved for Physical Laboratory Session on 25 November 2026

---

## 1. Academic Scope & Official Course Mapping

This measurement plan aligns all experimental protocols with the official course syllabus (`SDP4_Digital_Stethoscope_Plan_EN.docx`) and evaluation rubric (`SDP_Assessment_Criteria_for_Students.docx`).

### Course Requirement Matrix (Weeks 5–10)

| Course Milestone | Official Syllabus Requirement | Implementation & Measurement Protocol | Success Threshold / Criteria |
|---|---|---|---|
| **Week 5** | Acoustic transducer characterisation ($20\text{--}500\text{ Hz}$). | Swept-sine excitation ($20\text{--}1000\text{ Hz}$) through acoustic phantom; FRF $H_1(f)$ estimation. | Magnitude response documented across $20\text{--}500\text{ Hz}$; low-frequency roll-off identified ($<60\text{ Hz}$). |
| **Week 6** | Signal quality, SNR, and interference characterisation. | Dual-session quiet baseline vs. active cardiac stimulus capture; 50 Hz mains line power estimation. | Active-to-quiet band power ratio $\ge 12\text{ dB}$; 50 Hz harmonic power $\le -20\text{ dBFS}$. |
| **Week 7** | Mechanical coupling and tissue-mimicking phantom. | RTV-2 silicone disc ($12\text{ cm} \times 10\text{ mm}$); contact pressure variation ($100\text{ g}$ vs $200\text{ g}$). | Coherence $\gamma^2(f) \ge 0.60$ over $50\text{--}400\text{ Hz}$; stable contact without decoupling. |
| **Week 8** | Continuous streaming & packet drop accounting. | Continuous acquisition stress testing; direct-to-disk streaming candidate. | Zero sequence gaps, 0 CRC-32 errors, 0 DMA overflows during active session. |
| **Week 9 (P0)** | Physical feasibility gate: Known PCG stimulus playback. | Reproduction of CirCor clinical recording (`40058_AV.wav`) through exciter into INMP441 acquisition chain. | Pearson correlation $r \ge 0.70$; S1/S2 envelope match fraction $\ge 70\%$; timing jitter $\le 45\text{ ms}$. |
| **Week 10** | Transducer comparison & digital filter characterisation. | Baseline MEMS vs comparator; 4th-order Butterworth digital filter presets (Bell: $20\text{--}200\text{ Hz}$, Diaphragm: $100\text{--}500\text{ Hz}$). | Filter stopband attenuation $\ge 24\text{ dB/octave}$; signal SNR improvement demonstrated. |

---

## 2. Mathematical Formulations and Metrology Methods

### 2.1 Acoustic Transfer Function ($H_1$ Estimator)
To characterise the acoustic transfer function of the exciter-phantom-microphone chain without being biased by uncorrelated output noise, the $H_1(f)$ estimator is computed using Welch's averaged cross-spectral density:
$$H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$$
where:
- $S_{xx}(f)$ is the auto-spectral power density of the known excitation signal $x(t)$.
- $S_{xy}(f)$ is the cross-spectral density between input $x(t)$ and captured acoustic signal $y(t)$.
- Window length: $N_{\text{win}} = 4096\text{ samples}$ ($\Delta f \approx 11.72\text{ Hz}$ at $f_s = 48\text{ kHz}$), 50% overlap, Hanning taper.

### 2.2 Spectral Coherence Function
The reliability of the linear acoustic transfer measurement across frequency is evaluated via the magnitude-squared coherence:
$$\gamma_{xy}^2(f) = \frac{|S_{xy}(f)|^2}{S_{xx}(f) S_{yy}(f)}, \quad 0 \le \gamma_{xy}^2(f) \le 1$$
- $\gamma_{xy}^2(f) \ge 0.60$ indicates adequate signal-to-noise ratio and predominantly linear transmission across the silicone medium.
- Frequencies where $\gamma_{xy}^2(f) < 0.40$ (typically below $40\text{ Hz}$ due to exciter acoustic decoupling) are flagged as uncertain.

### 2.3 Active-to-Quiet Band Power Ratio (SNR Proxy)
Because an in-vivo reference microphone cannot be embedded inside human tissue during bench testing, the signal-to-noise ratio is measured as the ratio of captured cardiac band power ($20\text{--}500\text{ Hz}$) during active excitation versus ambient quiescent conditions:
$$\text{SNR}_{\text{band}} = 10 \log_{10} \left( \frac{\int_{20}^{500} S_{yy,\text{active}}(f) df}{\int_{20}^{500} S_{yy,\text{quiet}}(f) df} \right) \text{ dB}$$
- **Verification Rule:** If $P_{\text{quiet}} \le 10^{-12}\text{ FS}^2$, the measurement is rejected as `INCONCLUSIVE_QUIET_ZERO_OR_INVALID` to prevent manufacturing synthetic infinite SNR.

### 2.4 Morphological S1/S2 Correspondence
Envelope detection uses the normalised Shannon energy envelope to emphasize heart sound bursts over background murmur:
$$E_s[n] = - y_{\text{norm}}^2[n] \cdot \ln(y_{\text{norm}}^2[n] + \epsilon)$$
Smoothed by a moving rectangular window of $w = 20\text{ ms}$ ($960\text{ samples}$). Peaks are extracted with minimum distance $d_{\text{min}} = 180\text{ ms}$.

A reference peak $t_{\text{ref}, i}$ and captured peak $t_{\text{cap}, j}$ are matched if:
$$|t_{\text{cap}, j} - (t_{\text{ref}, i} + \Delta t_{\text{align}})| \le \tau_{\text{tol}}$$
with tolerance $\tau_{\text{tol}} = 80\text{ ms}$. Matching is strictly **one-to-one and monotonic** (each captured peak matches at most one reference peak).

---

## 3. End-to-End Latency & Packet Accounting

### 3.1 Latency Components
$$\tau_{\text{total}} = \tau_{\text{acoustic}} + \tau_{\text{DMA}} + \tau_{\text{USB}} + \tau_{\text{host}}$$
- **Acoustic propagation ($\tau_{\text{acoustic}}$):** Speed of sound in silicone $c_s \approx 1000\text{ m/s}$; $h = 10\text{ mm} \implies \tau_{\text{acoustic}} \approx 10\ \mu\text{s}$ (negligible).
- **Firmware DMA Framing ($\tau_{\text{DMA}}$):** 256 samples @ 48 kHz mono $= 5.333\text{ ms}$.
- **USB CDC Transport ($\tau_{\text{USB}}$):** 1–2 ms polling interval.
- **Host Processing Queue ($\tau_{\text{host}}$):** $\le 10\text{ ms}$.
- **Measured End-to-End Latency Target:** $\tau_{\text{total}} \le 25\text{ ms}$.

### 3.2 Post-Target DMA Drain Distinction
The ESP32-S3 firmware ring buffer commits samples in discrete 256-sample DMA blocks. For a target of $N = 480{,}000\text{ samples}$, the hardware driver receives up to $480{,}256\text{ samples}$. When clean stop telemetry reports `dropped_samples = 256` alongside `total_crc = 0`, `sequence_gaps = 0`, and `overflows = 0`, these samples are classified as **proven post-target DMA drain**, distinguishing them from genuine mid-stream data loss.

---

## 4. Measurement Uncertainty Budget

| Source of Uncertainty | Parameter Value | Standard Uncertainty $u$ | Impact on Primary Measurement |
|---|---|---|---|
| Sampling Clock Drift | ESP32-S3 crystal ($\pm 20\text{ ppm}$) | $\pm 0.96\text{ Hz}$ at $48\text{ kHz}$ | $\le 0.002\%$ frequency axis stretch over $10\text{ s}$ session. |
| Frequency Resolution | $N = 4096$ Welch FFT | $\Delta f = 11.72\text{ Hz}$ | Limits peak resonance localization to $\pm 5.86\text{ Hz}$. |
| Contact Loading Force | Nominal $100\text{ g}$ load ($\pm 5\text{ g}$) | $\pm 0.049\text{ N}$ ($\pm 5\%$) | Slight variation in high-frequency acoustic damping above $300\text{ Hz}$. |
| Silicone Thickness Tolerance | Nominal $10.0\text{ mm}$ ($\pm 1.0\text{ mm}$) | $\pm 0.58\text{ mm}$ (rectangular) | Damping exponent variation across repeated trials. |
| Microphone Roll-off | INMP441 low-frequency response | $\pm 3\text{ dB}$ below $60\text{ Hz}$ | Attenuates fundamental S1/S2 frequencies ($20\text{--}50\text{ Hz}$); requires explicit notation. |

---

## 5. Regulatory & Safety Disclaimer

This system is an **academic research prototype** developed exclusively for the EEE 495 / EEE 496 undergraduate curriculum. It is **not** an approved medical device and has not received FDA, CE-MDR, or Turkish TITCK regulatory clearance. It must never be used for clinical diagnosis or human patient monitoring.
