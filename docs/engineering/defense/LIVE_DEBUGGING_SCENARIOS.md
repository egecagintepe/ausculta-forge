# AuscultaForge — Live Examination Debugging & Failure Scenarios
**Document ID:** `AF-DEFENSE-DEBUGGING-V01`  
**Classification:** `ACADEMIC_DEFENSE` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Target Candidate:** Ege Çağın Tepe (Module C Owner)

---

## 1. Objective: Demonstrating Live Engineering Diagnostics

A hallmark of an expert engineering defense is the ability to calmly diagnose, isolate, and explain real-time system failures. If an anomaly occurs during a live demonstration in front of the examination committee, panicking or blaming "a glitch" results in poor grading.

This handbook outlines 6 concrete debugging scenarios, providing the exact physical symptom, diagnostic steps, underlying root cause, and immediate live fix.

---

## 2. Debugging Scenarios

### Scenario 1: Loud Digital Crackling / Harsh Buzzing Noise
* **Observed Symptom:** The audio monitor produces loud, periodic harsh buzzing or random digital clicks, even though the room is quiet.
* **Diagnostic Step 1:** Open `ScientificLab.tsx` and check the raw waveform amplitude and Welch PSD.
  * *Observation:* The waveform jumps between $+0.99$ and $-1.00$ rapidly.
* **Underlying Root Cause:** **Bit-Alignment Mismatch (MSB vs. LSB)**.
  * The firmware is sending MSB-aligned samples (audio in bits 31..8), but the host normalizer is interpreting them as LSB-aligned (dividing by $2^{23}$ instead of $2^{31}$). Multiplying by 256 causes massive mathematical overflow and digital wrap-around clipping.
* **Immediate Live Fix:**
  * Check the alignment flag in the configuration or pass `is_msb_aligned=True` in `software/pcg_app/device_runtime.py`.
  * Verify using `tools/c_golden_vectors/fixtures/manifest.json`.

---

### Scenario 2: Flatline Waveform ($y[n] = 0.000$) During Live Streaming
* **Observed Symptom:** The UI displays `STREAMING`, the canvas is active, but the waveform is a perfectly flat line at zero volts.
* **Diagnostic Step 1:** Check `POST /api/status`. State is `STREAMING`, but `metrics.rms` is $0.0000$.
* **Diagnostic Step 2:** Check the physical DevKit: Is the DTR line asserted?
* **Underlying Root Cause:** **DTR Gating / Port Binding Issue**.
  * The ESP32-S3 firmware gates transmission on `tud_cdc_connected()` (DTR assertion). If the host serial handle was opened without asserting DTR (`ser.dtr = False`), the microcontroller task sleeps and transmits zero packets.
  * Alternatively, the INMP441 `VDD` or `GND` jumper wire has loosened on the breadboard, starving the MEMS IC of power.
* **Immediate Live Fix:**
  * Assert DTR: `ser.dtr = True`.
  * Check $3.3 \text{ V}$ power rail across INMP441 pins with a digital multimeter.

---

### Scenario 3: Massive 50 Hz Fundamental Spike ($> 30 \text{ dB}$ Above Signal)
* **Observed Symptom:** The live audio sounds like a deep electrical hum. The Welch PSD shows an enormous spike at exactly $50.0 \text{ Hz}$ with harmonic peaks at $100, 150, 200 \text{ Hz}$.
* **Diagnostic Step 1:** Check if the host laptop is plugged into a wall outlet charger.
* **Underlying Root Cause:** **Ground Loop & Capacitive Mains Coupling**.
  * Unshielded breadboard jumper wires and switched-mode laptop power supplies create a capacitive displacement current loop through the ground plane.
* **Immediate Live Fix:**
  * Unplug the laptop power brick and run on internal battery power.
  * Verify that the INMP441 ground pin connects directly to the ESP32-S3 ground plane via a short wire ($< 5 \text{ cm}$).
  * Verify that the 4th-order high-pass filter ($f_c = 20 \text{ Hz}$) is active in software.

---

### Scenario 4: Periodic "Tick-Tick-Tick" Clicks Every 10.67 ms
* **Observed Symptom:** The audio contains a steady, high-pitched $93.75 \text{ Hz}$ buzzing whine or periodic tick clicks.
* **Diagnostic Step 1:** Zoom into the waveform canvas down to the 10 ms scale.
  * *Observation:* Sharp step discontinuities appear at exact 512-sample intervals.
* **Underlying Root Cause:** **Filter State Vector Loss (`_zi` reset)**.
  * The DSP filtering code is re-instantiating `StreamingBandpass` on every block, or resetting `self._zi = None`. This forces the IIR filter to calculate from zero initial conditions every 512 samples, generating a step response spike at the start of every block.
* **Immediate Live Fix:**
  * Ensure the filter instance persists in `StreamManager` and that `self._zi` is updated causally across calls:
    ```python
    filtered, self._zi = scipy.signal.sosfilt(self._sos, chunk, zi=self._zi)
    ```

---

### Scenario 5: UI Canvas Freezes, but Terminal Logs Show Active Streaming
* **Observed Symptom:** The React desktop UI waveform canvas stops moving and appears frozen, yet terminal logs show the Python server is actively receiving packets.
* **Diagnostic Step 1:** Open browser developer tools (`F12`) and inspect the Console and Network tabs.
* **Underlying Root Cause:** **Browser Background Tab Throttling or WebSocket Disconnect**.
  * Chrome/Edge throttles `requestAnimationFrame` to $1 \text{ FPS}$ or suspends WebSockets when a browser tab is minimized or in the background.
  * Alternatively, the WebSocket connection closed due to a ping timeout, and `BridgeClient` is in a reconnect backoff loop.
* **Immediate Live Fix:**
  * Bring the browser tab to the foreground.
  * Click the "Reconnect" button on the UI banner or refresh the page; the Python server will immediately reconnect and resume streaming.

---

### Scenario 6: Replay or Verification Flags File Integrity Mismatch
* **Observed Symptom:** Calling `GET /api/sessions/{session_id}/verify` returns `status: "failed"` with `sha256_match: false` (or `verify_session()` raises `SessionVerificationError`).
* **Diagnostic Step 1:** Check the session directory `experiments/sessions/<session_id>/` and inspect `raw.wav` and `session.json`.
* **Underlying Root Cause:** **External File Alteration, Truncation, or Bit Rot**.
  * Someone opened `raw.wav` in an external audio editor and re-saved it (changing RIFF headers or re-quantizing samples), or the file was truncated during an incomplete copy. The disk SHA-256 no longer matches `raw_wav_sha256` recorded in `session.json`.
* **Immediate Live Fix:**
  * Explain the scientific purpose to the examiner: *"This is a deliberate data integrity safeguard. AuscultaForge detects file corruption or external alterations to guarantee that downstream scientific metrology operates strictly on untampered raw recordings."*
