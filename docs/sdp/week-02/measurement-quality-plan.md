# Measurement & Recording Quality Plan
## Week-02 Draft v0.1

- **Status:** DRAFT / WEEK-02
- **Last Updated:** 2026-09-29
- **Owner:** Ege (Module C — Computer Application & Quality Assessment)
- **Contributors:**
  - Kaan (Module A — Acquisition Hardware & Characterisation)
  - Ozan (Module B — Embedded Acquisition & Data Path)
- **Course Context:** EEE495 Senior Design Project I / Semester I — Week 2
- **Relevant GitHub Issue:** [#5 ([EEE495][W2][C] Mandatory measurement and quality plan)](https://github.com/egecagintepe/ausculta-forge/issues/5)
- **Purpose:** Translate the course advisor's mandatory characterization requirements into rigorous, reproducible engineering experimental procedures.

> [!IMPORTANT]
> **SIX MANDATORY ADVISOR MEASUREMENTS:**
> 1. Phantom frequency response from 20 to 500 Hz
> 2. Signal-to-noise ratio (SNR)
> 3. Repeatability across at least 10 repeated measurements
> 4. Mains interference level (50 Hz and harmonics)
> 5. End-to-end latency
> 6. Dropped-packet rate during continuous acquisition
>
> These six physical measurements form the core empirical foundation of EEE495. Machine learning classification and software metrics shall **never** be substituted for these mandatory physical measurements.

---

## 1. Mandatory Measurement Matrix

The table below defines the formal engineering protocol for each mandatory physical measurement:

| Measurement | Engineering Question | Required Input / Experimental Setup | Module A Responsibility | Module B Responsibility | Module C Responsibility | Raw Data to Retain | Analysis Method | Output / Scientific Result | Current Week-02 Status |
|---|---|---|---|---|---|---|---|---|---|
| **1. Phantom Frequency Response** | What is the end-to-end magnitude response and linear coherence of the acoustic transmission chain across 20–500 Hz? | Audio DAC/PC $\to$ Power Amp $\to$ Phantom Exciter $\to$ Silicone Phantom $\to$ Stethoscope Chestpiece $\to$ Microphone $\to$ Preamp/ADC $\to$ MCU $\to$ Host PC. Swept-sine (20–500 Hz logarithmic) or multitone excitation. | Build phantom, mount exciter, ensure silicone coupling, position chestpiece reproducibly. | Ingest raw microphone samples at 48 kHz without digital filtering; stream uncompressed frames to PC. | Generate calibrated excitation; ingest capture; estimate transfer function $H_1(f)$ and coherence $\gamma_{xy}^2(f)$. | Synchronized excitation WAV and capture WAV; session JSON sidecar. | $H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$ via Welch cross-spectral density; report ordinary coherence $\gamma_{xy}^2(f)$ as diagnostic of reliability alongside $H_1(f)$. | Frequency response curve (dB vs Hz), $-3\text{ dB}$ bandwidth, mean band coherence. | **NOT YET MEASURED** |
| **2. Signal-to-Noise Ratio (SNR) / Level Ratio** | What is the ratio of active PCG acoustic stimulus level to quiescent system noise floor? | Standardized PCG recording played through phantom vs quiescent silence (exciter driven with zero input in quiet room). | Characterize acoustic isolation; document ambient noise; fix chestpiece contact force. | Maintain fixed analog gain and ADC configuration across both signal and quiet runs. | Ingest both sessions; compute band-limited RMS power and active-to-quiescent level ratio in dB. | Full 48 kHz audio WAVs for signal and noise runs; session metadata. | Filter 20–500 Hz; compute active-to-quiescent level ratio $\text{SNR}_{\text{conv}} = 20 \log_{10}\left(\frac{\text{RMS}_{\text{signal}}}{\text{RMS}_{\text{noise}}}\right)$ on full-rate audio (adopted experimental convention to be finalized during bench validation). | Scalar level ratio / SNR convention (dB) under declared gain and acoustic conditions. | **NOT YET MEASURED** |
| **3. Measurement Repeatability** | What is the statistical dispersion across $\ge 10$ independent repetitions of the identical measurement? | Repeatable mechanical mounting of chestpiece on silicone phantom; identical excitation sequence triggered 10 times consecutively. | Enforce identical physical positioning, clamping pressure, and silicone temperature across runs. | Maintain identical MCU clock, DMA configuration, and streaming parameters across all runs. | Execute automated test script running 10 trials; calculate mean, standard deviation, and variance. | 10 independent session folders (`run_01` to `run_10`) with raw WAVs and metadata. | Compute target metric ($H_1$ gain, SNR, RMS) per run; compute mean, standard deviation, and range. | Statistical table: mean, std dev ($\sigma$), coefficient of variation ($c_v$), min/max spread. | **NOT YET MEASURED** |
| **4. Mains Interference Level** | What is the electrical and magnetic interference pickup at 50 Hz and its harmonics? | Quiescent baseline acquisition under defined bench power configurations (USB power vs battery, cable dress, shielding). | Test shielded vs unshielded cable routing, chestpiece grounding, and metal enclosure shielding. | Ensure clean MCU analog ground routing and ADC reference decoupling. | Compute high-resolution Welch PSD; extract narrow-band power at 50, 100, 150, 200, 250 Hz relative to full-scale. | Quiescent raw session audio (60 s); grounding/shielding configuration log. | Welch PSD with high frequency resolution ($\Delta f \le 0.5\text{ Hz}$); integrate energy within $\pm 1\text{ Hz}$ of harmonics. | Mains harmonic levels in dBFS; total harmonic mains distortion percentage. | **NOT YET MEASURED** |
| **5. End-to-End Latency** | What is the physical delay from acoustic/electrical excitation at the phantom to host sample availability? | Electrical impulse/step trigger fed simultaneously to phantom exciter and MCU digital input pin (or hardware loopback). | Provide repeatable impulse stimulus and electrical sync marker to bench setup. | Capture hardware trigger timestamp in sample stream or dedicated sync flag in packet header. | Record timestamp delta between stimulus initiation and host packet ingestion buffer arrival. | Hardware timestamped trace or dual-channel loopback WAV recording. | Cross-correlation lag estimation or direct hardware timestamp subtraction: $\Delta t = t_{\text{host}} - t_{\text{stimulus}}$. | Total end-to-end latency in milliseconds (mean and jitter). | **NOT YET MEASURED** |
| **6. Dropped-Packet Rate** | Does the system maintain 100% sample continuity without buffer overruns during prolonged streaming? | Continuous 48 kHz acquisition over extended duration (Week 8 gate requires $\ge 30\text{ minutes}$). | Maintain stable DC power supply and thermal dissipation during prolonged run. | Increment strictly monotonic sequence counter in every transmitted frame; monitor DMA overflow flags. | Ingest stream; track sequence gaps; log missed samples; compute drop rate. | Telemetry stream log; cumulative dropped packet counter; total sample count. | $\text{Drop Rate} = \frac{N_{\text{missed samples}}}{N_{\text{expected samples}}} \times 100\%$. | Total elapsed time, total samples, dropped sample count, drop percentage. | **NOT YET MEASURED** |

---

## 2. Experimental Protocols

### A. Frequency Response (20 to 500 Hz)
- **Metrological Model:** Classical Single-Input Single-Output (SISO) best-linear estimator ($H_1$) implemented in `software/pcg_core/scientific/system_id.py`:
  $$H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$$
  $$\gamma_{xy}^2(f) = \frac{|S_{xy}(f)|^2}{S_{xx}(f) S_{yy}(f)}$$
- **Physical Boundary:** In our bench setup, $H_1(f)$ characterizes the **complete end-to-end electro-acoustic chain** ($\text{DAC} \to \text{amplifier} \to \text{exciter} \to \text{silicone} \to \text{chestpiece} \to \text{transducer} \to \text{ADC} \to \text{MCU} \to \text{PC}$). It is an engineering system transfer function, not an isolated anatomical chest response.
- **Stimulus:** Logarithmic swept sine spanning 10 Hz to 1000 Hz (duration $\ge 10\text{ s}$) or band-limited multitone sequence.
- **Reporting:** Tabulated magnitude response $|H_1(f)|$ in relative dB across 20–500 Hz, reporting ordinary coherence $\gamma_{xy}^2(f) \in [0, 1]$ alongside the transfer-function estimate as a diagnostic of reliability.
- **Rule:** Do not freeze a pass/fail coherence threshold (e.g., candidate criteria such as $\gamma_{xy}^2 \ge 0.8$) until physical bench data and measurement uncertainty are experimentally available. No fabricated pass/fail thresholds shall be applied prior to empirical baseline characterization in Week 5.

### B. Signal-to-Noise Ratio (SNR) / Level Ratio
- **Experimental Definition:** Under our Week-02 experimental convention, the active-to-quiescent level ratio is evaluated between an active acoustic PCG stimulus played through the phantom and a quiescent acoustic baseline:
  $$\text{SNR}_{\text{conv}} = 20 \log_{10}\left( \frac{\text{RMS}_{\text{signal, 20--500 Hz}}}{\text{RMS}_{\text{noise, 20--500 Hz}}} \right)$$
  *(Note: This represents an active-to-quiescent level ratio rather than an exact underlying signal-only SNR; the exact measurement convention will be finalized during physical bench validation).*
- **Documentation Requirements:** Every SNR entry must record:
  - Acoustic room condition (e.g. quiet laboratory ambient sound pressure level).
  - Exciter drive amplitude (Vrms or dBFS).
  - Transducer sensitivity and analog pre-amplifier gain setting.
- **Rule:** Numerical SNR targets are empirical results to be discovered, not pre-invented.

### C. Measurement Repeatability ($\ge 10$ Runs)
- **Procedure:** The phantom setup, transducer coupling, and excitation stimulus are kept mechanically invariant. Ten consecutive measurement runs are recorded:
  $$\text{Run}_1, \text{Run}_2, \dots, \text{Run}_{10}$$
- **Statistical Dispersion:**
  - Mean: $\mu = \frac{1}{N} \sum_{i=1}^N x_i$
  - Sample standard deviation: $\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \mu)^2}$
  - Coefficient of variation: $c_v = \frac{\sigma}{\mu} \times 100\%$
- **Integrity Rule:** All 10 runs must be reported. Cherry-picking runs or discarding outliers without an identified physical apparatus failure is strictly prohibited.

### D. Mains Interference (50 Hz and Harmonics)
- **Grid Context:** Operating under Turkey's 50 Hz electrical power grid.
- **Target Frequencies:** Fundamental (50 Hz), 2nd harmonic (100 Hz), 3rd harmonic (150 Hz), 4th harmonic (200 Hz), 5th harmonic (250 Hz).
- **Setup Variations to Characterize:**
  1. Laptop running on AC mains adapter vs running on internal battery.
  2. Shielded vs unshielded transducer cabling.
  3. Floating vs earth-grounded phantom frame.
- **Reporting:** Narrow-band spectral power at each harmonic in $\text{dBFS}$, computed via high-resolution Welch PSD (`software/pcg_core/scientific/spectral.py`).

### E. End-to-End Latency
- **Definition:** The elapsed time interval from the instant an electrical or acoustic event is generated at the phantom exciter to the instant the corresponding sample is ingested into the host application buffer.
- **Measurement Method:** Hardware synchronization pulse or electrical trigger simultaneously sampled by a reference channel or MCU GPIO.
- **Metrological Boundary:** GUI render/paint latency (browser refresh rate) is **decoupled** from acquisition latency and must not be reported as the primary acquisition latency.

### F. Dropped-Packet Rate & Continuous Acquisition
- **Mechanism:** Monotonic sequence indexing ($0, 1, 2, \dots, N$) verified by `StreamQualityMonitor` (`software/pcg_core/streaming.py`).
- **Advisor Week-8 Gate Requirement:** Sustained continuous streaming for at least 30 minutes (1,800 seconds) without unrecoverable stalling or data corruption.
- **Metric Formulation:**
  $$\text{Drop Rate} = \frac{N_{\text{dropped}}}{N_{\text{total\_expected}}} \times 100\%$$
- **Current Status:** Not yet measured on physical hardware (currently verified on synthetic software test doubles).

---

## 3. Recording-Quality Telemetry Indicators

In addition to the six mandatory physical measurements, Module C provides real-time signal quality checks during active recording:

1. **Digital Saturation / Clipping (`sat_fraction`):** Fraction of full-rate samples reaching $\ge 0.999$ full scale. Indicates digital headroom exhaustion; distinct from acoustic transducer clipping.
2. **Sample Discontinuity / Drop:** Flags missing sequential packets via the sequence counter.
3. **Abnormal Level / RMS Collapse:** Detects sudden collapse of signal energy (provisional software heuristic, e.g. $< -60\text{ dBFS}$; not yet physically calibrated and subject to phantom validation).
4. **Acoustic Contact Loss:** Characterized by loss of sub-100 Hz low-frequency acoustic energy coupled with elevated high-frequency ambient noise (provisional heuristic).
5. **Mains Hum Anomaly:** Detects disproportionate energy spikes centered at 50 Hz.
6. **Reference-vs-Capture Alignment:** Offline automated alignment (`pcg_core.validation`) evaluating cross-correlation, gain ratio, and mean squared error against known reference files.

> [!CAUTION]
> Controlled physical artefact injection (e.g., rubbing chestpiece, acoustic room noise, forced cable flexure) will be executed during late Semester I. Quality thresholds are provisional software heuristics and shall not be calibrated until real phantom data is acquired on bench hardware.

---

## 4. Scientific Reproducibility Rules

To uphold research integrity and satisfy engineering defense requirements:

1. **Script-Generated Artifacts:** All measurement tables, frequency-response plots, and statistical summaries must be generated programmatically by executable scripts in `software/pcg_core/` or `experiments/`.
2. **Local Raw Data Retention:** Raw measurement WAV files and JSON logs must be preserved locally in untracked experiment folders (`experiments/output/`, `data/raw/`). Large binary audio datasets shall not be committed to Git.
3. **No Fabricated Tables:** Under no circumstances shall measurement tables contain estimated, projected, or fabricated values. Unmeasured fields must explicitly read `NOT YET MEASURED`.
4. **Full Provenance Tracking:** Every generated report must record the hardware revision, firmware commit SHA, host software commit SHA, sample rate, filter settings, and date/time of capture.
