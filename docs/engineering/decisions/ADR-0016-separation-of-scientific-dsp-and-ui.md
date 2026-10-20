# ADR-0016: Architectural Boundary — Separation of Scientific DSP and UI
**Status:** `ACCEPTED`  
**Date:** 2026-09-26  
**Deciders:** Module C (Ege)  
**Technical Area:** Software Architecture & Modularity

## Context & Problem Statement
In scientific software platforms, algorithm code frequently becomes tightly coupled to application frameworks, web servers, or graphical widgets. This coupling prevents algorithms from being run in headless batch scripts, automated unit tests, or continuous integration environments.

## Decision Drivers
* Headless testability: Core DSP routines must execute and be tested without launching web servers or GUI browsers.
* Portability: Core mathematics should run on any system supporting standard Python, NumPy, and SciPy.
* Modularity: UI redesigns or framework changes must not impact verified signal processing algorithms.

## Considered Alternatives
1. **Monolithic Application Structure:** Embedding DSP filters directly inside FastAPI route handlers or React client hooks.
   * *Critical Flaw:* Impossible to unit-test mathematical routines without spinning up mock HTTP/WebSocket clients.
2. **Strict Layer Separation (`pcg_core` vs `pcg_app` vs `frontend`):**
   * `pcg_core`: Pure Python scientific library containing zero web or UI imports.
   * `pcg_app`: Application bridge exposing endpoints and routing streams.
   * `frontend`: User interface presentation layer.

## Decision
Enforced **Strict Layer Separation**:
* `pcg_core` has zero imports of `fastapi`, `starlette`, `uvicorn`, or web frameworks.
* All mathematical models (`StreamingBandpass`, `RollingBuffer`, `PhantomStimulusEngine`, `SpringerHSMM`, `MetrologyRunner`) live exclusively inside `software/pcg_core/`.
* `pcg_app` imports from `pcg_core`, but `pcg_core` never imports from `pcg_app`.

## Consequences & Trade-Offs
* **Positive:** Clean architecture; 394 automated tests execute headlessly in 16.42 seconds without network or UI dependencies.
* **Negative:** Requires explicit data model transformations (`SampleBlock` $\to$ WebSocket JSON frame) at the application boundary.
