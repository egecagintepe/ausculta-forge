# Module C — Computer Application & Quality Assessment
## Week 02 Status

- **Status:** DRAFT / WEEK-02
- **Last Updated:** 2026-09-29
- **Owner:** Ege (Module C — Computer Application & Quality Assessment)
- **Course Context:** EEE495 Senior Design Project I / Semester I — Week 2
- **Relevant GitHub Issue:** [#4 ([EEE495][W2][C] Module-C status and B-to-C interface requirements)](https://github.com/egecagintepe/ausculta-forge/issues/4)
- **Purpose:** Provide a truthful snapshot of Module C relative to the advisor's Semester-I plan and explicitly separate completed core work, work ahead of schedule / supporting research, work waiting on Modules A/B, and later-semester work.

---

## 1. Module-C Assessed Responsibility

Under the EEE495/496 project division, Module C (owned by Ege) is responsible for the host computing application, signal-processing chain, acoustic measurement validation, and quality assessment.

Module C owns:
1. **Live Waveform Display:** Real-time host visualization of ingested acoustic phonocardiogram (PCG) signals, maintaining bounded UI display decimation without modifying the full-rate scientific recording stream.
2. **Spectrogram & Spectral Display:** Real-time and offline time-frequency representation (Short-Time Fourier Transform, Welch Power Spectral Density) for inspecting acoustic energy distribution.
3. **Recording Library & Storage:** Deterministic session storage capturing raw unadulterated sensor samples, audio WAV containers, and structured provenance metadata.
4. **Recording Metadata Management:** Structured JSON sidecar management recording hardware profiles, sample rate, bit-depth conventions, host timestamps, and git commit provenance.
5. **Playback & Evaluation Path Using Open PCG Data:** Offline playback sources (`WavSource`, `RealtimeWavSource`, synthetic PCG) allowing deterministic algorithm verification before physical hardware arrival.
6. **Signal-Processing Pipeline:** Streaming digital filtering (stateful Butterworth bandpass filtering using second-order sections), envelope extraction, and feature extraction.
7. **Recording-Quality Assessment:** Real-time and post-acquisition telemetry flags (digital saturation/clipping, discontinuity detection, packet drops, crest factor, RMS drift, and contact-loss indicators).
8. **Automated Evaluation Framework:** Deterministic test suite and reproducible experiment execution scripts (`pcg_core.experiment`, `pcg_core.validation`) enforcing scientific traceability and regression prevention.

---

## 2. Current Implemented Capabilities Audit

The repository implementation was audited to establish an honest baseline of Module C assets. Advanced and supporting work is explicitly distinguished from the core physical stethoscope scope.

| Capability | Status | Evidence / Repository Path | Relevance to EEE495 Core Scope |
|---|---|---|---|
| **React/TypeScript Desktop UI** | DONE | `software/frontend/` | **Core:** Host visualization client providing live waveform, spectrogram, filter selection, and session controls. |
| **Backend Application & Bridge Service** | DONE | `software/pcg_app/app.py`, `software/pcg_app/server.py` | **Core:** Local FastAPI/WebSocket bridge coupling host signal processing, session recording, and frontend display. |
| **Display Pipeline & UI Decimation** | DONE | `software/pcg_app/display_pipeline.py` | **Core:** Bounded peak-preserving decimation ($\le 600$ points) ensuring responsive UI rendering without corrupting full-rate audio. |
| **Device Runtime & State Machine** | DONE | `software/pcg_app/device_runtime.py` | **Core:** Authoritative physical device lifecycle (`ABSENT`, `DETECTED`, `READY`, `STREAMING`, `INTERRUPTED`, `ERROR`) and handshake model. |
| **SampleBlock Container Abstraction** | DONE | `software/pcg_core/models.py` | **Core:** Unified data container decoupling signal ingestion (USB, mock, WAV) from downstream DSP and analysis. |
| **Streaming Bandpass Filtering** | DONE | `software/pcg_core/dsp.py` | **Core:** Stateful discrete-time IIR filtering (`scipy.signal.sosfilt`) with boundary state persistence across sample blocks. |
| **Rolling Buffer Sliding Window** | DONE | `software/pcg_core/buffers.py` | **Core:** Circular buffer maintaining fixed temporal history for sliding analysis and spectral estimation. |
| **Session Recording & Metadata Sidecar** | DONE | `software/pcg_core/recording.py` | **Core:** Dual persistence (raw audio WAV + JSON sidecar) recording session parameters, Git SHA, and quality statistics. |
| **Dataset Ingestion & Handling** | DONE | `software/pcg_core/sources.py`, `data/README.md` | **Core:** Offline verification mechanisms to evaluate algorithms using benchmark PCG recordings prior to hardware delivery. |
| **Basic Signal-Quality Telemetry** | DONE | `software/pcg_core/streaming.py`, `software/pcg_core/metrics.py` | **Core:** Real-time RMS, absolute peak, crest factor, and stream continuity monitoring (dropped packets, sample gaps). |
| **Scientific Signal Characterization** | DONE | `software/pcg_core/scientific/signal_quality.py` | **Core:** Full-rate scalar analysis: digital full-scale utilization, DC bias, digital saturation hits, and zero-crossing statistics. |
| **Scientific Spectral Engine (Welch PSD)** | DONE | `software/pcg_core/scientific/spectral.py` | **Core:** Deterministic Welch PSD estimation with explicit windowing, ENBW correction, and physical bin spacing metadata. |
| **Envelope Extraction Workbench** | DONE | `software/pcg_core/scientific/envelopes.py` | **Supporting:** Stage-A deterministic envelope extraction (Hilbert analytic magnitude, moving RMS, Teager-Kaiser Energy Operator). |
| **System Identification (H1 Estimator)** | DONE | `software/pcg_core/scientific/system_id.py` | **Core:** SISO best-linear frequency response ($H_1$), coherence ($\gamma_{xy}^2$), and spectral partitioning for phantom characterization. |
| **Reference-vs-Capture Alignment Workbench** | DONE | `software/pcg_core/validation.py`, `software/pcg_core/validate_capture.py` | **Core:** Cross-correlation time delay estimation, gain scaling, and residual calculation for bench phantom testing. |
| **Automated Test Suite** | DONE | `software/tests/` (37 test modules) | **Core:** Regression testing covering DSP statefulness, streaming continuity, recording integrity, and scientific calculations. |
| **Springer HSMM Segmentation Support** | DONE (Advanced) | `software/pcg_core/segmentation/springer.py`, `hsmm.py`, `logistic.py` | **Advanced / Supporting Only:** Research-level heart-sound state segmentation (S1, systole, S2, diastole). **NOT a core EEE495 requirement.** |
| **CirCor Real-PCG Validation Infrastructure** | DONE (Advanced) | `software/pcg_core/segmentation/validation/` | **Advanced / Supporting Only:** External dataset benchmarking infrastructure. **NOT a replacement for physical stethoscope characterization.** |

### Critical Scope Clarification:
The presence of Springer logistic-regression HSMM segmentation and CirCor PhysioNet validation tools inside `software/pcg_core/segmentation/` represents advanced algorithmic research. **Under no circumstances shall these software modules be presented as fulfilling or replacing the physical digital stethoscope acoustic validation, phantom testing, and hardware measurements mandated by the EEE495 advisor plan.**

---

## 3. Work Waiting on Module A / Module B

Although the software foundation is substantially advanced, the following tasks are strictly blocked by physical hardware availability and cannot be scientifically completed until Module A (Acoustic Hardware) and Module B (Embedded Ingestion) deliver physical hardware:

1. **Real Microphone / Transducer Input:** Ingestion of live acoustic signals from physical electret condenser or MEMS microphones via hardware interface.
2. **Acoustic Phantom Playback / Capture Validation:** Execution of physical sound transmission through the silicone phantom into the physical stethoscope chestpiece.
3. **Physical Device Telemetry & Status:** Capture of real hardware status registers (DMA buffer flags, I2S sync state, physical battery/supply rail status).
4. **Hardware Packet-Loss & Jitter Evidence:** Empirical quantification of Native USB transport packet delivery, USB endpoint FIFO drops, and bus interrupt timing under full continuous load.
5. **Hardware-Derived Quality Thresholds:** Calibration of digital saturation, noise-floor limits, and contact-loss thresholds against physical acoustic sound pressure and transducer overload points.
6. **Controlled Physical Artefact Tests:** Measurement and characterization of real physical friction, skin rubbing, hand tremor, ambient room speech, and acoustic leakage.
7. **Physical Frequency Response Measurements:** Execution of swept-sine or multitone test sequences through the physical phantom transducer chain to measure real end-to-end transmission $H_1(f)$ from 20 to 500 Hz.
8. **Physical SNR / Noise / Interference Measurements:** Measurement of quiescent acoustic/electrical noise floor and quantification of 50 Hz power-line mains hum in a physical bench environment.
9. **Physical End-to-End Latency:** Experimental measurement of propagation time from physical transducer excitation to host application display frame delivery.

---

## 4. Current Module-C Week-02 Conclusion

- **Schedule Standing:** Module C software and metrology foundations are substantially ahead of the nominal Week-02 course timeline (which nominally only requires opening a dataset, reading a recording, and plotting it).
- **Current Engineering Priority:** The immediate priority is **NOT** adding new software features, GUI eye-candy, or machine learning algorithms.
- **Active Focus:**
  1. Formalize interface requirements for the embedded data path (Module B $\to$ Module C).
  2. Formalize physical measurement procedures and reproducibility protocols with Modules A and B.
  3. Support component selection (BOM v0.1) and experimental design for the upcoming Week-4 and Week-5 gates.
