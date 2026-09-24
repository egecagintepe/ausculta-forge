# AuscultaForge

**AuscultaForge** is an engineering capstone design project developing a digital phonocardiogram (PCG) stethoscope system aimed at reliable heart sound acquisition, embedded sampling, real-time PC streaming, and digital signal processing. High-fidelity acoustic reproduction and clinical utility are design targets to be experimentally validated.

---

## Current Project Status & Milestone

- **Current Status:** Foundation phase. The core software streaming abstraction, mock PCG generator, stateful Butterworth bandpass filtering, and test suite are operational. No GUI, AI, or embedded preprocessing components are implemented yet.
- **Current Milestone:**
  $$\text{physical/acoustic source} \longrightarrow \text{microphone/transducer} \longrightarrow \text{MCU/acquisition unit} \longrightarrow \text{PC} \longrightarrow \text{real-time PCG samples}$$

---

## High-Level Architecture

The system pipeline is designed with strict layer separation. Input acquisition is abstracted behind a common `SampleBlock` container, allowing identical DSP algorithms and downstream analysis to run seamlessly on synthetic mock signals, offline WAV files, USB-UART serial streams, or future wireless transports.

```text
[ Acoustic Head / Sensor ]
          │
          ▼
 [ Microphone / Transducer ]
          │  (Analog / Digital interface)
          ▼
[ MCU / Acquisition Unit ]
 (Candidate: ESP32 family)
          │  (Serial / Wire Stream)
          ▼
   [ Host PC Ingestion ]
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
| **Kaan** | Embedded Electronics, MCU / Acquisition Platform, Firmware & PCB | Sensor interfacing (analog/digital options), MCU firmware, DMA/buffer management, wire communication driver, PCB schematics & layout. |
| **Ege** | System Architecture, PC Software, DSP & Integration | Software architecture, PC-side ingestion, DSP filtering pipeline, integration testing, verification tools. |

---

## Repository Structure

```text
ausculta-forge/
├── software/
│   ├── pcg_core/           # PCG streaming abstractions, sources, DSP, metrics
│   │   ├── __init__.py
│   │   ├── models.py       # SampleBlock data structure
│   │   ├── sources.py      # MockPCGSource, WavSource, and RealtimeWavSource
│   │   ├── dsp.py          # StreamingBandpass filter (stateful sosfilt)
│   │   ├── buffers.py      # RollingBuffer audio sliding window
│   │   ├── streaming.py    # StreamQualityMonitor and LiveStreamingPipeline
│   │   ├── metrics.py      # RMS, peak, crest factor calculations
│   │   ├── analysis.py     # Offline PCG metrics and spectrogram computation
│   │   ├── experiment.py   # Reproducible experiment runner & JSON reporter
│   │   ├── demo.py         # Standalone synthetic PCG pipeline demonstration
│   │   ├── analyze.py      # CLI for real PCG WAV analysis
│   │   └── stream_demo.py  # CLI for live PCG streaming simulation
│   ├── tests/              # Automated unit tests
│   │   ├── test_core.py
│   │   ├── test_analysis.py
│   │   ├── test_streaming.py
│   │   └── test_experiment.py
│   ├── pyproject.toml      # Packaging metadata for editable installation
│   └── requirements.txt    # Python dependencies (numpy, scipy, pytest)
├── firmware/               # Microcontroller firmware and communication drivers
├── hardware/               # Schematics, PCB layouts, mechanical CAD, acoustic models
├── experiments/            # Reproducible experiment configurations and runner
│   ├── configs/            # Tracked experiment configuration files (e.g. baseline.json)
│   └── output/             # (Ignored by git) Generated experiment JSON reports
├── docs/                   # Architectural specs, protocols, and meeting notes
│   ├── architecture/       # Detailed system design documents
│   ├── knowledge-base/     # AuscultaForge Engineering Knowledge Base (study & capstone defense)
│   ├── protocol/           # Draft MCU-to-PC communication specifications
│   │   └── PROTOCOL_DRAFT.md
│   └── meeting-notes/      # Engineering sprint & advisor meeting minutes
├── data/                   # Dataset documentation & guidelines
│   ├── raw/                # (Ignored by git) Untracked local raw datasets
│   ├── processed/          # (Ignored by git) Untracked processed data
│   └── README.md           # Dataset sources and acquisition policies
├── .gitignore              # Ignores venvs, cache, audio, IDE, datasets, and logs
├── pytest.ini              # Central pytest configuration
└── README.md               # Project overview, setup, and architecture
```

---

## Engineering Knowledge Base

Comprehensive engineering explanations, design rationale, mathematical formulations, and capstone defense summaries for all AuscultaForge subsystems are maintained in the [Engineering Knowledge Base](docs/knowledge-base/README.md).

The knowledge base covers:
- [00. Proje Genel Bakışı & Ekip Rolleri](docs/knowledge-base/00-project-overview.md)
- [01. PCG Temelleri & Örnekleme Prensipleri](docs/knowledge-base/01-pcg-fundamentals.md)
- [02. SampleBlock ve Veri Kaynağı Soyutlaması](docs/knowledge-base/02-sampleblock-and-sources.md)
- [03. Blok Tabanlı Akış ve Kayan Tampon](docs/knowledge-base/03-streaming-and-rolling-buffer.md)
- [04. Sayısal İşaret İşleme (DSP) ve Durumlu Filtreleme](docs/knowledge-base/04-dsp-and-filtering.md)
- [05. Spektral Analiz: FFT, Welch PSD ve Spektrogram](docs/knowledge-base/05-spectral-analysis.md)
- [06. Akış Kalitesi İzleme (Stream Quality Monitoring)](docs/knowledge-base/06-stream-quality-monitoring.md)
- [07. Test Stratejisi ve Doğrulama](docs/knowledge-base/07-testing-and-validation.md)
- [Mühendislik Terimleri Sözlüğü (Glossary)](docs/knowledge-base/GLOSSARY.md)

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

### 2. Install Package & Dependencies

Install dependencies and the `software/` package in editable mode:

```bash
pip install -r software/requirements.txt
pip install -e ./software
```

### 3. Run Automated Tests

Tests can be executed directly from the repository root:

```bash
pytest
```

### 4. Run Demonstration & Analysis CLIs

Run the synthetic demo:

```bash
python -m pcg_core.demo
```

Run offline analysis on a real PCG recording:

```bash
python -m pcg_core.analyze data/raw/a0001.wav
```

Simulate live MCU streaming playback from a PCG recording:

```bash
# Live playback at wall-clock speed:
python -m pcg_core.stream_demo data/raw/a0001.wav

# Or fast unpaced mode for quick benchmarks:
python -m pcg_core.stream_demo data/raw/a0001.wav --fast
```

Run reproducible experiment and generate verifiable JSON report:

```bash
# Single file analysis:
python -m pcg_core.experiment --input data/raw/a0001.wav --config experiments/configs/baseline.json

# Batch processing over a directory:
python -m pcg_core.experiment --input data/raw --config experiments/configs/baseline.json
```

---

## Design Principles & Project Constraints

- **No Premature GUI / AI:** Focus strictly on clean signal acquisition, deterministic streaming, and filter verification before introducing GUI frameworks or machine learning.
- **Protocol Flexibility:** The byte-level wire protocol between MCU and PC is currently in draft status (`docs/protocol/PROTOCOL_DRAFT.md`) and will be finalized iteratively between Kaan and Ege.
- **Microphone Agnostic:** No assumption is made that the INMP441 or any particular sensor is final; the software ingest layer remains abstracted.
- **Data Privacy:** Raw clinical recordings and medical datasets are never committed to Git.
