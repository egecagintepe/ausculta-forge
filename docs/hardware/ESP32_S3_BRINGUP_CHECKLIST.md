# AuscultaForge — ESP32-S3 Physical Hardware Bring-Up & Integration Checklist

**Document ID:** `AF-HW-BRINGUP-CHECKLIST-V01`  
**Course:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Hardware Target:** ESP32-S3-DevKitC-1 (N16R8) + INMP441 I²S MEMS Microphone  
**Owners:** Module B (Ozan — Embedded) & Module C (Ege — Host Software)  
**Status:** UNVERIFIED / PENDING PHYSICAL HARDWARE ARRIVAL & MODULE B APPROVAL

---

> [!IMPORTANT]
> **HARDWARE READINESS & CROSS-MODULE BOUNDARY NOTICES:**
> 1. **Software Sprint vs Academic Calendar:** This checklist was prepared under Software Sprint 10 (agile software iteration for Module C). It must **NOT** be confused with academic semester Week 10 (currently Week 04/05 of EEE495).
> 2. **DirencNet Board Verification Required:** The purchased DirencNet N16R8 board must **NOT** be assumed to be an official Espressif DevKitC-1 with functional dual-USB routing without physical bench inspection. Many commercial clones feature only a single USB port or wire a CH340 USB-UART bridge without routing out the native USB OTG PHY. Physical inspection of connectors and traces is mandatory before Gate 2.
> 3. **Unapproved Wire Framing & Alignment:** Firmware packet framing (headers, magic word `0xAA55`, CRC-16 polynomial) and integer alignment (LSB vs MSB) remain **UNAPPROVED PROPOSALS** pending joint sign-off with Module B (Ozan under DW03-09/12). Production firmware ownership remains strictly with Ozan under `firmware/`.
> 4. **48 kHz Sampling Rate Limitation:** `512 samples + vTaskDelay(11 ms)` in experimental tasks is an approximation subject to FreeRTOS tick jitter. Production hardware sampling MUST be governed by I2S DMA interrupts to guarantee true 48.000 kHz sampling.
> 5. **USB Backpressure & Data Loss:** USB queue writes must handle short writes and buffer backpressure rather than assuming lossless transmission.

---

## 1. Purchased Hardware Identification & Port Mapping

| Hardware Item | Exact Specification | Role in System | Port / Header Identification |
|---|---|---|---|
| **MCU Board** | **ESP32-S3-DevKitC-1-N16R8 (DirencNet Order — Requires Physical Verification)** | Central audio acquisition controller, I²S DMA master, Native USB peripheral | **Requires physical confirmation on arrival:**<br>1. **"UART" / "COM" Port:** USB-to-UART bridge for firmware flashing and serial debug.<br>2. **"USB" Port:** Direct connection to ESP32-S3 internal USB OTG PHY (`GPIO 19` D-, `GPIO 20` D+). If board is a single-port clone, USB OTG streaming requires a custom breakout cable to GPIO 19/20. |
| **Acoustic Sensor** | **INMP441 Omnidirectional MEMS Microphone Breakout Board** | Heart sound capture from phantom chestpiece | 6-pin 0.1" header: `VDD`, `GND`, `SD`, `SCK`, `WS`, `L/R` |
| **Interconnect** | Breadboard jumper wires / 30 AWG stranded wire (< 10 cm recommended) | I²S digital bus connection between INMP441 and ESP32-S3 | Keep signal traces short to minimize high-frequency I²S edge reflections and clock jitter |

---

## 2. Step-by-Step Bring-Up & Verification Checklist

### Gate 1: Physical Inspection & Power Rails
- [ ] **1.1 Visual Inspection:** Inspect ESP32-S3 DevKit and INMP441 board for solder bridges, bent pins, or defective components.
- [ ] **1.2 3.3V Power Rail Check:** Connect USB power to UART port. Measure voltage across `3V3` and `GND` pins with a digital multimeter. Verify $3.30 \pm 0.10 \text{ V}$.
- [ ] **1.3 INMP441 Pin Connections:**
  - `VDD` $\to$ ESP32-S3 `3V3` (3.3V power supply)
  - `GND` $\to$ ESP32-S3 `GND` (Ground return)
  - `L/R` $\to$ ESP32-S3 `GND` (Tied to ground for Left Channel audio output)
  - `WS`  $\to$ ESP32-S3 `GPIO 5` (Word Select / LRCLK)
  - `SCK` $\to$ ESP32-S3 `GPIO 4` (Continuous Bit Clock / BCLK)
  - `SD`  $\to$ ESP32-S3 `GPIO 6` (Serial Data Out from microphone)

---

### Gate 2: Native USB Enumeration & Driver Binding
- [ ] **2.1 Dual-Cable Connection:** Connect Cable 1 to "UART" port (for flashing/logs) and Cable 2 to "USB" port (for host streaming).
- [ ] **2.2 Device Manager Enumeration:**
  - Open Windows Device Manager (`devmgmt.msc`).
  - Under **Ports (COM & LPT)**, verify two distinct COM devices appear:
    - `Silicon Labs CP210x USB to UART Bridge (COMx)` (Flashing/Logs)
    - `USB Serial Device (COMy)` or `ESP32-S3 USB CDC (COMy)` (Native USB)
  - Confirm Hardware IDs for Native USB:
    - Vendor ID: `0x303A` (Espressif Systems)
    - Product ID: `0x4001` (TinyUSB CDC-ACM) or `0x1001` (ESP USB JTAG/CDC)
- [ ] **2.3 Driver Class Confirmation:**
  - Verify Windows driver is `usbser.sys` (standard Microsoft USB Serial Driver).
  - Confirm zero custom INF or Zadig driver overrides are required for normal evaluation.

---

### Gate 3: INMP441 I²S Clock & DMA Alignment Verification
- [ ] **3.1 Oscilloscope / Logic Analyzer Verification:**
  - Probe `SCK` (`GPIO 4`): Verify clean square wave at continuous bit clock frequency:
    $$f_{\text{SCK}} = 2 \times \text{slot\_bits} \times f_s = 2 \times 32 \times 48,000 = 3,072,000 \text{ Hz} \ (3.072 \text{ MHz})$$
  - Probe `WS` (`GPIO 5`): Verify symmetric 50% duty cycle square wave at:
    $$f_{\text{WS}} = f_s = 48,000 \text{ Hz} \ (48 \text{ kHz})$$
  - Probe `SD` (`GPIO 6`): Verify data transitions 1 SCK clock period after WS transition (standard I²S protocol).
- [ ] **3.2 Bit Alignment Determination (Ozan & Ege Sign-off):**
  - Read raw DMA 32-bit buffer words:
    - **LSB-Aligned:** Lower 24 bits contain audio, upper 8 bits are sign-extended.
    - **MSB-Aligned (Left-Justified):** Upper 24 bits contain audio, lowest 8 bits are zeroed (`0x00`).
  - Document the observed alignment in `W10_C_embedded-interoperability-audit.md`.

---

### Gate 4: Known Synthetic Sample Transmission Test
- [ ] **4.1 Flash Synthetic 100 Hz Generator:** Flash `tools/esp32_bench_example` (or Ozan's synthetic test firmware) via UART port.
- [ ] **4.2 Host COM Port Reading:**
  - Open Python terminal:
    ```python
    import serial
    ser = serial.Serial('COMy', 115200, timeout=1.0)
    data = ser.read(2048)  # Read 1 block (512 samples * 4 bytes)
    print(f"Read {len(data)} bytes")
    ```
  - Verify received byte stream does not stutter or throw serial framing errors.

---

### Gate 5: Host Runtime Handshake & Ingestion
- [ ] **5.1 Launch AuscultaForge Python Host Backend:**
  ```powershell
  # Option A: Recommended CLI server entrypoint
  .venv\Scripts\python.exe -m pcg_app.server --host 127.0.0.1 --port 8000

  # Option B: Direct Uvicorn launch using application factory
  .venv\Scripts\python.exe -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000
  ```
- [ ] **5.2 Handshake Verification:**
  - Trigger device scan via API or UI (`POST /api/device/poll`).
  - Verify device transitions cleanly through lifecycle states:
    $$\text{ABSENT} \longrightarrow \text{DETECTED} \longrightarrow \text{OPENING} \longrightarrow \text{HANDSHAKING} \longrightarrow \text{READY}$$
  - Verify `capabilities` response reflects 48000 Hz, 1 channel, 32-bit container, 24-bit data.
- [ ] **5.3 Stream Initiation:**
  - Call `POST /api/stream/start` (or click "Connect & Stream" in Live Workstation UI).
  - Verify state transitions to `STREAMING`.
  - Verify WebSocket `signal_frame` messages broadcast to frontend at steady 30–60 Hz rate.

---

### Gate 6: WAV Recording & Sample-Count Integrity Verification
- [ ] **6.1 Fixed-Duration Capture:**
  - Record a 10.0-second session of synthetic 100 Hz tone.
- [ ] **6.2 Sample Count Monotonicity Check:**
  - Exact expected sample count:
    $$N_{\text{expected}} = 48,000 \times 10.0 = 480,000 \text{ samples}$$
  - Confirm recorded WAV file contains exactly 480,000 samples (zero dropped blocks, zero timeline drift).
- [ ] **6.3 Spectral Integrity Check:**
  - Perform Welch PSD in `ScientificLab.tsx` or using `pcg_core.spectral`.
  - Verify single sharp peak at **exactly 100.0 Hz** with harmonic distortion down $> 50 \text{ dB}$.

---

### Gate 7: Disconnect / Reconnect Fault-Tolerance Test
- [ ] **7.1 Mid-Stream Cable Disconnect:**
  - While recording, physically pull the Native USB cable out of the PC.
  - Verify host transitions immediately from `STREAMING` to `INTERRUPTED`.
  - Verify the active session file is safely closed and saved to disk with metadata `termination_reason='device_disconnected'`.
  - Confirm the Python backend and React frontend DO NOT crash or freeze.
- [ ] **7.2 Cable Re-insertion:**
  - Plug the cable back in.
  - Verify host detects reconnection (`DETECTED`), re-negotiates capabilities, and returns to `READY`.

---

### Gate 8: Gate G1 Evidence Package Collection
For official advisor Gate G1 milestone sign-off, archive the following artifacts:
1. [ ] **Photograph / Diagram:** Bench setup showing ESP32-S3 DevKit connected to INMP441 and PC via dual USB cables.
2. [ ] **Logic Analyzer Trace:** Screenshot of SCK, WS, and SD lines proving clean I²S clocking at 3.072 MHz.
3. [ ] **Device Manager Screenshot:** Showing enumerated Native USB CDC-ACM COM port.
4. [ ] **Recorded 10-Second WAV:** `HeartSound_Synthetic100Hz_Verification.wav` stored in `experiments/sessions/`.
5. [ ] **Session Metadata JSON:** Authoritative JSON file with Git SHA, sample count (480,000), sample rate (48000), and zero drop count.
6. [ ] **PSD Plot:** Spectrum showing 100 Hz fundamental peak without spectral leakage.

---

## 3. Local Start & Verification Guide (Host Software)

### Step 1: Start Python FastAPI Backend
```powershell
# In repository root:
.\.venv\Scripts\Activate.ps1

# Option A: Recommended CLI server entrypoint
python -m pcg_app.server --host 127.0.0.1 --port 8000

# Option B: Direct Uvicorn launch using application factory
python -m uvicorn pcg_app.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```
- Status & Capabilities: `http://127.0.0.1:8000/api/status`
- API Documentation: `http://127.0.0.1:8000/docs`

### Step 2: Start React Frontend
```powershell
# In software/frontend:
cd software/frontend
npm run dev
```
- Open browser at: `http://127.0.0.1:3000`

### Step 3: Run Full Automated Verification Suite
```powershell
# Run all backend unit and regression tests
python -m pytest software/tests

# Run frontend lint and production build
cd software/frontend
npm run lint
npm run build
npm test
```
