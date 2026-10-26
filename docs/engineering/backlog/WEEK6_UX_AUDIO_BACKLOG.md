# AuscultaForge — Week 6 UX & Audio Backlog (Post-Acceptance Audit)

**Date**: 2026-10-26  
**Status**: ACTIVE / TRIAGED  
**Scope**: Desktop UX, Playback Synchronization, Telemetry Truthfulness, and Manifest Provenance  
**Author**: Antigravity Pair-Programming Agent & Engineering Team

---

## 1. Executive Summary

During manual acceptance testing on a native Windows release build using real CirCor acoustic phonocardiograms (`40058_AV.wav`, 4000 Hz, 11.888s) and recorded session archives (`session_20261026_121726_530cde89`, 27968 samples, 6.992s), primary data integrity functions (physical G1 transducer acquisition, bounded WAV upload, SHA-256 verification, manifest generation, and session replay) were successfully confirmed.

However, several UX inconsistencies, state synchronization glitches, and playback ergonomics issues were observed. This backlog document formalizes each observation with priority, reproduction steps, technical root cause, and implementation roadmap.

---

## 2. Prioritized Bug & Improvement Catalog

### Item 1: Specimen Archives Bottom Card Overlap with Status Bar
- **ID**: `UX-BACKLOG-01`
- **Priority**: P2 (Visual / Layout Usability) — **RESOLVED & VERIFIED**
- **Component**: `software/frontend/src/components/SamplesView.tsx`, `FooterStatus.tsx`
- **Symptoms**: When scrolling to the very bottom of the specimen or recorded session list in `SamplesView`, the lowest card's action buttons (Verify, Manifest, Analyze, Audition, Replay) were partially obscured by the fixed bottom telemetry status bar (`h-7`).
- **Remediation Applied**: Increased bottom padding on `#samples-view` scroll container from `pb-8` to `pb-28` (112px). All card buttons now remain fully visible and completely clear of the fixed bottom status footer with generous clearance.

---

### Item 2: "Browse Workstation Drives" Phrasing Ambiguity
- **ID**: `UX-BACKLOG-02`
- **Priority**: P3 (User Guidance & Phrasing) — **RESOLVED & VERIFIED**
- **Component**: `software/frontend/src/components/HomeView.tsx`
- **Symptoms**: In the local file drop area on the Home tab, the label read *"Browse Workstation Drives"*. Furthermore, users reported clicking this or the adjacent button and navigating to Archives.
- **Root Cause**: The label was a non-button `<span>` inside `#drop-zone`, and the banner immediately below had an identically worded button *"Browse Starter Signals & Sessions"* triggering `onNavigate('samples')`.
- **Remediation Applied**:
  - Replaced the `<span>` with an explicit, accessible button: `<button id="browse-local-files-btn" type="button" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>` with clear label `"Choose Local Audio File (*.wav, *.mp3)"`.
  - Renamed the reference archive banner button to `"Open Reference Corpus & Sessions"` (`data-testid="open-samples-archive-btn"`), completely eliminating the ambiguous word collision.
  - Added unit regression tests in `ux_stabilization_regression.test.ts` verifying click event isolation.

---

### Item 3: Static `L-44100-RAW` Label Discrepancy
- **ID**: `UX-BACKLOG-03`
- **Priority**: P2 (Scientific Truthfulness & Demarcation) — **RESOLVED & VERIFIED**
- **Component**: `software/frontend/src/components/LiveWorkspace.tsx`
- **Symptoms**: The Audacity-style full recording overview strip displayed a static badge labeled `L-44100-RAW`, even when playing a 4000 Hz CirCor research specimen or a 2000 Hz sensor stream.
- **Remediation Applied**: Updated to dynamic string `L-{sampleRate}-RAW` (e.g. `L-4000-RAW`). Verified by unit tests.

---

### Item 4: Frozen `REC 0.0s` Timer During Live Session Recording
- **ID**: `UX-BACKLOG-04`
- **Priority**: P2 (Recording Usability & Telemetry) — **RESOLVED & VERIFIED**
- **Component**: `software/pcg_app/state.py`, `software/pcg_core/recording.py`, `software/frontend/src/App.tsx`, `Header.tsx`
- **Symptoms**: When starting a session recording, the red recording indicator in `Header.tsx` displayed `REC 0.0s` and stayed frozen at `0.0s` until stopped.
- **Root Cause**: Backend only sent `recording_state` at start (`elapsed=0.0`) and stop; no periodic telemetry updates were dispatched during streaming.
- **Remediation Applied**:
  - Added `elapsed_seconds`, `total_blocks`, and `source` properties to `SessionRecorder` in `software/pcg_core/recording.py`, derived strictly from `total_samples / sample_rate_hz`.
  - In `software/pcg_app/state.py`, implemented periodic (5 Hz / 200ms) `recording_state` broadcasts during active sample block dispatch and device packet ingestion.
  - Pausing streaming immediately freezes `elapsed_seconds` because no new samples are added. Resuming streaming resumes time counting.
  - In `App.tsx`, updated `unsubRec` to cleanly maintain state transition logging and continuous elapsed time display.
  - Verified with Python unit tests (`test_stream_manager_recording_elapsed_broadcast_and_pause`) and frontend tests.

---

### Item 5: Silent Manifest Export Notification
- **ID**: `UX-BACKLOG-05`
- **Priority**: P3 (Feedback & Confirmation) — **RESOLVED & VERIFIED**
- **Component**: `software/frontend/src/components/SamplesView.tsx`, `App.tsx`
- **Symptoms**: Clicking the **Manifest** button on a recorded session card downloaded `manifest_<session_id>.json` without displaying any confirmation toast or diagnostic log in AuscultaForge.
- **Remediation Applied**: Added `onToast` and `onLog` props to `SamplesViewProps`. `handleExportManifestClick` now emits informative success toasts (`Manifest exported: manifest_<id>...json`) and diagnostic log entries, as well as warning toasts if manifest generation fails.

---

### Item 6: Version Identifier Clarification (`app_version: 2.0.0` vs Desktop `0.1.0-alpha.1`)
- **ID**: `UX-BACKLOG-06`
- **Priority**: P2 (Metadata & Traceability) — **RESOLVED & VERIFIED**
- **Component**: `software/pcg_core/recording.py`, `software/pcg_app/app.py`, `software/pcg_app/state.py`
- **Symptoms**: Session manifests listed `app_version: "2.0.0"`, while the Tauri desktop client declared `0.1.0-alpha.1`, creating confusion between DSP engine and desktop client versions.
- **Remediation Applied**:
  - Demarcated explicit version keys in `SessionMetadata` and `export_session_manifest`:
    - `dsp_engine_version: "2.0.0"`
    - `desktop_client_version: "0.1.0-alpha.1"`
    - `app_version: "2.0.0"` (retained as backward-compatible alias).
  - Maintained full backward compatibility in `SessionMetadata.from_dict` when reading older v1 manifests.
  - Updated `/api/health` to explicitly report `dsp_engine_version` and `desktop_client_version`.
  - Verified with `test_session_manifest_version_disambiguation` and `test_backward_compatible_manifest_reading`.

---

### Item 7: Playback Duration & Source Demarcation Confusion
- **ID**: `UX-BACKLOG-07`
- **Priority**: P1 (Core Audio / DSP Architecture) — **RESOLVED & VERIFIED**
- **Component**: `software/frontend/src/App.tsx`, `audioEngine.ts`, `LiveWorkspace.tsx`, `SamplesView.tsx`
- **Symptoms**: Backend DSP replay animated waveforms without speaker sound; pressing PLAY generated ~0.5s ghost cutoff noise; local WAV import was stomped by old session names.
- **Remediation Applied**: Implemented `GET /api/sessions/{session_id}/wav`, added dedicated **Audition** button alongside **Replay**, eliminated WebAudio double-filtering, added `audioEngine.clear()`, and insulated Local Audition from backend telemetry events.

---

## 3. Implementation Schedule & Resolution Status

| Item ID | Title | Priority | Resolution Status | Verified Milestone |
|---|---|:---:|:---:|:---:|
| `UX-BACKLOG-07` | Audio Playback & Source State Synchronization | **P1** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |
| `UX-BACKLOG-03` | Dynamic Sample Rate Badge (`L-{fs}-RAW`) | **P2** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |
| `UX-BACKLOG-04` | Live Recording Timer Progress (`REC Xs`) | **P2** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |
| `UX-BACKLOG-01` | Specimen Archives Bottom Card Overlap | **P2** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |
| `UX-BACKLOG-06` | Version Discrepancy Demarcation in Manifest | **P2** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |
| `UX-BACKLOG-02` | File Picker Phrasing ("Choose Local Audio File") | **P3** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |
| `UX-BACKLOG-05` | Manifest Export Toast Notification | **P3** | **RESOLVED & VERIFIED** | Week 6 Sprint Closeout |

---

*All seven UX and audio backlog items have been resolved, covered by automated regression tests, and verified in the production release candidate.*

