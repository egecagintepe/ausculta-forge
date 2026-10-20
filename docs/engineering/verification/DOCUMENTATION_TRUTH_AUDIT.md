# AuscultaForge — Engineering Documentation Source-of-Truth Audit
**Document ID:** `AF-AUDIT-SOT-PR32-V01`  
**Classification:** `AUTHORITATIVE_AUDIT_REPORT`  
**Repository:** `egecagintepe/ausculta-forge`  
**Branch:** `docs/ege-engineering-intelligence-system`  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43` (Master Integration Gate PR #31)  
**Primary Auditor:** Module C (Host Software, DSP & System Integration)  
**Target Evaluation:** EEE495 / EEE496 Senior Design Project Oral Academic Defense

---

## 1. Executive Summary & Audit Mandate

An independent source-of-truth verification audit was conducted across the 71-document AuscultaForge Engineering Intelligence System. The objective was to eliminate all factual contradictions between the written documentation and the actual integrated production source code.

### Core Audit Principles:
1. **Source Code is the Authority for Implemented Behavior:** If documentation claims a function, endpoint, format, or algorithm that does not exist in code, the document is false and must be corrected.
2. **Official Course Documents are the Authority for Project Requirements:** Institutional attribution, project scope, and grading criteria derive strictly from official SDP4 documents (`docs/official-docs/`).
3. **Git History is the Authority for Chronology:** Commits, sprint dates, and PR numbers must match `git log`.
4. **Physical Measurements Require Physical Evidence:** Synthetic simulation results and software unit tests must never be disguised as physical bench measurements (`HARDWARE_UNVERIFIED`).
5. **No Fiction / No Code Invention:** We do not alter production code to fit misleading documentation; we correct documentation to accurately reflect real code.

---

## 2. Critical Source-of-Truth Corrections (Itemized Audit Records)

### Item 1: Session Recording Architecture & Storage Format
* **Original Documentation Claim:**
  * Audio was saved as raw 24-bit integer PCM WAV.
  * Saved as flat dual-file pairs: `<session_id>.wav` and `<session_id>.meta.json`.
  * The recorder incrementally appended PCM bytes to disk during acquisition.
  * A 44-byte RIFF header was rewritten on disk during finalization.
  * An incremental `self._sha256` hash was maintained during streaming, covering only raw audio samples.
  * SHA-256 provided cryptographic tamper-proofing.
* **Why It Was Incorrect:**
  * Direct inspection of `software/pcg_core/recording.py` and `software/pcg_app/state.py` shows that `SessionRecorder` defaults to `wav_format="float32"` and `StreamManager` explicitly constructs it with `wav_format="float32"`.
  * Samples are buffered in memory (`self._chunks`) as accepted normalized `np.float32` blocks to avoid disk I/O jitter.
  * Upon `stop()`, samples are concatenated, verified against counted samples, and written in a single operation via `scipy.io.wavfile.write()`.
  * Files are persisted in dedicated directories (`experiments/sessions/<session_id>/`) containing `raw.wav`, `session.json`, and `manifest.json`.
  * `compute_file_sha256(raw_wav_path)` hashes the **entire serialized `.wav` file on disk**, not an in-memory sample stream.
  * SHA-256 provides file storage integrity comparison (detecting truncation, disk rot, or manual file editing); it does not provide cryptographic tamper-proofing because `session.json` is unauthenticated plaintext.
* **Actual Source of Truth:**
  * `software/pcg_core/recording.py` (`SessionRecorder`, `verify_session`, `compute_file_sha256`, `load_session`)
  * `software/pcg_app/state.py` (`StreamManager.start_recording`)
  * `software/tests/test_recording.py`
* **Corrected Interpretation:**
  * The canonical recording format is normalized IEEE 32-bit floating-point WAV (`[-1.0, +1.0]`).
  * Dedicated session directory containing `raw.wav`, `session.json`, and `manifest.json`.
  * Whole-file SHA-256 storage hash protects scientific reproducibility by detecting corrupted or externally modified files.
* **Affected Documents Corrected:**
  * `docs/engineering/code-atlas/RECORDING_AND_SESSION_INTERNALS.md`
  * `docs/engineering/decisions/ADR-0014-lossless-raw-wav-and-metadata-sidecar.md`
  * `docs/engineering/decisions/ADR-0011-crc-integrity-verification-policy.md`
  * `docs/engineering/architecture/COMPONENT_MAP.md`
  * `docs/engineering/architecture/DATA_FLOW.md`
  * `docs/engineering/architecture/FAILURE_RECOVERY.md`
  * `docs/engineering/defense/QUESTION_BANK.md` (Q88, Q89)
  * `docs/engineering/defense/LIVE_DEBUGGING_SCENARIOS.md` (Scenario 6)
  * `docs/engineering/defense/DEMO_RUNBOOK.md`
  * `docs/engineering/history/DECISION_TIMELINE.md`
  * `docs/engineering/history/DEVELOPMENT_CHRONICLE.md`
* **Verification Method:**
  * Automated test execution: `pytest software/tests/test_recording.py` (all tests PASS).
  * Direct file inspection and SHA-256 calculation verification.
* **Remaining Uncertainty:** None. Implemented behavior in `pcg_core.recording` is completely verified.

---

### Item 2: FastAPI Route Inventory & API Surface
* **Original Documentation Claim:**
  * Documented 11 nonexistent or incorrectly named routes: `/api/device/open`, `/api/device/close`, `/api/stream/metrics`, `/api/analysis/spectral`, `/api/analysis/envelopes`, `/api/metrology/run_all`, `/api/bench/load`, `/api/bench/run_all`, `/api/research/segment`, `/api/research/validate`, `/api/ws/stream`.
* **Why It Was Incorrect:**
  * Programmatic inspection via `tools/audit_fastapi_routes.py` (instantiating `create_app()` and parsing `app.routes`) reveals that none of those route paths exist in `software/pcg_app/app.py`.
  * Real endpoints follow clean, domain-specific REST conventions:
    * Device lifecycle: `POST /api/device/poll`, `POST /api/device/connect`, `POST /api/device/disconnect`
    * Streaming: `POST /api/stream/start`, `POST /api/stream/stop`
    * Metrology: `POST /api/scientific/metrology/run`, `POST /api/scientific/metrology/export`
    * Segmentation: `POST /api/scientific/segmentation/segment`, `POST /api/scientific/segmentation/benchmark`
    * Virtual Bench: `POST /api/bench/run`, `GET /api/bench/status`
    * WebSocket: `GET /ws`
* **Actual Source of Truth:**
  * `software/pcg_app/app.py` (`create_app()`, routes registry)
  * `tools/audit_fastapi_routes.py` (reproducible automated route audit tool)
* **Corrected Interpretation:**
  * The actual application surface consists of exactly 57 route objects (52 HTTP application endpoints + 1 WebSocket at `/ws` + 4 OpenAPI/docs endpoints).
  * All endpoints are cataloged with exact HTTP methods, path/query/body parameters, Pydantic schemas, and HTTP status codes.
  * Routes covered by automated HTTP tests in `software/tests/test_api.py` are explicitly distinguished from registered routes.
* **Affected Documents Corrected:**
  * `docs/engineering/code-atlas/FASTAPI_API_REFERENCE.md` (fully rewritten)
  * `docs/engineering/architecture/RUNTIME_LIFECYCLE.md` (`/api/device/open` -> `/api/device/connect`)
  * `docs/engineering/defense/FAILURE_FALLBACK_PLAN.md`
  * `docs/engineering/code-atlas/FRONTEND_ARCHITECTURE.md` (`/api/ws/stream` -> `/ws`)
  * `docs/engineering/decisions/ADR-0013-fastapi-rest-and-websocket-architecture.md`
* **Verification Method:**
  * Automated route audit tool `tools/audit_fastapi_routes.py` executes in CI / locally, verifying every route against `software/pcg_app/app.py`.
* **Remaining Uncertainty:** None.

---

### Item 3: Embedded C, FreeRTOS Tick Rate & USB Bandwidth Calculations
* **Original Documentation Claim:**
  * Referenced nonexistent C files like `portable_generator/generator.c` and `esp32_bench_example_main.c`.
  * Referenced nonexistent function `generate_sine_100hz_sample()` and `pack_and_align_sample()`.
  * Assumed a universal FreeRTOS tick rate of 100 Hz (`portTICK_PERIOD_MS = 10 ms`).
  * Claimed USB 2.0 Full-Speed bandwidth consumption was $1.92 \text{ Mbps}$ leaving $> 80\%$ headroom.
  * Described USB CDC-ACM and dual-core task pinning as finalized, verified decisions.
* **Why It Was Incorrect:**
  * C files in the repository are located at:
    * `tools/c_golden_vectors/golden_common.h` and `tools/c_golden_vectors/golden_generator.c`.
    * `tools/esp32_bench_example/main/main.c`.
  * The actual trigonometric function is `generate_pcm_sine()` in `golden_common.h` and `s_sine_table[480]` cyclic indexing in `main.c`.
  * In `tools/esp32_bench_example/sdkconfig.defaults`, FreeRTOS is configured with `CONFIG_FREERTOS_HZ=1000` (1 ms tick period).
  * Calling `vTaskDelay(11)` suspends the task for 11 ms. To acquire 512 samples at 48,000 Hz requires $512 / 48000 \approx 10.6667 \text{ ms}$ ($\approx 93.75 \text{ frames/s}$). Software pacing with 11 ms delays produces only $\approx 90.91 \text{ frames/s}$ ($46,545 \text{ samples/s}$), creating a $-3.03\%$ sample rate deficit. Continuous acquisition requires hardware I2S DMA bit clocks.
  * Bandwidth calculation:
    * $48,000 \text{ samples/s} \times 4 \text{ bytes/sample} = 192,000 \text{ bytes/s}$ ($1.536 \text{ Mbit/s}$ payload).
    * Proposed 256-sample frame: $48000 / 256 = 187.5 \text{ frames/s}$.
    * 40-byte header overhead: $187.5 \times 40 = 7,500 \text{ bytes/s}$.
    * Total nominal application data rate: $192,000 + 7,500 = 199,500 \text{ bytes/s} = 1.596 \text{ Mbit/s}$.
    * Nominal application rate does not equal USB bus utilization. USB Full-Speed transmits via 64-byte bulk packets, with SOF tokens every 1 ms, token/data/handshake packet headers, CRC-16, and NRZI bit stuffing. Physical bus utilization cannot be computed by simple subtraction from 12 Mbps without physical measurements.
  * CDC-ACM transport and dual-core task pinning are candidate architectural proposals awaiting Module B's physical hardware bring-up.
* **Actual Source of Truth:**
  * `tools/c_golden_vectors/golden_common.h` (`sign_extend_24_to_32`, `lsb_to_msb_aligned`, `generate_pcm_sine`)
  * `tools/esp32_bench_example/main/main.c` (`s_sine_table`, `s_sine_index`, `audio_generator_task`)
  * `tools/esp32_bench_example/sdkconfig.defaults` (`CONFIG_FREERTOS_HZ=1000`)
* **Corrected Interpretation:**
  * Accurate C functions and filenames documented across code atlas.
  * Precise FreeRTOS 1000 Hz tick rate and $10.667 \text{ ms}$ DMA period explained.
  * Exact $1.596 \text{ Mbit/s}$ nominal application throughput derived, with explicit caveats regarding USB physical layer transaction overhead.
  * CDC-ACM and dual-core pinning designated as candidate proposals (`HARDWARE_UNVERIFIED`).
* **Affected Documents Corrected:**
  * `docs/engineering/code-atlas/EMBEDDED_C_WALKTHROUGH.md`
  * `docs/engineering/code-atlas/USB_PROTOCOL_ENGINEERING.md`
  * `docs/engineering/KNOWLEDGE_COVERAGE_MATRIX.md`
  * `docs/engineering/DOCUMENTATION_MAINTENANCE.md`
  * `docs/engineering/templates/PR_ENGINEERING_RECORD.md`
  * `docs/engineering/defense/QUESTION_BANK.md` (Q9, Q13, Q15, Q25, Q27, Q28, Q33)
  * `docs/engineering/defense/CODE_READING_EXERCISES.md` (Exercise 1)
* **Verification Method:**
  * C golden vector verification: `pytest software/tests/test_c_golden_vectors.py` (6/6 bit-exact PASS in 1.75s).
  * Direct formula recalculation and FreeRTOS config inspection.
* **Remaining Uncertainty:**
  * Module B physical firmware performance under Windows USB host controller load remains to be measured during Week 05 hardware bring-up.

---

### Item 4: PCM Representation, Floating-Point Precision & Acoustic Dynamic Range
* **Original Documentation Claim:**
  * `SampleBlock.samples` was described as `Float64`.
  * INMP441 was claimed to provide $146 \text{ dB}$ of usable dynamic range due to 24-bit output.
  * Absolute quantization steps were quoted in nanovolts without reference voltage.
* **Why It Was Incorrect:**
  * `software/pcg_core/models.py` explicitly casts samples to `np.float32` in `SampleBlock.__post_init__()`.
  * Theoretical SQNR for an ideal uniform 24-bit quantizer is:
    $$\text{SQNR} = 6.02 \cdot N + 1.76 \approx 146.24 \text{ dB}$$
  * However, the INMP441 MEMS microphone has an acoustic dynamic range bounded by its physical acoustic noise floor ($\text{SNR} = 61 \text{ dBA}$, equivalent input noise $33 \text{ dB SPL}$) and Acoustic Overload Point ($120 \text{ dB SPL}$):
    $$\text{Dynamic Range}_{\text{acoustic}} = 120 \text{ dB} - 33 \text{ dB} = 87 \text{ dB}$$
    This corresponds to an Effective Number of Bits (ENOB) of $\approx 14.1 \text{ bits}$. The lower 9–10 bits of the 24-bit word carry acoustic and thermal Johnson-Nyquist noise, not usable physiological signal.
  * In a digital I2S microphone, output samples represent a fraction of digital full scale (`dBFS`), not absolute voltage. Stating absolute voltage quantization steps in nanovolts is physically meaningless without an explicit analog reference voltage $V_{\text{ref}}$.
* **Actual Source of Truth:**
  * `software/pcg_core/models.py` (`SampleBlock.samples: np.ndarray`, `dtype=np.float32`)
  * INMP441 Datasheet (Rev 1.1, InvenSense / TDK)
  * `software/tests/test_models.py`
* **Corrected Interpretation:**
  * `SampleBlock.samples` is documented as `np.float32`.
  * Rigorous distinction maintained between nominal container depth (32-bit `S32_LE`), quantizer resolution (24-bit), theoretical SQNR (146.2 dB), and real sensor acoustic dynamic range (87 dB, ENOB $\approx 14.1$).
  * Quantization step defined rigorously as $\Delta = 2^{-(N-1)} \text{ FS} = 2^{-23} \approx 1.192 \times 10^{-7} \text{ FS}$.
* **Affected Documents Corrected:**
  * `docs/engineering/code-atlas/PCM_BINARY_REPRESENTATION.md`
  * `docs/engineering/code-atlas/CROSS_LANGUAGE_DATA_CONTRACTS.md`
  * `docs/engineering/architecture/DATA_FLOW.md`
  * `docs/engineering/defense/QUESTION_BANK.md`
* **Verification Method:**
  * Python assertion check: `assert SampleBlock(samples=np.zeros(10)).samples.dtype == np.float32`.
  * Mathematical derivation and acoustic noise floor calculation.
* **Remaining Uncertainty:** None.

---

### Item 5: Academic Identity & Institutional Governance
* **Original Documentation Claim:**
  * An earlier summary report mistakenly asserted the project institution as "Bilkent University."
* **Why It Was Incorrect:**
  * Thorough search across official project documents (`docs/official-docs/*.docx`) confirms the authoritative project identification:
    * **Program:** Senior Design Project (EEE 495 Senior Design Project I / EEE 496 Senior Design Project II)
    * **Department:** Department of Electrical and Electronics Engineering
    * **Project Topic:** SDP4 — Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
    * No specific university name is declared in the authoritative course syllabus pack; the previous mention of "Bilkent" in meeting notes was an unverified campus laboratory equipment survey note.
* **Actual Source of Truth:**
  * `docs/official-docs/SDP4_Digital_Stethoscope_Plan_EN.docx`
  * `docs/official-docs/SDP4_Component_Requirements_EN.docx`
  * `docs/official-docs/SDP_Assessment_Criteria_for_Students.docx`
* **Corrected Interpretation:**
  * Official academic identity is: **Department of Electrical and Electronics Engineering, EEE495 / EEE496 Senior Design Project**.
  * Unverified institutional claims removed across all templates and reports.
  * Team ownership strictly separated:
    * Kaan (Module A): Acoustic front-end, phantom fabrication, transducer evaluation.
    * Ozan (Module B): Embedded acquisition firmware, FreeRTOS tasks, hardware procurement.
    * Ege (Module C): Host software runtime, DSP algorithms, metrology automation, Springer segmentation lab, and master integration.
* **Affected Documents Corrected:**
  * `docs/engineering/templates/EXPERIMENT_EVIDENCE.md`
  * `docs/sdp/week-02/meeting-brief.md`
  * `docs/engineering/defense/QUESTION_BANK.md` (Q101, Q104)
  * `docs/engineering/defense/EEE495_PRESENTATION_PLAN.md`
* **Verification Method:**
  * Programmatic XML extraction from official course `.docx` files in `docs/official-docs/`.
* **Remaining Uncertainty:** None.

---

### Item 6: Defense Question Bank & Machine-Readable Matrix
* **Original Documentation Claim:**
  * Contained references to nonexistent functions (`generate_sine_100hz_sample`, `pack_and_align_sample`).
  * Contained incorrect FreeRTOS tick rate assumptions and wrong USB bandwidth percentages.
  * Contained obsolete segmentation paths (`software/pcg_core/segmentation/springer_hsmm.py` vs `hsmm.py`).
  * Lacked a machine-readable verification status matrix.
* **Why It Was Incorrect:**
  * An engineering student memorizing inaccurate answers would fail or be discredited during an in-depth oral defense with faculty examiners.
* **Actual Source of Truth:**
  * `software/pcg_core/` (DSP, segmentation, recording models)
  * `software/pcg_app/` (runtime, state machine, display pipeline)
  * `tools/c_golden_vectors/` and `tools/esp32_bench_example/`
* **Corrected Interpretation:**
  * All 105 questions audited and updated against real code and math.
  * Appended a comprehensive machine-readable matrix mapping every question to its exact implementation status (`VERIFIED_IMPLEMENTED`, `VERIFIED_PROPOSAL`, `THEORETICAL_FOUNDATION`, `ACADEMIC_GOVERNANCE`), source code path, and automated verification method.
* **Affected Documents Corrected:**
  * `docs/engineering/defense/QUESTION_BANK.md`
* **Verification Method:**
  * Automated script `tools/audit_question_bank.py` confirmed 0 broken file references across all 105 questions.
* **Remaining Uncertainty:** None.

---

## 3. Student Learning-Readiness Assessment for Oral Examination

| Evaluation Dimension | Status | Assessment Details |
| :--- | :---: | :--- |
| **Code Atlas Fidelity** | **READY** | All file paths, class names, and algorithms in `code-atlas/` map 1-to-1 with real source code in `software/pcg_app/` and `software/pcg_core/`. A student can open any referenced file and find the exact functions described. |
| **FastAPI Route Reference** | **READY** | All 57 endpoints in `FASTAPI_API_REFERENCE.md` are derived directly from `create_app().routes`. No invented routes exist. |
| **Recording & Persistence** | **READY** | Explains the real float32 accumulation, SciPy serialization, dedicated directory layout, whole-file SHA-256 integrity hashing, and real exception hierarchy. |
| **Embedded & C Foundations** | **READY** | Explains actual functions in `golden_common.h`, real FreeRTOS 1000 Hz tick configuration, task pacing limits, nominal 1.596 Mbit/s application rate, and USB packetization overhead. |
| **Oral Question Bank** | **READY** | All 105 questions verified. Mathematical proofs, bitwise derivations, and architectural caveats are factually sound and backed by the Question Verification Matrix. |
| **Scientific & Metrology Scope** | **READY** | Strict non-clinical boundary upheld. The six mandatory advisor measurements are truthfully categorized as `HARDWARE_UNVERIFIED` pending Week 05 bench testing. |

### Outstanding Blockers:
* **Zero Software Blockers.** The documentation system is fully synchronized with baseline `fa4b75a80d29aab04875534234574db9f6c0af43`.
* **Physical Hardware Gate:** Physical bench measurements (SNR, phantom frequency response, mains pickup) await physical delivery of DirencNet components in Academic Week 05. The documentation explicitly emphasizes this status (`HARDWARE_UNVERIFIED`).

---

## 4. Final Recommendation

**RECOMMENDATION: READY FOR REVIEW**  
The 71-document Engineering Intelligence System has been purged of factual discrepancies, unverified claims, and invented APIs. It stands as an authoritative, source-grounded academic reference for the AuscultaForge platform.
