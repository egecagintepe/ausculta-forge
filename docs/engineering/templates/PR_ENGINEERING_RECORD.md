# AuscultaForge — PR Engineering Record Template

> **Instructions:** Copy this template into your PR description or include it as a markdown record when introducing non-trivial architectural, DSP, firmware, or host software changes.

---

## PR Summary & Metadata

- **PR Title:** `[Module / Subsystem] Brief summary of change`
- **Target Branch:** `main` (or designated integration branch)
- **Author / Module Owner:** [Kaan (Module A) / Ozan (Module B) / Ege (Module C)]
- **Reviewers:** [Team members / Advisors]
- **Associated Issue(s):** `#XX`
- **Classification:** `[CODE_VERIFIED / TEST_VERIFIED / DOCUMENTED_PROPOSAL / HARDWARE_UNVERIFIED]`

---

## 1. Context and Problem Statement

*Explain the engineering motivation for this change. What requirement, limitation, bug, or academic milestone does this PR address?*

---

## 2. Proposed Architectural & Code Changes

*Detail the technical implementation. List modified subsystems, new classes, data models, or protocol changes.*

| File / Component | Nature of Modification | Rationale |
| :--- | :--- | :--- |
| `software/...` | Added / Modified / Removed | |
| `docs/...` | Updated documentation | |

---

## 3. Data Contracts & Cross-Language Impact

- **Route Impact:** *Did any FastAPI routes in `software/pcg_app/app.py` change? (Yes/No)*
  - *If Yes, list changes and note update to `FASTAPI_API_REFERENCE.md`.*
- **Protocol Impact:** *Did any packet headers, serialization rules, or C/Python binary formats change? (Yes/No)*
  - *If Yes, note update to `CROSS_LANGUAGE_DATA_CONTRACTS.md` and C generator parity.*
- **Frontend Impact:** *Did any WebSocket messages or REST models change in `software/frontend/`? (Yes/No)*

---

## 4. Verification and Evidence Observed

*Record the exact automated test evidence observed during this PR's verification session.*

- [ ] **Python Pytest:**
  - Command: `pytest`
  - Observed Result: `X passed, Y warnings in Z.ZZs`
- [ ] **Frontend Verification:**
  - Commands: `npm run lint`, `npm run test`, `npm run build`
  - Observed Result: `0 errors, X tests passed, clean build`
- [ ] **C Golden Vector Parity:**
  - Command: `pytest software/tests/test_c_golden_vectors.py`
  - Observed Result: `PASS (6/6 vectors bit-exact)`
- [ ] **Hardware Bringup:**
  - Status: `[HARDWARE_UNVERIFIED / BENCH_VERIFIED]`
  - Prerequisites / Equipment:

---

## 5. Non-Clinical Metrology Boundary Confirmation

- [ ] I confirm that this pull request adheres strictly to the non-clinical acoustic engineering metrology scope and introduces no medical diagnostic claims.

---

## 6. Academic Traceability

- **Syllabus / SDP Section:** *Which milestone or requirement does this satisfy?*
- **Potential Defense Examination Question:** *What question might an examiner ask about this implementation?*
