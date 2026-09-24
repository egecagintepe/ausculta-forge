# AuscultaForge

**AuscultaForge** is an engineering capstone design project developing an intelligent, digital phonocardiogram (PCG) stethoscope system capable of high-fidelity heart sound acquisition, embedded pre-processing, real-time PC streaming, and digital signal processing.

---

## Current Project Status & Milestone

- **Current Status:** Foundation phase. The core software streaming abstraction, mock PCG generator, stateful Butterworth bandpass filtering, and test suite are operational. No GUI or AI components are introduced at this stage.
- **Current Milestone:**
  $$\text{physical/acoustic source} \longrightarrow \text{microphone} \longrightarrow \text{MCU} \longrightarrow \text{PC} \longrightarrow \text{real-time PCG samples}$$

---

## High-Level Architecture

The system pipeline is designed with strict layer separation. Input acquisition is abstracted behind a common `SampleBlock` container, allowing identical DSP algorithms and downstream analysis to run seamlessly on synthetic mock signals, offline WAV files, USB-UART serial streams, or future wireless transports.

```text
[ Acoustic Head / Sensor ]
          │
          ▼
   [ Microcontroller ]
 (ESP32 Sampling & DMA)
          │  (Serial / Wire Stream)
          ▼
   [ PC Ingestion ]
          │
          ▼
    SampleBlock  ───────────► Common streaming interface
          │                   (sequence, timestamp, fs, samples)
          ▼
    DSP Pipeline
 (Streaming Bandpass)
          │
    ┌─────┴─────────────────────────┐
    ▼                               ▼
Metrics / Verification         Future UI & Logging
(RMS, Peak, Crest Factor)
```

### Core Abstraction: `SampleBlock`
The PC software does not couple directly to wire-level protocols or specific hardware peripherals. Any source produces uniform chunks of normalized 1D float32 audio data wrapped in `SampleBlock`, insulating the signal processing pipeline from sensor changes or protocol adjustments.

---

## Team Responsibility Areas

| Team Member | Area of Responsibility | Key Focus Areas |
|---|---|---|
| **Ozan** | Acoustic / Mechanical Acquisition & Physical Prototype | Chest piece acoustic coupling, bell/diaphragm design, noise isolation, 3D casing, mechanical ergonomics. |
| **Kaan** | Embedded Electronics, ESP32/MCU, Firmware & PCB | Microphone interfacing (I2S/ADC), MCU firmware, DMA buffering, wire protocol, PCB schematics & layout. |
| **Ege** | System Architecture, PC Software, DSP & Integration | Software architecture, PC-side ingestion, DSP filtering pipeline, integration testing, verification tools. |

---

## Repository Structure

```text
ausculta-forge/
├── software/
│   ├── pcg_core/           # PCG streaming abstractions, sources, DSP, metrics
│   │   ├── __init__.py
│   │   ├── models.py       # SampleBlock data structure
│   │   ├── sources.py      # MockPCGSource and WavSource
│   │   ├── dsp.py          # StreamingBandpass filter (stateful sosfilt)
│   │   ├── metrics.py      # RMS, peak, crest factor calculations
│   │   └── demo.py         # Standalone PCG pipeline demonstration
│   ├── tests/              # Automated unit tests
│   │   └── test_core.py
│   ├── pytest.ini          # Pytest configuration for software directory
│   └── requirements.txt    # Python dependencies (numpy, scipy, pytest)
├── firmware/               # Microcontroller firmware and drivers (ESP32)
├── hardware/               # Schematics, PCB layouts, mechanical CAD, acoustic models
├── experiments/            # Exploratory DSP scripts and validation logs
│   └── output/             # (Ignored by git) Local experiment outputs
├── docs/                   # Architectural specs, protocols, and meeting notes
│   ├── architecture/       # Detailed system design documents
│   ├── protocol/           # Draft MCU-to-PC communication specifications
│   │   └── PROTOCOL_DRAFT.md
│   └── meeting-notes/      # Engineering sprint & advisor meeting minutes
├── data/                   # Dataset documentation & guidelines
│   ├── raw/                # (Ignored by git) Untracked local raw datasets
│   ├── processed/          # (Ignored by git) Untracked processed data
│   └── README.md           # Dataset sources and acquisition policies
├── .gitignore              # Ignores venvs, cache, audio, IDE, datasets, and logs
├── pytest.ini              # Pytest configuration for repository root
└── README.md               # Project overview, setup, and architecture
```

---

## Software Setup Instructions

### Prerequisites
- Python 3.11+ (Python 3.13 tested)
- Git

### 1. Environment Setup

Create and activate a virtual environment:

```bash
# Clone the repository
git clone https://github.com/egecagintepe/ausculta-forge.git
cd ausculta-forge

# Create virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate
# Activate on Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r software/requirements.txt
```

### 3. Run Automated Tests

Tests can be executed from the repository root or from within `software/`:

```bash
# From repository root:
pytest

# Or inside software directory:
cd software
pytest
```

### 4. Run the Pipeline Demo

Run the demonstration script to verify the synthetic PCG generator, bandpass filter, and metrics calculation:

```bash
# From repository root:
python -m pcg_core.demo

# Or if running without editable install from root:
$env:PYTHONPATH="software"; python -m pcg_core.demo
```

The script will compute RMS and peak values and generate `demo_raw.wav` and `demo_filtered.wav` (which are automatically ignored by Git).

---

## Design Principles & Project Constraints

- **No Premature GUI / AI:** Focus strictly on clean signal acquisition, deterministic streaming, and filter verification before introducing GUI frameworks or machine learning.
- **Protocol Flexibility:** The byte-level wire protocol between MCU and PC is currently in draft status (`docs/protocol/PROTOCOL_DRAFT.md`) and will be finalized iteratively between Kaan and Ege.
- **Microphone Agnostic:** No assumption is made that the INMP441 or any particular sensor is final; the software ingest layer remains abstracted.
- **Data Privacy:** Raw clinical recordings and medical datasets are never committed to Git.
