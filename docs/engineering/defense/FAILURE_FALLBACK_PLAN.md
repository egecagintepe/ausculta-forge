# AuscultaForge — Demonstration Failure Contingency & Fallback Plan
**Document ID:** `AF-DEFENSE-FALLBACK-V01`  
**Classification:** `EMERGENCY_PROCEDURE`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Author:** Ege Çağın Tepe (Module C Owner)  
**Baseline Git Commit:** `fa4b75a80d29aab04875534234574db9f6c0af43`

---

## 1. Golden Rule of Demo Failures: Graceful Engineering Fallbacks

Hardware prototypes deployed on breadboards are vulnerable to loose jumper wires, broken USB cables, or university ground loops during examination presentations. If physical hardware misbehaves in front of the professors, **never attempt frantically to re-solder or wiggle wires for 15 minutes while the committee waits in silence.**

AuscultaForge integrates a pre-built, fully functional **Software Virtual Bench** and offline playback fallback mechanism. This plan defines the immediate pivot procedures for four major failure contingencies.

---

## 2. Contingency Procedures

### Contingency 1: Physical ESP32-S3 Fails to Enumerate on USB
* **Failure Symptom:** Windows Device Manager does not list a USB Serial Device when plugged in; status reports `ABSENT`.
* **Immediate Verbal Pivot to Committee:**
  > *"Professors, the physical USB PHY is not enumerating on this host controller, likely due to a loose D+/D- breadboard jumper wire. To demonstrate our verified end-to-end processing, display decimation, metrology automation, and segmentation pipeline, I will now switch the runtime to our deterministic Virtual Bench mode."*
* **Fallback Execution:**
  1. Open the UI tab **"Virtual Bench"**.
  2. Select **Scenario 1: `sine_100hz`** or **Scenario 2: `ascending_counter`**.
  3. Click **"Mount Virtual Source & Stream"**.
  4. The runtime feeds deterministic 48 kHz blocks through the exact same `StreamManager`, `DisplayDecimator`, WebSocket bridge, and session recording pipelines as real hardware.

---

### Contingency 2: INMP441 Acoustic Sensor Produces Silence ($y[n] = 0$)
* **Failure Symptom:** Device is `STREAMING`, but the INMP441 data line (`GPIO 6`) is disconnected or the MEMS chip is starved of power. Waveform is completely flat.
* **Immediate Verbal Pivot to Committee:**
  > *"The I2S serial data line has lost electrical contact on the breadboard. Rather than spending exam time with a multimeter, I will switch our stream input to our offline acoustic phantom reference playback source to demonstrate our live filtering and spectral metrology."*
* **Fallback Execution:**
  1. In `LiveWorkstation.tsx`, select Source: **"Offline Phantom Capture Playback"** (`data/raw/sample.wav`).
  2. Click **"Stream Reference"**.
  3. The `RealtimeWavSource` paces the recorded 48 kHz phonocardiogram through the streaming pipeline at exact real-time speed ($\Delta t = 10.67\text{ ms}$ per 512 samples).

---

### Contingency 3: Severe 50 Hz Mains Hum Corrupts the Spectrum
* **Failure Symptom:** The examination hall has ungrounded 220V power outlets, injecting massive 50 Hz hum ($> 30\text{ dB}$ above heart sounds).
* **Immediate Verbal Pivot to Committee:**
  > *"As expected in unshielded breadboard prototypes, the room's ungrounded power lines are capacitively coupling 50 Hz hum into our high-impedance acoustic cavity. Notice how our high-resolution mains analysis immediately flags the fundamental and harmonics. I will now disconnect the laptop charger to break the ground loop and engage our software high-pass filter."*
* **Fallback Execution:**
  1. Physically unplug the laptop AC adapter to run on DC battery power.
  2. In the UI filter panel, verify that the 4th-order Butterworth high-pass filter ($f_c = 20 \text{ Hz}$) is active.
  3. If hum persists, toggle the optional software 50 Hz notch filter ($Q = 30$).

---

### Contingency 4: Windows COM Port is Locked by Another Process (`PermissionError`)
* **Failure Symptom:** Calling `POST /api/device/connect` returns HTTP 500: `serial.SerialException: could not open port 'COM3': PermissionError(13, 'Access is denied.')`.
* **Root Cause:** A background Python instance, serial monitor (PuTTY/Arduino IDE), or previous crashed process still holds an open Windows kernel handle to the port.
* **Immediate Emergency Command:**
  Open PowerShell as Administrator and kill lingering Python processes:
  ```powershell
  # Force terminate any orphaned python or uvicorn processes locking COM ports:
  Stop-Process -Name python -Force -ErrorAction SilentlyContinue
  
  # Restart AuscultaForge backend:
  .\.venv\Scripts\python.exe -m pcg_app.server --port 8000
  ```
  The COM port is released instantaneously.
