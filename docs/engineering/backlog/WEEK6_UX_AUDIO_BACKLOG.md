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
- **Priority**: P2 (Visual / Layout Usability)
- **Component**: `software/frontend/src/components/SamplesView.tsx`, `FooterStatus.tsx`
- **Symptoms**: When scrolling to the very bottom of the specimen or recorded session list in `SamplesView`, the lowest card's action buttons (Verify, Manifest, Analyze, Audition, Replay) are partially obscured by the fixed bottom telemetry status bar (`h-9`).
- **Reproduction Steps**:
  1. Open AuscultaForge desktop app and navigate to **Auscultation Signals & Recorded Sessions** (`SamplesView`).
  2. Switch to **Recorded Acquisition Sessions** tab (or stay on **Curated Physiological Specimens**).
  3. Scroll all the way to the bottom.
  4. Observe that the bottom card's padding and delete/action buttons collide with the fixed status footer.
- **Root Cause**: The scrollable container `#samples-view` has `pb-8`, which is insufficient to clear the fixed-position `FooterStatus` component (`z-40`, height ~36px) plus window margins.
- **Remediation Plan**: Increase bottom padding on the main view scroll container to `pb-16` or `pb-20` (e.g. `className="... pb-20 ..."`).

---

### Item 2: "Browse Workstation Drives" Phrasing Ambiguity
- **ID**: `UX-BACKLOG-02`
- **Priority**: P3 (User Guidance & Phrasing)
- **Component**: `software/frontend/src/components/HomeView.tsx`
- **Symptoms**: In the local file drop area on the Home tab, the label reads *"Browse Workstation Drives"*. This leads users to believe it opens an internal filesystem tree or network drive mount viewer, whereas it simply triggers the standard native operating system file open dialog for audio files.
- **Reproduction Steps**:
  1. Navigate to the **Home** tab (`HomeView`).
  2. In the "Load Auscultation File" dropzone, observe the prominent button text: *"Browse Workstation Drives"*.
  3. Clicking the button opens the standard Windows Explorer file picker for `.wav` / `.mp3`.
- **Root Cause**: The label was an early design placeholder imitating CAD/enterprise tools.
- **Remediation Plan**: Update phrasing to **"Select Audio File (*.wav, *.mp3)"** or **"Browse Local Files"**, aligning with standard desktop user expectations.

---

### Item 3: Static `L-44100-RAW` Label Discrepancy
- **ID**: `UX-BACKLOG-03`
- **Priority**: P2 (Scientific Truthfulness & Demarcation) — **RESOLVED IN PATCH**
- **Component**: `software/frontend/src/components/LiveWorkspace.tsx`
- **Symptoms**: The Audacity-style full recording overview strip displayed a static badge labeled `L-44100-RAW`, even when playing a 4000 Hz CirCor research specimen or a 2000 Hz sensor stream.
- **Reproduction Steps**:
  1. Open `40058_AV.wav` (4000 Hz) in Local Audition.
  2. Inspect the label directly below `FULL RECORDING OVERVIEW (15.0s ARCHIVE)`.
  3. Notice it hardcoded `L-44100-RAW`.
- **Root Cause**: Hardcoded string literal in JSX line 1245 without interpolation of `sampleRate`.
- **Remediation Applied**: Updated to dynamic string `L-{sampleRate}-RAW` (e.g. `L-4000-RAW`). Verified by unit tests.

---

### Item 4: Frozen `REC 0.0s` Timer During Live Session Recording
- **ID**: `UX-BACKLOG-04`
- **Priority**: P2 (Recording Usability & Telemetry)
- **Component**: `software/pcg_app/state.py`, `software/frontend/src/components/Header.tsx`
- **Symptoms**: When the user starts a session recording by clicking "Record Session", the red recording indicator in `Header.tsx` displays `REC 0.0s` and stays frozen at `0.0s` for the entire duration of the recording, only updating to the final duration (e.g. `6.992s`) when stopped.
- **Reproduction Steps**:
  1. Connect a live stream or synthetic generator source.
  2. Click "Record Session".
  3. Observe that the red badge shows `REC 0.0s` with a pulsing dot, but the timer counter does not advance.
  4. Click "Stop". The session saves, and the log correctly states the final recorded sample count and elapsed seconds.
- **Root Cause**: In `software/pcg_app/state.py`, `make_recording_state_message` is only broadcasted twice: once upon `start_recording` (`elapsed_seconds=0.0`) and once upon `stop_recording`. During the active streaming loop, `recording_state` is never periodically broadcasted. The frontend only updated its `recordingElapsedSeconds` state on receiving `recording_state` WebSocket messages.
- **Remediation Plan**:
  - *Option A (Backend)*: In `StreamManager.stream_worker()`, broadcast `recording_state` every 500 ms while `recorder.is_recording` is active.
  - *Option B (Frontend)*: In `App.tsx`, record `recordingStartTimeRef.current = performance.now()` when `isRecording` becomes true, and run a 100 ms `setInterval` advancing `recordingElapsedSeconds`. Option B gives silky-smooth 10 Hz UI feedback without adding WebSocket message traffic.

---

### Item 5: Silent Manifest Export Notification
- **ID**: `UX-BACKLOG-05`
- **Priority**: P3 (Feedback & Confirmation)
- **Component**: `software/frontend/src/components/SamplesView.tsx`
- **Symptoms**: Clicking the **Manifest** button on a recorded session card downloads `manifest_<session_id>.json` via the browser's blob download anchor, but displays no confirmation toast in the application UI. Users are unsure whether the manifest was generated.
- **Reproduction Steps**:
  1. Navigate to **Recorded Acquisition Sessions** in `SamplesView`.
  2. Click **Manifest** on any session card.
  3. The file appears in Windows `Downloads` folder, but no toast or log appears in AuscultaForge.
- **Root Cause**: `handleExportManifestClick` silently created an `<a>` element without triggering `addToast` or `addLog`.
- **Remediation Plan**: Pass `addToast` / `addLog` to `SamplesView` or invoke a toast callback upon successful manifest generation: `addToast('Exported manifest: manifest_' + sessionId + '.json', 'success')`.

---

### Item 6: Version Identifier Clarification (`app_version: 2.0.0` vs Desktop `0.1.0-alpha.1`)
- **ID**: `UX-BACKLOG-06`
- **Priority**: P2 (Metadata & Traceability)
- **Component**: `software/pcg_core/recording.py`, `software/pcg_app/protocol.py`, `docs/engineering/release/`
- **Symptoms**: Session manifests exported from the application state list `app_version: "2.0.0"`, while the Tauri desktop client window header and `package.json` declare `0.1.0-alpha.1`. This can confuse academic reviewers and clinical evaluators.
- **Reproduction Steps**:
  1. Open an exported `manifest.json`.
  2. Inspect top-level keys: `"app_version": "2.0.0"`.
  3. Compare with window header: `"AuscultaForge Desktop v0.1.0-alpha.1"`.
- **Root Cause**: `pcg_core` was versioned independently as the core DSP engine (`2.0.0`), while the Tauri desktop wrapper started at `0.1.0-alpha.1`.
- **Remediation Plan**: Split the manifest field into explicit distinct keys:
  - `dsp_engine_version: "2.0.0"`
  - `desktop_client_version: "0.1.0-alpha.1"`
  - `schema_version: "1.1.0"` (backward-compatible upgrade).

---

### Item 7: Playback Duration & Source Demarcation Confusion
- **ID**: `UX-BACKLOG-07`
- **Priority**: P1 (Core Audio / DSP Architecture) — **RESOLVED IN PATCH**
- **Component**: `software/frontend/src/App.tsx`, `audioEngine.ts`, `LiveWorkspace.tsx`, `SamplesView.tsx`
- **Symptoms**:
  1. Playing a session in backend replay displayed moving waveforms but gave no speaker sound.
  2. Pressing PLAY produced ~0.5s of wind/static noise and then cut off.
  3. Opening a local WAV while backend replay was active caused the header to revert to the old session name.
- **Root Cause**:
  - Backend streaming operates on 25 Hz decimated telemetry points; it does NOT stream PCM audio over WebSocket.
  - When in backend streaming, `handleTogglePlay` mistakenly called `audioEngine.play()` with a stale buffer.
  - `unsubState` allowed incoming backend `is_streaming: true` messages to overwrite `sourceType` and wipe local audition state.
  - WebAudio Channel 0 was pre-filtered in software and then double-filtered through WebAudio Biquad nodes.
- **Remediation Applied**:
  - Implemented `GET /api/sessions/{session_id}/wav` endpoint in FastAPI.
  - Added **Audition** button next to **Replay** on recorded session cards for true WebAudio speaker playback.
  - Removed double filtering in `audioEngine.ts`.
  - Added `audioEngine.clear()` to purge buffers upon switching to backend streams.
  - Strictly isolated Local Audition in `unsubState` from backend telemetry events.
  - Added clear, truthful badges in `LiveWorkspace.tsx`: `SPEAKER AUDITION` vs `TELEMETRY (SPEAKER: LOCAL AUDITION)`.
  - Added 8 automated regression tests in `audio_playback_regression.test.ts`.

---

## 3. Implementation Schedule & Roadmap

| Item ID | Title | Priority | Status in Current Patch | Target Milestone |
|---|---|:---:|:---:|:---:|
| `UX-BACKLOG-07` | Audio Playback & Source State Synchronization | **P1** | **FIXED & TESTED** | Week 6 Release Candidate |
| `UX-BACKLOG-03` | Dynamic Sample Rate Badge (`L-{fs}-RAW`) | **P2** | **FIXED & TESTED** | Week 6 Release Candidate |
| `UX-BACKLOG-04` | Live Recording Timer Progress (`REC Xs`) | **P2** | Documented | Sprint 7.1 |
| `UX-BACKLOG-01` | Specimen Archives Bottom Card Overlap | **P2** | Documented | Sprint 7.1 |
| `UX-BACKLOG-06` | Version Discrepancy Demarcation in Manifest | **P2** | Documented | Sprint 7.1 |
| `UX-BACKLOG-02` | File Picker Phrasing ("Browse Audio Files") | **P3** | Documented | Sprint 7.1 |
| `UX-BACKLOG-05` | Manifest Export Toast Notification | **P3** | Documented | Sprint 7.1 |

---

*This backlog serves as the authoritative UX tracking document for AuscultaForge desktop client stabilization.*
