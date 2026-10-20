# AuscultaForge — Documentation Maintenance & Governance Policy

This document defines the official engineering workflow, quality standards, and maintenance rules for extending and preserving the AuscultaForge Engineering Intelligence & Defense System across future sprints, Semester II development, and academic milestones.

---

## 1. Documentation Philosophy & Cardinal Principles

1. **Grounded in Verified Code:** Documentation must reflect the actual integrated codebase, not aspirational designs or unmerged branches.
2. **Strict Provenance Classification:** Every claim, diagram, formula, and performance figure must carry an explicit source-of-truth status label.
3. **Zero Fabricated Evidence:** Never record simulated test results as physical hardware results. Never claim PASS on an unexecuted physical test.
4. **Non-Clinical Boundary:** Maintain strict adherence to non-diagnostic acoustic metrology. Do not introduce clinical medical diagnostic claims.
5. **Separation of Sprints and Weeks:** Always distinguish agile software development cycles (Sprints 01–10) from the academic course calendar (Weeks 01–14).

---

## 2. Source-of-Truth Classification System

When authoring or updating technical documents, tag major assertions and architectural interfaces using the following standardized taxonomy:

| Status Tag | Operational Definition | Acceptable Evidence |
| :--- | :--- | :--- |
| `CODE_VERIFIED` | Directly inspected and confirmed in the merged codebase. | Merged source file path and line numbers. |
| `TEST_VERIFIED` | Covered by automated tests observed passing in the active session. | Pytest or Vitest output with test function name. |
| `GIT_VERIFIED` | Backed by historical Git commits, pull requests, or release tags. | Commit SHA, PR number, or Git tag. |
| `DOCUMENTED_PROPOSAL` | Specified in design proposals or SDPs, but not yet implemented. | SDP or RFC document reference. |
| `HARDWARE_UNVERIFIED` | Requires physical bench execution with physical MCU/sensors. | Laboratory protocol waiting on hardware bringup. |
| `INFERRED` | Engineering deduction based on design constraints or standards. | Explicit engineering rationale provided. |
| `UNKNOWN` | Source evidence is absent or contradictory; needs future research. | Explicit knowledge gap acknowledgement. |

---

## 3. Pull Request Maintenance Workflow

When submitting a Pull Request that introduces or alters functionality, the author must execute the following documentation checklist:

```
+-----------------------------------------------------------------------------------------+
|                               PULL REQUEST DOCUMENTATION WORKFLOW                       |
+-----------------------------------------------------------------------------------------+
| 1. Code / Test Changes                                                                  |
|    * Write feature or bugfix                                                            |
|    * Run pytest, npm run lint, vitest, and C bench parity                               |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-----------------------------------------------------------------------------------------+
| 2. Impact Analysis & Documentation Updates                                              |
|    * If routes changed: Update docs/engineering/code-atlas/FASTAPI_API_REFERENCE.md      |
|    * If models changed: Update docs/engineering/code-atlas/CROSS_LANGUAGE_DATA_CONTRACTS|
|    * If DSP altered: Update docs/engineering/science/ using ALGORITHM_RECORD template    |
|    * If architecture altered: Submit new ADR in docs/engineering/decisions/             |
|    * If tests altered: Update docs/engineering/verification/TEST_ATLAS.md               |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-----------------------------------------------------------------------------------------+
| 3. Quality Control & Link Verification                                                  |
|    * Verify relative Markdown links                                                     |
|    * Ensure no absolute URI schemes or drive letters appear                             |
|    * Fill out docs/engineering/templates/PR_ENGINEERING_RECORD.md                       |
+-----------------------------------------------------------------------------------------+
```

### 3.1 Route and API Contract Updates
- If a route in `software/pcg_app/app.py` is added, modified, or removed:
  1. Inspect the route signature and response models programmatically.
  2. Update `docs/engineering/code-atlas/FASTAPI_API_REFERENCE.md`.
  3. Update `software/frontend/src/api/client.ts` to reflect TypeScript signature changes.
  4. Ensure bringup checklists (`docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`) match the exact endpoint paths.

### 3.2 Signal Processing & Science Updates
- When introducing a new filter, spectral estimator, or quality metric:
  1. Use the [ALGORITHM_RECORD](templates/ALGORITHM_RECORD.md) template.
  2. Place the technical specification in the relevant document under `docs/engineering/science/`.
  3. Include the exact mathematical formula, unit definitions, sampling constraints, and test references.
  4. Cross-reference relevant citations in `docs/research/PCG_LITERATURE_REGISTRY.md`.

### 3.3 Architectural Decisions
- When a major architectural fork or technology selection is made:
  1. Create a new Architecture Decision Record under `docs/engineering/decisions/`.
  2. Use the sequential numbering format: `ADR-XXXX-<descriptive-slug>.md`.
  3. Follow the structure in [ADR_TEMPLATE](templates/ADR_TEMPLATE.md).
  4. Update the ADR Index table in `docs/engineering/decisions/README.md` and [KNOWLEDGE_COVERAGE_MATRIX.md](KNOWLEDGE_COVERAGE_MATRIX.md).

### 3.4 Verification & Test Updates
- When test suites expand:
  1. Record actual newly observed execution numbers (`pytest` count, pass rate, runtime).
  2. Update `docs/engineering/verification/TEST_ATLAS.md`.
  3. Do not overwrite historical baselines without noting the baseline Git commit SHA.

---

## 4. Module Ownership and Attribution Guidelines

To ensure academic and project integrity, changes to the documentation must respect team module boundaries:

- **Module A (Acoustic Transduction & Phantom):** Primary author: **Kaan**. Covers mechanical housing, stethoscope acoustics, silicone phantoms, transducer selection, and SPL calibration.
- **Module B (Embedded Hardware & Firmware):** Primary author: **Ozan**. Covers ESP32-S3 hardware bringup, I2S DMA, USB CDC-ACM firmware drivers, and embedded FreeRTOS tasks.
- **Module C (Host Software, DSP & System Integration):** Primary author: **Ege**. Covers host Python application, StreamManager, DSP pipelines, FastAPI, WebSockets, React UI, test automation, and cross-module integration.

*Rule:* Cross-module contributions should be coordinated and documented in the PR Engineering Record with appropriate co-author credits.

---

## 5. Automated Documentation Verification Checks

Before submitting any documentation pull request, run the following automated verification checks:

1. **Relative Link Integrity:** Ensure all Markdown links use standard relative syntax and resolve to existing repository files.
2. **No Local Machine Paths:** Verify that no local absolute paths (e.g., Windows drive letters or local file URI schemes) are committed.
3. **Mermaid Diagram Syntax:** Ensure Mermaid diagram blocks use valid syntax and quoted node strings where special characters appear.
4. **Code Compilation & Parity:**
   ```bash
   # Verify backend tests
   pytest
   
   # Verify frontend types and linting
   cd software/frontend && npm run lint && npm run test && npm run build
   
   # Verify C golden vector parity
   pytest software/tests/test_c_golden_vectors.py
   ```

---

## 6. Deprecation and Archival Policy

- Deprecated architectures or superseded proposals must not be deleted.
- Instead, update the document header with:
  ```markdown
  > [!WARNING]
  > **SUPERSEDED / DEPRECATED:** This document describes an earlier architecture superseded by a later ADR. Retained for historical traceability.
  ```
- This preserves the audit trail required for academic defense and project chronicle reconstruction.
