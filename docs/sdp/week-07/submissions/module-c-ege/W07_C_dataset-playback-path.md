# W07 Module C: Dataset Playback Path

- **Week:** 7
- **Module:** C (Computer Application & Quality Assessment)
- **Owner:** Ege Çağın Tepe
- **Status:** SOFTWARE IMPLEMENTATION COMPLETE / PHYSICAL PHANTOM PLAYBACK PENDING (Module A phantom assembly required)

## Objective

Implement the software playback path, deterministic test stimuli, and session provenance tracking required to drive an open dataset PCG recording (or calibrated excitation) through PC audio output into the acoustic phantom chain, while clearly separating software replay from physical phantom capture.

## Inputs / Dependencies

- Week-6 offline real PCG acceptance baseline (`4629f6a`, `069b810`): CirCor v1.0.3 (`4000 Hz`) and Challenge 2016 (`2000 Hz`) reference readers.
- Module A dependency: physical acoustic phantom (exciter + PAM8403 + silicone coupling + chestpiece) — currently pending physical assembly.

## Work Performed

1. **Deterministic Stimulus Generation (`software/pcg_core/stimulus.py`):**
   - Implemented `StimulusRecord` with SHA-256 content integrity hashing and normalized full-scale `[-1.0, +1.0]` provenance (`NO uncalibrated acoustic SPL claims`).
   - Implemented `generate_100hz_sine`, `generate_multitone` (Schroeder-phase cardiac passband), `generate_log_sweep` (20–500 Hz), `generate_impulse_train`, and reference PCG WAV asset preparation with rational resampling.
2. **Real-Time & Offline Playback Adapters (`software/pcg_core/sources.py`, `software/pcg_app/app.py`, `software/pcg_app/state.py`):**
   - Verified `WavSource` and `RealtimeWavSource` pacing and rate-accurate `SampleBlock` emission (`2 kHz`, `4 kHz`, `48 kHz`).
   - Hardened `POST /api/stream/upload_source_wav` (`4981500`, `4629f6a`) with source WAV SHA-256 tracking (`processing_profile.source_wav_sha256`), separate from recorded output `raw.wav` SHA-256.
   - Added explicit UI demarcation in `software/frontend/src/components/LiveWorkspace.tsx` (`9b480a4`) separating client-side **Local File Audition** from **Backend DSP Stream** and resolving double-filtering.
3. **USB Device State & Loss Detection Consumption (`software/pcg_app/app.py`, `software/pcg_app/canonical/session.py`):**
   - Verified canonical `StatusTelemetry` consumption (`dropped_samples`, `dma_overflow_events`, `ring_overflow_events`, `usb_partial_write_events`) and host-side FSM disconnect/reconnect safety (`(ABSENT | INTERRUPTED | ERROR) -> DETECTED -> OPENING` fix on 2026-11-16).

## Evidence

- Source modules: `software/pcg_core/sources.py`, `software/pcg_core/stimulus.py`, `software/pcg_app/app.py`, `software/pcg_app/state.py`, `software/pcg_app/canonical/session.py`
- Automated tests: `software/tests/test_real_pcg_acceptance.py`, `software/tests/test_replay_eof_health.py`, `software/tests/test_stream_filter_contract.py`, `software/tests/test_phantom_system_id.py`
- Handoff summary: [`docs/sdp/PROGRESS_ASOF_2026-11-17.md`](../../../PROGRESS_ASOF_2026-11-17.md)

## Results

- Software playback path, deterministic stimulus preparation, rate tracking, and host loss telemetry consumption pass all automated software regressions.
- **Physical acoustic phantom playback:** `PENDING` / `NOT_EXECUTED` (physical exciter, PAM8403, chestpiece, and live INMP441 path not yet assembled on bench).

## Open Decisions / Risks

- Open: Physical calibration of PC DAC output gain into PAM8403 (must avoid digital clipping and BTL `OUT-` grounding hazards documented in [`docs/handoff/HARDWARE_GATES_AND_ROLLBACK.md`](../../../../handoff/HARDWARE_GATES_AND_ROLLBACK.md)).

## Next Week Handoff

Once Module A assembles the acoustic phantom and PAM8403 exciter chain safely (and G2 INMP441 passes standalone checks), drive `PHANTOM_LOG_SWEEP_20_500HZ_V1` and `PHANTOM_PCG_REPLAY_V1` captures into Week-8 metrology scripts.
