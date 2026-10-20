# AuscultaForge — Complete System Reproducibility & Verification Guide
**Document ID:** `AF-VERIF-REPRODUCIBILITY-V01`  
**Classification:** `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Target Environment:** Windows 10 / 11 (PowerShell)  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. System Requirements & Prerequisites

To reproduce all automated test suites, build artifacts, and live application workstations from a clean checkout, the following toolchains must be installed on the host computer:

| Dependency | Minimum Version | Verified Version | Role in Project | Installation Verification Command |
|---|---|---|---|---|
| **Python** | 3.11.0+ | 3.11.9 (64-bit) | Backend, DSP, Metrology, Tests | `python --version` |
| **Node.js** | 18.0.0+ | 20.18.0 (LTS) | React Desktop Frontend, Vite | `node --version` |
| **npm** | 9.0.0+ | 10.8.2 | Frontend Package Manager | `npm --version` |
| **GCC (MinGW)** | 9.0+ | 16.2.0 (w64devkit) | Portable C11 Golden Vectors | `gcc --version` |
| **Git** | 2.30.0+ | 2.45.2.windows.1 | Version Control & Provenance | `git --version` |

---

## 2. Step-by-Step Environment Setup

Execute the following commands in **Windows PowerShell** from the cloned repository root:

### Step 2.1: Python Virtual Environment Setup
```powershell
# In repository root (ausculta-forge/):
python -m venv .venv

# Activate the virtual environment:
.\.venv\Scripts\Activate.ps1

# Upgrade pip and packaging tools:
python -m pip install --upgrade pip

# Install pinned Python dependencies:
pip install -r software/requirements.txt

# Install software packages in editable development mode:
pip install -e ./software
```

### Step 2.2: Frontend Node Modules Setup
```powershell
# Navigate to frontend directory:
cd software/frontend

# Install JavaScript/TypeScript dependencies:
npm install

# Return to repository root:
cd ../..
```

---

## 3. Automated Test Execution Guide

### 3.1 Run Central Python Pytest Suite (394 Tests)
```powershell
# Execute all 37 test modules from repository root:
.\.venv\Scripts\pytest.exe

# Expected Result:
# ======================= 394 passed, 1 warning in ~16s =======================
```

### 3.2 Run Frontend Verification (Lint, Unit Tests & Production Build)
```powershell
cd software/frontend

# 1. Run TypeScript compiler type-check (must return 0 errors):
npm run lint

# 2. Run frontend mathematical and telemetry unit tests:
npm test

# 3. Verify production Vite bundle build:
npm run build

# Return to root:
cd ../..
```

### 3.3 Compile & Verify Portable C Golden Vectors
```powershell
# 1. Navigate to C golden vectors tool directory:
cd tools/c_golden_vectors

# 2. Compile portable C11 generator using GCC:
gcc -std=c11 -Wall -Wextra -pedantic -o golden_gen.exe golden_generator.c -lm

# 3. Generate binary and CSV reference fixtures:
.\golden_gen.exe

# 4. Return to root:
cd ../..

# 5. Run Python automated bit-exact parity test:
.\.venv\Scripts\pytest.exe software/tests/test_c_golden_vectors.py
```

---

## 4. Launching the Live Application Workstation

To run the interactive desktop application locally:

### Step 4.1: Start Python FastAPI Backend Server
```powershell
# Option A: Recommended CLI server entrypoint (in root):
.\.venv\Scripts\python.exe -m pcg_app.server --host 127.0.0.1 --port 8000

# Option B: Direct Uvicorn launch using application factory:
.\.venv\Scripts\python.exe -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```
* Status & Health Check: [http://127.0.0.1:8000/api/status](http://127.0.0.1:8000/api/status)
* Interactive Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Step 4.2: Start React Desktop Frontend
Open a second PowerShell terminal:
```powershell
cd software/frontend
npm run dev
```
* Open your web browser at: [http://127.0.0.1:3000](http://127.0.0.1:3000)

---

## 5. Command-Line Simulation & Metrology Runners

AuscultaForge provides reproducible CLI utilities for headless research:

```powershell
# 1. Run synthetic streaming pipeline demonstration:
python -m pcg_core.demo

# 2. Execute Virtual Bench all-scenario automated sweep:
python -c "from pcg_app.virtual_bench import VirtualBench; print(VirtualBench().run_all_scenarios())"

# 3. Run automated 6-measurement metrology campaign and generate Markdown report:
python -m pcg_core.metrology.cli --output-dir experiments/output/
```
All generated report artifacts are saved in structured JSON, CSV, and Markdown formats.
