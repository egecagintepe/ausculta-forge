# AUSCULTAFORGE — FIRST PHYSICAL ESP32-S3 USB BRING-UP GUIDE
## Canonical Profile B v0.1 Host ↔ Hardware Verification Manual
**Target Audience:** Ege (Module C Host Architecture), Ozan (Module B ESP-IDF Firmware), Kaan (Module A Acoustic Transducer)  
**Standard Specification Reference:** `docs/engineering/protocol/B_C_CANONICAL_PROTOCOL_V0_1.md`  
**Host Application Baseline:** AuscultaForge Desktop v0.1-alpha.1 (`main`)

---

## 1. PHYSICAL HARDWARE INSPECTION & USB INTERFACE IDENTIFICATION

### 1.1 Dual USB Connectors on ESP32-S3 DevKit
Standard ESP32-S3 development boards feature **two separate USB Type-C connectors**:
1. **USB-to-UART / USB-Serial-JTAG (Debug / Flashing Port):**
   - Typically labeled `UART` or `DEBUG`.
   - Connected internally to CP2102/CH340 or the ESP32-S3 internal USB Serial/JTAG controller.
   - **Role:** Flashing firmware via `idf.py flash`, inspecting console output via `idf.py monitor`.
   - **DO NOT USE FOR HIGH-SPEED AUDIO STREAMING.** It lacks sustained throughput for 200 kB/s raw audio and does not support USB-OTG TinyUSB CDC-ACM audio endpoints.
2. **Native USB-OTG (Data / Canonical Streaming Port):**
   - Typically labeled `USB` or `OTG`.
   - Connected directly to GPIO 19 (`D-`) and GPIO 20 (`D+`).
   - **Role:** High-speed USB CDC-ACM transport running TinyUSB device stack.
   - **THIS IS THE REQUIRED AUSCULTAFORGE CANONICAL STREAMING PORT.**

> [!IMPORTANT]
> For the first physical bring-up, connect **BOTH** ports to the host PC using quality USB 2.0 data cables (not charge-only cables):
> - Port 1 (`UART/DEBUG`): For Ozan to observe real-time firmware logs via ESP-IDF terminal.
> - Port 2 (`USB/OTG`): For Ege's AuscultaForge Desktop application to execute the canonical protocol.

---

## 2. WINDOWS DEVICE MANAGER VERIFICATION

Open **Windows Device Manager** (`devmgmt.msc`) under the **Ports (COM & LPT)** branch:

1. **Verify Enumeration:**
   - When the Native USB cable is plugged in, a new COM port must appear (e.g. `COMx`).
   - If Windows shows `USB Serial Device (COMx)`, right-click → Properties → Details → **Hardware Ids**.
2. **Distinguishing Interfaces:**
   - Native USB CDC-ACM devices typically exhibit standard USB CDC-ACM descriptor class `02h` / subclass `02h`.
   - USB-Serial-JTAG exhibits interface descriptors specific to Espressif debug adapters.
   - Note down the exact COM port number assigned to the Native USB CDC-ACM interface.

> [!WARNING]
> Do NOT guess or hardcode COM port numbers or USB VID/PIDs. Windows dynamically assigns COM port numbers depending on which USB root hub port is utilized.

---

## 3. CANONICAL PROTOCOL SPECIFICATION CONSTANTS

Every packet over USB CDC-ACM strictly conforms to Canonical Profile B v0.1:

| Constant | Value | Description |
| :--- | :--- | :--- |
| **Magic Word** | `0xAF534331` (`"1CSA"`) | 32-bit Synchronization magic (Little-Endian) |
| **Profile ID** | `0x0001` | Profile B (Standard 40-byte control & audio header) |
| **Header Size** | `40 bytes` | Profile B fixed header size |
| **Trailer Size** | `4 bytes` | CRC-32/IEEE (`poly=0xEDB88320`, init `0xFFFFFFFF`) |
| **Sample Rate** | `48,000 Hz` | Fixed 48 kHz sampling frequency |
| **Channels** | `1` (Mono) | Single acoustic channel |
| **Sample Format** | `0x0002` (`S32_LE`) | Signed 32-bit slot, 24 meaningful LSB-aligned bits |
| **Samples per Frame** | `256` | 256 samples per AUDIO packet |
| **Payload Size** | `1,024 bytes` | $256 \times 4\text{ bytes} = 1024\text{ bytes}$ audio payload |
| **Full Audio Packet Size** | `1,068 bytes` | $40\text{ (header)} + 1024\text{ (payload)} + 4\text{ (CRC)} = 1068\text{ bytes}$ |
| **Audio Bandwidth** | $\approx 200,250\text{ B/s}$ | Continuous streaming transport rate |

### Supported Firmware Source Modes:
- **Mode 1 (`0x0001`): Deterministic G1 Verification Mode**
  - Synthesizes 480,000 deterministic pseudo-random S32 samples over exactly 10.0 seconds (1,875 frames).
  - Formula: $\text{sample}[n] = ((n \times 1,103,515,245 + 12,345) \pmod{2^{31}}) - 2^{30}$.
  - Bit-exact mathematical validation on host.
- **Mode 0 (`0x0000`): Real Acoustic Capture Mode**
  - Streams real transducer acoustic data from physical I2S DMA.
  - Requires physical microphone hardware bring-up.

---

## 4. DESKTOP APPLICATION BRING-UP WORKFLOW

### Step 1: Launch AuscultaForge Desktop
1. Start the desktop environment:
   ```bash
   npm run dev  # in software/frontend
   # Ensure Python backend is running on 127.0.0.1:8000
   ```
2. Navigate to the **Device** view from the navigation drawer.

### Step 2: Scan USB Ports
1. Click **Scan USB Bus** (`#btn-scan-usb-bus`).
2. The drop-down menu populates with detected serial ports.
3. If an Espressif candidate is identified by USB Discovery Doctor, it displays `★ [ESP32 Candidate]`.
4. Select the COM port corresponding to the Native USB port.

### Step 3: Connect & Perform HELLO Handshake
1. Click **Connect & HELLO** (`#btn-connect-usb`).
2. Host opens the serial port with finite timeouts (2000ms read, 1000ms write) and generates a random 64-bit nonce.
3. Host transmits `OP_HELLO_REQ` (`0x0001`) with profile `0x0001`.
4. Firmware must respond with `OP_HELLO_RESP` (`0x0002`) echoing the identical nonce.
5. Upon successful handshake, UI badge transitions to:
   ```
   [ HARDWARE VERIFIED / READY ]
   ```

### Step 4: Execute Deterministic G1 Qualification
1. Select **Deterministic G1 (Mode 1)** radio button.
2. Click **Start Acquisition** (`#btn-start-usb-acquisition`).
3. Host sends `OP_START_REQ` (`0x0003`) with `source_mode=1`, `sample_rate=48000`, `encoding=2`, `channels=1`.
4. Firmware returns `OP_START_ACK` (`0x0004`) containing a nonzero `session_id` (e.g. `0xA1B2C3D4`).
5. Application switches to **Live Hardware Streaming** (`[ ACQUIRING · G1 DETERMINISTIC ]`).
6. Observe live frame counters:
   - Validated Frames increments at $\approx 187.5\text{ frames/s}$.
   - Accepted Samples increments at $48,000\text{ samples/s}$.
   - Sequence Gaps and CRC Errors must remain `0`.
7. After 10 seconds (1,875 frames / 480,000 samples), click **Stop Acquisition** (`#btn-stop-usb-acquisition`).
8. Host sends `OP_STOP_REQ` (`0x0005`) carrying the active `session_id`.
9. Firmware flushes final FIFO buffers and returns `OP_STOP_ACK` (`0x0006`) with 72-byte status telemetry.
10. Host computes SHA-256 digest of received samples, compares against known-answer formula, and displays **Hardware G1 Verification Evidence Card**:
    - `all_samples_matched`: `true` (100.00%)
    - `accepted_samples`: `480000 / 480000`
    - `conclusion`: `VALIDATION_PASSED`

---

## 5. DIAGNOSTICS & ERROR RECOVERY

### 5.1 Common Faults & Diagnostics

| Symptom | Diagnostic Root Cause | Action |
| :--- | :--- | :--- |
| **Port cannot be opened (`PermissionError`)** | Port held by another tool (e.g., PuTTY, Arduino IDE, or orphaned python process) | Close competing serial monitors. Run `taskkill /F /IM python.exe` if orphaned. |
| **HELLO Timeout (`TIMEOUT_AWAITING_HELLO`)** | Firmware not running CDC task or plugged into Debug UART port instead of Native USB | Verify cable is in Native USB port. Ensure TinyUSB task is actively polling CDC. |
| **Invalid Nonce (`NONCE_MISMATCH`)** | Firmware responded with stale or hardcoded nonce | Ozan must ensure `hello_resp.nonce == hello_req.nonce`. |
| **CRC-32 Error (`CRC_MISMATCH`)** | Electrical noise, buffer corruption, or wrong polynomial | Ensure IEEE 802.3 CRC-32 polynomial `0xEDB88320` is used without bit inversion bugs. |
| **Sequence Discontinuity (`SEQ_GAP`)** | USB endpoint FIFO overrun on ESP32-S3 or host buffer stall | Increase TinyUSB endpoint FIFO buffer size in `sdkconfig`. Ensure host ingestion thread is not blocked. |
| **Connection Interrupted (`INTERRUPTED`)** | Physical cable disconnect or ESP32-S3 brownout | Application enters `INTERRUPTED` state without crashing. Reconnect cable and click `Scan USB`. |

### 5.2 Session Interruption Recovery Procedure
If USB cable is unplugged during streaming:
1. Host enters `INTERRUPTED` state, preserving already recorded samples.
2. In the UI, click **Disconnect** (`#btn-disconnect-usb`).
3. Reconnect physical USB cable.
4. Click **Scan USB Bus** and re-select the port.
5. Click **Connect & HELLO** to establish a fresh session ID.

---

## 6. TEAM HANDOFF REQUIREMENTS

### 6.1 What Ozan (Module B Firmware) Must Provide
1. ESP-IDF console logs from `UART` port showing:
   - TinyUSB initialization: `CDC-ACM endpoint opened (EP 0x81 IN, 0x01 OUT)`.
   - Received `OP_HELLO_REQ` with nonce `0x...`.
   - Transmitted `OP_HELLO_RESP`.
   - Received `OP_START_REQ` (`mode=1`, `fs=48000`).
   - Generated `session_id` (`0x...`).
   - Frame dispatch count reaching exactly `1875` frames.
   - Received `OP_STOP_REQ`.
   - Transmitted `OP_STOP_ACK` with final telemetry counters:
     - `hw_frames_sent == 1875`
     - `hw_fifo_overflows == 0`
     - `hw_dma_underruns == 0`

### 6.2 What Ege (Module C Host Software) Must Capture
1. G1 Evidence JSON report saved in session directory:
   - `evidence_id`, `sha256_hash`, `accepted_samples: 480000`, `all_samples_matched: true`.
2. Flight recorder log bundle exported via `DiagnosticsDrawer` (`Export Support Bundle`).
3. Recorded 10-second session WAV file and metadata manifest.

### 6.3 What Kaan (Module A Transducer) Must Verify Before Real Acoustic Test
1. Acoustic chamber baseline SNR $> 40\text{ dB}$.
2. Transducer analog front-end power rail stability (no 50/60 Hz mains ripple exceeding 5 mV).
3. Confirm microphone I2S DMA clocking ($48\text{ kHz} \times 32\text{ bits} \times 2 = 3.072\text{ MHz}$ BCLK).
4. Run Deterministic G1 test first before attempting Real Acoustic Mode.
