# Smart Digital Stethoscope

**Heart Sound Acquisition, Signal Processing and Quality Assessment**

EEE495 / EEE496 Senior Design Project
Department of Electrical and Electronics Engineering
Repository / Software Codename: `AuscultaForge`

---

## Project Overview

This repository contains the implementation developed for the EEE495/EEE496 Senior Design Project titled **"Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment"** in the Department of Electrical and Electronics Engineering.

The project investigates a complete digital stethoscope acquisition chainâ€”from the acoustic chestpiece and transducer front-end, through embedded microcontroller acquisition and streaming, to a host computer applicationâ€”supported by repeatable acoustic phantom characterisation and recording-quality assessment.

The internal repository and software platform codename is **AuscultaForge**.

> [!NOTE]
> **Engineering Prototype Notice:**
> This project is an undergraduate engineering capstone prototype and experimental research platform. It is **not** a certified medical device, does **not** provide clinical diagnostic interpretations, and does **not** involve human-subject clinical trials. All physical acoustic characterisation is performed on bench acoustic phantoms.

---

## Formal Project Scope & Boundaries

The project scope is strictly governed by the official EEE495/EEE496 design requirements:

### Core Scope
- **Acoustic Modality:** Cardiac phonocardiography (PCG / heart sounds) only.
- **Acquisition Hardware:** Team-designed acoustic chestpiece coupling, microphone transducer selection, and analogue signal conditioning.
- **Embedded Acquisition & Data Path:** Microcontroller audio sampling (nominal 48 kHz continuous acquisition baseline), DMA buffering, sample continuity tracking, and wired transport to host.
- **Host Computer Application:** Real-time waveform display, spectrogram, session recording with technical metadata sidecars, device status tracking, and recording-quality assessment.
- **Acoustic Phantom:** Repeatable physical bench test fixture (audio exciter, power amplifier, compliant silicone/gel tissue layer, and rigid mounting frame).
- **Engineering Characterisation:** Formal measurement of frequency response, signal-to-noise ratio, repeatability, mains interference, end-to-end latency, and stream continuity.
- **Automated Workflow:** Script-driven, reproducible measurement and verification pipeline.

### Fixed Boundaries & Academic Constraints
- **No Human Subjects:** All physical acoustic verification is conducted strictly on laboratory acoustic phantoms.
- **No Diagnostic Claims:** The platform assesses technical signal quality and physical transmission fidelity, not medical pathology.
- **No Lung Sound Scope:** Lung sounds are strictly out of scope; focused entirely on phonocardiographic cardiac acoustics ($20\text{--}500\text{ Hz}$).
- **Machine Learning is Optional:** Diagnostic machine learning or automated classification is not a primary course success criterion.
- **Photoplethysmography (PPG) is an Optional Extension:** PPG is an optional Semester-II extension outside the assessed core scope. It is not required for project success and is not a current core deliverable.
- **Custom PCB is Optional:** Initial development uses breadboard and dev-board setups. A soldered prototype (e.g., perfboard / stripboard) is entirely sufficient for course completion unless experimental measurements justify a custom PCB spin.

---

## Module Ownership

The advisor-defined structural rule requires one primary student owner per Module (A, B, C) for a three-student team to enable individual assessment, Git contribution tracking, and capstone defense. The table below reflects the **current team working allocation (pending formal advisor confirmation)**:

| Module | Scope | Working Allocation (Pending Advisor Confirmation) | Key Responsibilities |
|---|---|---|---|
| **Module A** | Acquisition Hardware & Characterisation | **Kaan** | Transducer evaluation (electret vs MEMS), acoustic chestpiece coupling, analogue front-end conditioning, acoustic phantom design, physical test setup, and experimental characterisation. |
| **Module B** | Embedded Acquisition & Data Path | **Ozan** | Microcontroller hardware integration, audio sampling, DMA ping-pong buffering, monotonic sample continuity counter, Native USB data transport, error telemetry, and Turkish local component sourcing (BOM). |
| **Module C** | Computer Application & Quality Assessment | **Ege** | Host PC desktop application (React/TypeScript), FastAPI bridge service, streaming DSP pipeline, recording library with JSON metadata sidecars, recording-quality assessment, and automated test suite. |

*Team members support each other across module boundaries during integration, but each module has one clear primary owner responsible for its engineering rigor and oral defense.*

---

## Expected Course Outputs & Current Status

| Expected Output | Status | Evidence / Repository Location |
|---|---|---|
| **Working digital-stethoscope prototype** | IN PROGRESS | Breadboard / bench hardware assembly underway (Target: Week 5). |
| **Team-designed acquisition electronics** | IN PROGRESS | Analogue front-end and transducer evaluation underway (`hardware/`). |
| **Embedded firmware & ingestion path** | IN PROGRESS | ESP32-S3 Native USB data-path architecture designed (`firmware/`). |
| **Documented device-to-computer protocol** | IN PROGRESS | Protocol requirements draft: [`docs/sdp/week-02/bc-interface-requirements.md`](docs/sdp/week-02/bc-interface-requirements.md). |
| **PC Application â€” Live Waveform Display** | DONE | Bounded peak-preserving decimation pipeline: `software/pcg_app/display_pipeline.py`. |
| **PC Application â€” Spectrogram Display** | DONE | Time-frequency STFT visualization in frontend and analysis engine (`software/pcg_core/analysis.py`). |
| **PC Application â€” Session Recording & Metadata** | DONE | Dual persistence (raw audio WAV + JSON sidecar): `software/pcg_core/recording.py`. |
| **PC Application â€” Device Control & Status** | DONE | Authoritative device lifecycle state machine: `software/pcg_app/device_runtime.py`. |
| **PC Application â€” Recording-Quality Feedback** | DONE | Real-time and offline scalar metrics: `software/pcg_core/scientific/signal_quality.py`. |
| **Repeatable acoustic phantom** | PLANNED | Phantom electro-acoustic requirements drafted (Exciter + Amp + Silicone + Frame). |
| **Automated test suite** | DONE | Central test suite with 274+ automated tests: `software/tests/`. |
| **Characterisation measurement report** | PLANNED | Protocols and measurement matrix formalized: [`docs/sdp/week-02/measurement-quality-plan.md`](docs/sdp/week-02/measurement-quality-plan.md). |
| **Comparison of $\ge 2$ transducer candidates** | PLANNED | Technical selection criteria drafted for Week-3 evaluation (Electret vs MEMS). |
| **Comparison of $\ge 2$ prototyping approaches** | PLANNED | Breadboard vs soldered prototype comparison planned for Semester I / II. |
| **Quality check against controlled artefacts** | PLANNED | Physical friction, rubbing, and movement artefact testing scheduled for late Semester I. |
| **Reproducible repository & documentation** | DONE | Comprehensive engineering knowledge base and reproducible experiment CLI runners. |

---

## Mandatory Engineering Measurements

The course advisor mandates **six primary final physical measurements** to characterize the digital stethoscope prototype. These physical measurements cannot be replaced by software simulations or machine learning metrics:

1. **Phantom Frequency Response ($20\text{--}500\text{ Hz}$):** End-to-end magnitude response $|H_1(f)|$ and coherence $\gamma_{xy}^2(f)$ estimated via the SISO best-linear estimator (`software/pcg_core/scientific/system_id.py`).
2. **Signal-to-Noise Ratio (SNR):** Band-limited ($20\text{--}500\text{ Hz}$) ratio of active phantom PCG acoustic stimulus power to quiescent noise floor in relative dB.
3. **Measurement Repeatability ($\ge 10$ Runs):** Statistical dispersion (mean, standard deviation, coefficient of variation, and min/max spread) across at least 10 identical, independent phantom measurements.
4. **Mains Interference Level:** High-resolution spectral quantification of 50 Hz fundamental and harmonic pickup ($100, 150, 200, 250\text{ Hz}$) in dBFS under varied shielding and grounding arrangements.
5. **End-to-End Latency:** Propagation delay from electrical/acoustic excitation at the phantom exciter to sample buffer ingestion on the host PC.
6. **Dropped-Packet Rate:** Verification of 100% sample continuity via the monotonic sequence counter during prolonged streaming (including the advisor-mandated $\ge 30$-minute continuous acquisition test in Week 8).

> [!IMPORTANT]
> All physical measurements are currently marked **NOT YET MEASURED**. No numerical thresholds or fabricated values are applied prior to physical bench experiments.

---

## Academic Roadmap & Semester Milestones

```text
Semester I (EEE495) â€” Foundation & Feasibility
â”œâ”€â”€ Week 02 (Current): Technical research, requirements draft, Turkish sourcing BOM v0.1.
â”œâ”€â”€ Week 03: Component selection, frame format draft, purchase-ready BOM v1.0.
â”œâ”€â”€ Week 04 GATE: Requirements specification frozen, components ordered, lab tools secured.
â”œâ”€â”€ Week 05 GATE: Bench setup operational, known test signal captured end-to-end.
â”œâ”€â”€ Week 08: 30-minute continuous streaming stability test.
â”œâ”€â”€ Week 09 FEASIBILITY GATE: Phantom PCG capture with recognisable S1/S2 acoustic structure.
â”‚                           (If unrecognisable: revise transducer/coupling before adding features).
â””â”€â”€ Week 13: Baseline device works end-to-end (Phantom -> HW -> MCU -> PC App),
             initial characterisation complete, interim report submitted.

Semester II (EEE496) â€” Hardening, Characterisation & Defense
â”œâ”€â”€ Hardware hardening onto a soldered prototype (where justified by bench measurements).
â”œâ”€â”€ Recording-quality evaluation validated against controlled physical artefacts.
â”œâ”€â”€ Full characterisation campaign across all six mandatory measurements.
â”œâ”€â”€ Microcontroller power consumption and host processing-load profiling.
â””â”€â”€ Final engineering report, project demonstration, and capstone oral defense.
```

---

## Advanced Existing Work (Supporting Research)

The repository contains advanced software and signal-processing implementations developed during early prototyping:

- **Springer LR-HSMM Heart-Sound Segmentation:** Machine-learning-assisted segmentation (`software/pcg_core/segmentation/`) predicting cardiac states ($S_1$, systole, $S_2$, diastole) via duration-dependent Hidden Semi-Markov Models.
- **CirCor Real-PCG Validation Infrastructure:** Automated benchmarking suite (`software/pcg_core/segmentation/validation/`) evaluating segmentation tolerance on open-access pediatric PCG records.
- **Envelope Extraction Lab:** Stage-A analytical Hilbert, moving RMS, and Teager-Kaiser Energy Operator (TKEO) extractors (`software/pcg_core/scientific/envelopes.py`).
- **SISO System Identification Workbench:** Cross-spectral transfer function and coherence estimation tools (`software/pcg_core/scientific/system_id.py`).

> [!NOTE]
> **Academic Scope Distinction:**
> These capabilities represent **ADVANCED / SUPPORTING RESEARCH**. They provide valuable scientific insight and offline verification tools, but they do **NOT** fulfill or substitute for the mandatory physical acquisition hardware, acoustic phantom experiments, and hardware characterisation required by the course.

---

## High-Level System Architecture

The AuscultaForge software pipeline enforces strict layer separation. Input acquisition is abstracted behind a common `SampleBlock` container, allowing identical DSP algorithms, filtering, and downstream analysis to run seamlessly on physical hardware streams, offline WAV files, or synthetic mock sources.

```text
[ Acoustic Phantom / Test Exciter ]
                â”‚
                â–¼
[ Stethoscope Chestpiece & Microphone ]
  (Electret Condenser or MEMS Transducer)
                â”‚  (Analogue / I2S Interface)
                â–¼
[ Microcontroller Acquisition Unit ]
  (ESP32-S3: Sampling, DMA Double-Buffering, Continuity Counter)
                â”‚  (Wired Native USB Stream)
                â–¼
      [ Host PC Ingestion ]
                â”‚
                â–¼
           SampleBlock  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º Common Streaming Interface
                â”‚                    (sequence, timestamp, fs, samples)
                â–¼
          DSP Pipeline
       (Stateful Bandpass)
                â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â–¼                                â–¼
   Live Metrics                 Display Pipeline
(RMS, Peak, Crest)            (Peak-Preserving Decimation)
        â”‚                                â”‚
        â–¼                                â–¼
Session Recording Sidecar          React Desktop UI
 (WAV + JSON Metadata)         (Waveform & Spectrogram)
```

---

## Repository Structure

```text
ausculta-forge/
â”œâ”€â”€ software/
â”‚   â”œâ”€â”€ pcg_app/            # FastAPI desktop bridge, device runtime, and display decimation
â”‚   â”‚   â”œâ”€â”€ app.py          # REST & WebSocket server
â”‚   â”‚   â”œâ”€â”€ device_runtime.py # Authoritative hardware lifecycle state machine
â”‚   â”‚   â”œâ”€â”€ display_pipeline.py # Peak-preserving UI decimation (<= 600 points)
â”‚   â”‚   â”œâ”€â”€ protocol.py     # Local WebSocket bridge protocol
â”‚   â”‚   â””â”€â”€ state.py        # StreamManager and client session management
â”‚   â”œâ”€â”€ pcg_core/           # Core signal processing, streaming, and scientific engines
â”‚   â”‚   â”œâ”€â”€ models.py       # SampleBlock container dataclass
â”‚   â”‚   â”œâ”€â”€ sources.py      # MockPCGSource, WavSource, RealtimeWavSource
â”‚   â”‚   â”œâ”€â”€ dsp.py          # Stateful StreamingBandpass filter (sosfilt)
â”‚   â”‚   â”œâ”€â”€ buffers.py      # RollingBuffer circular FIFO window
â”‚   â”‚   â”œâ”€â”€ streaming.py    # StreamQualityMonitor continuity tracking
â”‚   â”‚   â”œâ”€â”€ recording.py    # Dual persistence (raw WAV + JSON sidecar)
â”‚   â”‚   â”œâ”€â”€ scientific/     # Full-rate spectral, envelope, and system ID engines
â”‚   â”‚   â””â”€â”€ segmentation/   # Advanced research: Springer LR-HSMM & CirCor validation
â”‚   â”œâ”€â”€ frontend/           # React / TypeScript / Vite local desktop UI
â”‚   â”œâ”€â”€ tests/              # Automated pytest suite (37 test modules)
â”‚   â”œâ”€â”€ pyproject.toml      # Packaging metadata for editable install
â”‚   â””â”€â”€ requirements.txt    # Python dependencies (numpy, scipy, fastapi, pytest)
â”œâ”€â”€ firmware/               # Microcontroller firmware and USB transport drivers
â”œâ”€â”€ hardware/               # Analogue schematics, CAD, component evaluation, and BOM
â”œâ”€â”€ experiments/            # Reproducible experiment configurations and runner scripts
â”‚   â”œâ”€â”€ configs/            # Tracked configuration files (e.g. baseline.json)
â”‚   â””â”€â”€ output/             # (Ignored by git) Local measurement outputs and reports
â”œâ”€â”€ docs/                   # Engineering documentation and course deliverables
â”‚   â”œâ”€â”€ sdp/week-02/        # Official Week-02 project-management pack
â”‚   â”‚   â”œâ”€â”€ module-c-status.md
â”‚   â”‚   â”œâ”€â”€ bc-interface-requirements.md
â”‚   â”‚   â”œâ”€â”€ measurement-quality-plan.md
â”‚   â”‚   â””â”€â”€ meeting-brief.md
â”‚   â”œâ”€â”€ architecture/       # System design specifications
â”‚   â”œâ”€â”€ knowledge-base/     # Comprehensive engineering knowledge base
â”‚   â”œâ”€â”€ protocol/           # Wire-level MCU-to-PC protocol specifications
â”‚   â””â”€â”€ research/           # Literature registry (R001â€“R008) and scientific conventions
â”œâ”€â”€ data/                   # Dataset documentation & guidelines
â”‚   â”œâ”€â”€ raw/                # (Ignored by git) Local raw audio recordings
â”‚   â””â”€â”€ processed/          # (Ignored by git) Local processed datasets
â”œâ”€â”€ .gitignore              # Ignores venvs, cache, audio data, and build artifacts
â”œâ”€â”€ pytest.ini              # Pytest configuration
â””â”€â”€ README.md               # Main project overview (this document)
```

---

## Software Setup & Verification

### Prerequisites
- Python 3.11+ (Python 3.11â€“3.13 tested)
- Node.js 18+ (for frontend desktop UI)
- Git

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/egecagintepe/ausculta-forge.git
cd ausculta-forge

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install Python dependencies and package in editable mode
pip install -r software/requirements.txt
pip install -e ./software
```

### 2. Run Automated Tests
```bash
# Execute central test suite from repository root
pytest
```

### 3. Run Demonstration & Simulation CLIs
```bash
# Run synthetic PCG streaming pipeline demonstration
python -m pcg_core.demo

# Run offline analysis on a real PCG WAV file
python -m pcg_core.analyze data/raw/sample.wav

# Simulate live paced streaming playback
python -m pcg_core.stream_demo data/raw/sample.wav

# Run reproducible experiment and generate JSON report
python -m pcg_core.experiment --input data/raw/sample.wav --config experiments/configs/baseline.json

# Run reference-vs-capture alignment validation
python -m pcg_core.validate_capture --reference data/raw/ref.wav --simulate --delay-ms 45 --save-report
```

---

## References & Documentation Links
- **Week-02 Project Planning Pack:** [`docs/sdp/week-02/`](docs/sdp/week-02/)
- **Engineering Knowledge Base:** [`docs/knowledge-base/README.md`](docs/knowledge-base/README.md)
- **Literature & Research Governance:** [`docs/research/README.md`](docs/research/README.md)
- **System Architecture:** [`docs/architecture/README.md`](docs/architecture/README.md)
