# AuscultaForge — Dependency, License & Scientific Provenance Audit
**Document ID:** `AF-LEGAL-DEPENDENCY-AUDIT-V01`  
**Classification:** `LEGAL_AUDIT` / `PROVENANCE_RECORD`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Executive Summary & Legal Compliance Framework

Academic research and open-source medical software require strict software license compliance and algorithmic provenance tracking. Committing third-party code without proper attribution, violating copyleft provisions (e.g. GPL viral contamination in proprietary contexts), or ignoring dataset redistribution restrictions undermines academic integrity.

This audit reviews every software dependency, adapted algorithm, literature source, and benchmark dataset utilized in AuscultaForge.

---

## 2. Python Runtime & Development Dependencies

Audited from `software/pyproject.toml` and `software/requirements.txt`:

| Package Name | Pinned / Min Version | License | Upstream Origin | Subsystem Role | License Compatibility Notes |
|---|---|---|---|---|---|
| **`numpy`** | `^1.26.0` / `>=1.24.0` | BSD 3-Clause | NumPy Developers | Core array processing, `SampleBlock` | Permissive; compatible with project distribution. |
| **`scipy`** | `^1.12.0` / `>=1.11.0` | BSD 3-Clause | SciPy Developers | Signal processing (`sosfilt`, `welch`, `resample_poly`) | Permissive; core scientific mathematical engine. |
| **`fastapi`** | `^0.110.0` / `>=0.110.0` | MIT | Tiangolo / FastAPI | REST and WebSocket application bridge | Permissive; lightweight ASGI framework. |
| **`uvicorn`** | `^0.28.0` / `>=0.28.0` | BSD 3-Clause | Encode / Uvicorn | High-performance ASGI web server | Permissive; executes asynchronous event loop. |
| **`pyserial`** | `>=3.5` | BSD 3-Clause | Chris Liechti | USB CDC-ACM virtual COM communication | Permissive; non-blocking hardware serial access. |
| **`anyio`** | `>=4.0.0` | MIT | Alex Grönholm | Asynchronous task primitives and synchronization | Permissive; used for background stream pumps. |
| **`pytest`** | `>=8.0.0` | MIT | Holger Krekel et al. | Automated regression test execution | Permissive; development dependency only. |
| **`pytest-asyncio`** | `>=0.23.0` | Apache 2.0 | pytest-dev | Asynchronous coroutine test execution | Permissive; development dependency only. |

* **License Conclusion:** All core Python runtime dependencies are licensed under permissive open-source licenses (BSD 3-Clause, MIT, Apache 2.0). There is **zero viral copyleft (GPL) dependency** in the runtime.

---

## 3. Frontend Dependencies (Node.js / React)

Audited from `software/frontend/package.json`:

| Package Name | Installed Version | License | Upstream Project | Role in Application |
|---|---|---|---|---|
| **`react`** | `^18.2.0` | MIT | Meta Platforms, Inc. | User interface rendering engine |
| **`react-dom`** | `^18.2.0` | MIT | Meta Platforms, Inc. | DOM element binding and lifecycle |
| **`vite`** | `^6.4.3` | MIT | Yuxi (Evan) You et al. | Development dev-server and Rollup bundler |
| **`typescript`** | `^5.2.2` | Apache 2.0 | Microsoft Corporation | Compile-time type analysis (`tsc --noEmit`) |
| **`tsx`** | `^4.7.0` | MIT | Privatenumber | Direct execution of TypeScript test suites |

* **License Conclusion:** 100% of frontend packages use MIT or Apache 2.0 licenses.

---

## 4. Algorithmic Adaptations & Upstream Provenance

AuscultaForge integrates algorithmic techniques originally described in peer-reviewed biomedical literature. The adaptation boundaries are strictly documented below:

### 4.1 Springer Logistic Regression-HSMM Segmentation
* **Original Publication:** Springer, Tarassenko, & Clifford, *"Logistic Regression-HSMM-based Heart Sound Segmentation,"* IEEE TBME, 2016 (Source R001).
* **Original Implementation:** MATLAB / C implementation released under open academic license by Oxford University / PhysioNet.
* **AuscultaForge Adaptation:**
  * Clean-room reimplementation in pure Python (`pcg_core/segmentation/springer_hsmm.py` and `springer_logistic.py`).
  * Direct transcription of mathematical formulations (extended Viterbi dynamic programming, Bayes emission derivation, Gaussian duration modeling).
  * No proprietary Oxford C source files are copied into this repository.

### 4.2 Schmidt Spike Removal Algorithm
* **Original Publication:** Schmidt et al., *"A markerless method for heart sound segmentation,"* Computers in Cardiology, 2010 (Source R002).
* **AuscultaForge Adaptation:**
  * Pure Python implementation (`pcg_core/segmentation/preprocessing.py`) following published mathematical definitions (median of window maxima).

---

## 5. Benchmark Datasets & Data Governance

| Dataset Name | Primary Citation | License / Terms of Use | Usage in AuscultaForge | Data Storage Location |
|---|---|---|---|---|
| **CirCor DigiScope Pediatric PCG Dataset** | Oliveira et al., *"The Circor DigiScope Dataset,"* PhysioNet Challenge 2022 (Source R008) | Open Data Commons Attribution License (ODC-By v1.0) | Used exclusively for offline segmentation benchmark validation (`pcg_core/segmentation/circor.py`). | Data files are excluded from Git tracking via `.gitignore`. Downloaded on-demand. |
| **PhysioNet Computing in Cardiology 2016** | Clifford et al., *"Classification of normal/abnormal heart sound recordings,"* Physiol. Meas. 2016 | Open Data Commons Attribution License (ODC-By v1.0) | Secondary benchmark for heart sound feature extraction. | Excluded from Git tracking. |

> [!IMPORTANT]
> **DATASET GOVERNANCE POLICY:**
> Commercial patient identifiable data is strictly barred from the repository. All PhysioNet records are de-identified open-access research benchmarks. Large audio files (`.wav`) are placed under `data/raw/` and `data/processed/`, which are enforced as untracked in `.gitignore`.
