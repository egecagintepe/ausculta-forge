# AuscultaForge — Week 6 Audio Fix Release Build & Acceptance Report

**Date**: 2026-10-26  
**Build Profile**: Production Windows x64 Native Release & NSIS Installer  
**Source Commit**: `ccc98eb54280e10b975a757be8d58ec68689411d`  
**Author**: AuscultaForge Automated Engineering & Delivery Pipeline  
**Overall Status**: VERIFIED — ACCEPTANCE GATE PENDING USER SPEAKER AUDITION  

---

## 1. Executive Summary

Following the diagnosis and resolution of audio audition and source synchronization issues (WebAudio double-filtering, session replay ghost sounds, missing session WAV endpoint, and state stomping), a complete **clean production Windows release** was rebuilt, packaged, and verified end-to-end.

The release incorporates:
1. Re-packaged standalone Python backend (`auscultaforge-backend.exe`) via PyInstaller, containing the new `GET /api/sessions/{session_id}/wav` endpoint.
2. Production frontend compilation (`vite build`) and native Tauri application packaging (`makensis`).
3. Complete multi-layer test suite execution across Python (full suite + 48 kHz performance + real PCG manifest), Rust, and frontend TypeScript.
4. Isolated runtime smoke testing in clean `%APPDATA%` / `%LOCALAPPDATA%` environments.

---

## 2. Release Artifacts & Cryptographic Provenance

| Artifact | Relative Path | Size (Bytes) | SHA-256 Checksum | Build Time (UTC) |
|---|---|---:|---|---|
| **Native Executable** | `software/frontend/src-tauri/target/release/auscultaforge-desktop.exe` | 9,139,200 | `99e1000bf053c6458b122ead8489f7c8fb68cc78660ca30681e6a703993fb812` | 2026-10-26 14:16:44 |
| **NSIS Installer** | `software/frontend/src-tauri/target/release/bundle/nsis/AuscultaForge_0.1.0-alpha.1_x64-setup.exe` | 164,521,275 | `29aac14209df7e1c82d1fe0bdd0a3c1076fa754db3a466b79e1920367e1ad2f4` | 2026-10-26 14:16:44 |
| **Packaged Backend** | `software/dist_backend/auscultaforge-backend/auscultaforge-backend.exe` | 58,493,866 | `9605b4df6966fe7a66e004cf3623f5db8f19216c8cde9d1d90f9a8b65429e7c5` | 2026-10-26 14:06:19 |

> [!NOTE]
> All previous installer archives (`e90785e-nsis-setup.exe`, `gui-tested-59d773e-setup.exe`, `intermediate-574b52e-setup.exe`, `pre-audiofix-release-setup.exe`) and original PCG dataset fixtures have been strictly preserved.

---

## 3. Test & Verification Matrix

### 3.1. Full Python Test Suite
- **Command**: `.venv\Scripts\pytest.exe software/tests research/ml/tests -v`
- **Result**: **583 passed, 1 skipped, 2 warnings** (Duration: 59.80s).
- **Skipped Test**: `test_real_recording_display_filters_and_replay` when run without manifest environment variable (intentional placeholder design).

### 3.2. 48 kHz Streaming Performance Test Suite
- **Command**: `.venv\Scripts\pytest.exe software/tests/test_streaming_performance.py -v`
- **Result**: **6 passed, 0 failed** (Duration: 12.13s).
- **Checks Verified**:
  - `test_48khz_continuous_throughput_and_recording_preservation`: 240,128 samples continuous ingestion at > 2.0x real-time speed, 0 dropped samples, 0 MCU sequence gaps.
  - `test_slow_client_backpressure_does_not_corrupt_recording_or_mcu_stats`: PASSED.
  - `test_display_aggregator_bounded_memory`: PASSED.
  - `test_peak_preserving_decimation_retains_transient_spikes`: PASSED.
  - `test_adaptive_welch_spectral_frame_48khz`: PASSED.
  - `test_pause_and_resume_resets_aggregator_cleanly`: PASSED.

### 3.3. Real PCG Manifest Acceptance Tests
- **Environment**: `AUSCULTA_PCG_MANIFEST=data/raw/week6_real_pcg_20261026/manifest.json`
- **Command**: `.venv\Scripts\pytest.exe software/tests/test_real_pcg_acceptance.py -v`
- **Result**: **7 passed, 0 failed** (Duration: 7.08s).
- **Records Tested**:
  - `test_wav_selection_rate_source_reset_and_recording_origin[2000]`: PASSED.
  - `test_wav_selection_rate_source_reset_and_recording_origin[4000]`: PASSED.
  - `C1` (`40058_AV.wav`, CirCor 4000 Hz, 47,552 samples): PASSED.
  - `C2` (`24160_MV.wav`, CirCor 4000 Hz, 90,368 samples): PASSED.
  - `C3` (`49568_PV.wav`, CirCor 4000 Hz, 113,792 samples): PASSED.
  - `C4` (`49627_TV.wav`, CirCor 4000 Hz, 127,360 samples): PASSED.
  - `P1` (`a0001.wav`, PhysioNet CinC 2000 Hz, 71,332 samples): PASSED.

### 3.4. Rust Unit Tests
- **Command**: `cargo test` in `software/frontend/src-tauri`
- **Result**: **6 passed, 0 failed** (Duration: 1.73s).
- **Checks Verified**: Handshake deserialization, missing port validation, malformed JSON rejection, process command resolution, live process supervision.

### 3.5. Frontend TypeScript Lint & Regression Suites
- **Lint**: `npm run lint` (`tsc --noEmit`) -> **0 errors, clean**.
- **Tests**: `npm test` -> **8 test suites passed**:
  1. `live_workspace_math.test.ts`: 4 passed.
  2. `scientific_ui_truth.test.ts`: 11 passed.
  3. `device_first_contact.test.ts`: passed.
  4. `acquisition_stop_gate.test.ts`: passed.
  5. `spectral_history.test.ts`: passed.
  6. `file_audio_import.test.ts`: passed.
  7. `filter_transfer_response.test.ts`: passed.
  8. `audio_playback_regression.test.ts`: **8 passed**:
     - Real CirCor `40058_AV.wav` (4000 Hz, 11.888s) decoded accurately.
     - Play -> Seek -> Pause -> Play -> Stop lifecycle verified.
     - Volume & Mute verified.
     - WebAudio natural EOF handling without premature cutoffs verified.
     - `AudioEngine.clear()` purges buffers and prevents ghost audio.
     - Single-filter direct routing verified (no double filtering).
     - Exact sample-rate and duration demarcation verified (2 kHz / 4 kHz / 6.992s session / 15s window).
     - Local Audition strictly insulated from rogue backend stream events.

---

## 4. Standalone Packaged Backend & Endpoint Verification

The standalone packaged executable `auscultaforge-backend.exe` was launched directly and verified via `verify_packaged_backend_wav.py`:
1. Ephemeral port dynamic allocation and token generation: PASSED.
2. `GET /api/health`: Returned `{"status": "ok", "app": "AuscultaForge", "version": "0.1.0-alpha.1"}`.
3. `GET /api/sessions/{session_id}/wav`:
   - Valid session: Returned HTTP 200, Content-Type: `audio/wav`, exact 8,044 bytes, SHA-256 match.
   - Non-existent session: Returned HTTP 404 Not Found.
   - Malformed/traversal session ID (`bad..session`): Returned HTTP 400 Bad Request.

---

## 5. Isolated Native Tauri Runtime Acceptance Test

Using `test_native_release_audiofix.py`, the native production `auscultaforge-desktop.exe` was run in isolated test directories (`gui-audiofix-appdata` and `gui-audiofix-localappdata`):
1. **Child Process Supervision**: Tauri desktop automatically spawned `auscultaforge-backend.exe`, waited for `handshake.json`, and established authenticated communication.
2. **Real PCG WAV Upload**: `POST /api/stream/upload_source_wav` with `40058_AV.wav` (4000 Hz, 11.888s, 47,552 samples) succeeded; sample rate and samples recorded accurately.
3. **Session Recording**: Captured live audio blocks to a new session (`session_20261026_144118_3056b0a9`).
4. **Session WAV Endpoint via Tauri**: `GET /api/sessions/{session_id}/wav` served the newly recorded WAV (15,930 bytes, audio/wav).
5. **State Stomping & Source Switching**:
   - `realtime_wav` -> `session` replay: active source transitioned to session.
   - `session` -> `synthetic_dev`: session disassociated.
   - `synthetic_dev` -> `realtime_wav` (`40058_AV.wav`): active source restored cleanly to `Replay: 40058_AV.wav` with 4000 Hz; old session header did **not** persist.
6. **Process Termination**: Desktop window closure cleanly terminated both desktop and child backend processes.

---

## 6. GUI New Behaviors Checklist

- [x] **Specimen Archives → Recorded Sessions Audition Button**: Dedicated `Audition` button (`<Volume2 />`) rendered alongside `Replay` on all valid recorded session cards.
- [x] **Clear Separation Between Replay & Audition**:
  - `Replay` triggers backend 25 Hz decimated DSP telemetry and live Welch spectrogram stream.
  - `Audition` triggers workstation speaker output via WebAudio engine (`audioEngine.ts`).
- [x] **Header Truthfulness upon Opening Local WAV**: Loading a local WAV sets `sourceType = 'file'`, causing `unsubState` to isolate GUI state from rogue backend stream updates.
- [x] **Exact 4000 Hz & Recording Duration Display**: CirCor 4000 Hz files show exact 11.888s length (or 6.992s for recorded session archives), distinct from the 15.0s display rolling window.
- [x] **Dynamic Sample Rate Label**: The overview waveform strip displays `L-{sampleRate}-RAW` (e.g. `L-4000-RAW`) instead of the previous static `L-44100-RAW`.

---

## 7. Manual Acceptance Gate: Acoustic Speaker Test

> [!IMPORTANT]
> **Status: PENDING USER CONFIRMATION**  
> Automated tests have validated all DSP pipelines, buffer lifecycles, and WebAudio node graphs. Actual physical acoustic sound heard through physical headphones or workstation speakers requires explicit manual verification by the user.

### How to Perform the Manual Audio Test:
1. Launch the new release build:
   `C:\Dev\Antigravity\bitirme\ausculta-forge\software\frontend\src-tauri\target\release\auscultaforge-desktop.exe`
2. Ensure workstation speakers or headphones are connected and volume is set to a comfortable level.
3. **Test Local Audio Playback**:
   - Go to **Home** or **Samples**.
   - Load or select a specimen (e.g. `40058_AV.wav`).
   - Click **Play** in the bottom transport controls.
   - Verify that continuous heart sound is clearly audible without clicks, 0.5s cutoffs, or muffled double-filtering.
4. **Test Recorded Session Audition**:
   - Switch to **Specimen Archives** (`SamplesView`) -> **Recorded Acquisition Sessions**.
   - Locate a recorded session card.
   - Click the **Audition** button (with speaker icon).
   - Verify that the recorded session audio plays directly through your workstation speakers.
