# AuscultaForge — 30-Minute Endurance Streaming Candidate (P1)

**Document Date:** 2026-11-24  
**Author:** Ege Çağın Tepe (Module C)  
**Engineering Status:** Isolated Software Candidate Ready / Physical Execution `NOT_EXECUTED` (Preserved for Post-P0 Lab Gate)

---

## 1. Objective and Course Requirement

As specified in the official course document `SDP4_Digital_Stethoscope_Plan_EN.docx` (Weeks 7–8 / 10), the system must demonstrate stability under continuous streaming operation:
- **Duration:** $\ge 30\text{ minutes}$ ($1800\text{ seconds}$).
- **Sampling Rate:** $48{,}000\text{ Hz}$ mono, 24-bit acquisition.
- **Total Samples:** $1800\text{ s} \times 48{,}000\text{ samples/s} = 86{,}400{,}000\text{ samples}$.
- **Frame Count:** $86{,}400{,}000 / 256 = 337{,}500\text{ frames}$ (Profile B format).
- **Target Metrics:** Zero packet loss within the streaming interval, 0 sequence gaps, 0 CRC-32 errors, bounded memory on host, and zero buffer overflow on ESP32-S3 DMA/ring buffer.

---

## 2. Theoretical Transport & Storage Accounting

| Parameter | Unit / Value | Engineering Note |
|---|---|---|
| Nominal Sampling Rate ($f_s$) | $48{,}000\text{ Hz}$ | Standard acquisition clock |
| Profile B Frame Size | $256\text{ samples}$ | Fixed frame granularity |
| Frame Duration | $5.\bar{33}\text{ ms}$ | $256 / 48000$ |
| Frame Rate | $187.5\text{ frames/sec}$ | Wire transmission frequency |
| Wire Frame Format | $1068\text{ bytes}$ | 40 B Header + 1024 B Payload (256 $\times$ int32) + 4 B CRC-32 |
| Protocol Wire Data Rate | $200{,}250\text{ bytes/s}$ ($\approx 1.602\text{ Mbps}$) | Well within USB 2.0 Full Speed (12 Mbps) / High Speed CDC |
| Total Protocol Wire Bytes (30 min) | $360{,}450{,}000\text{ bytes}$ ($\approx 343.75\text{ MiB}$) | Total USB bulk data transmitted over wire |
| Host WAV File Size (int16 PCM) | $172{,}800{,}044\text{ bytes}$ ($\approx 164.79\text{ MiB}$) | 2 bytes/sample + 44 B standard RIFF header |
| Host WAV File Size (float32 PCM) | $345{,}600{,}044\text{ bytes}$ ($\approx 329.59\text{ MiB}$) | 4 bytes/sample + 44 B standard RIFF header |
| Minimum Free Host Disk Space | $\ge 2.0\text{ GB}$ | Required for safe streaming and scratch space |

---

## 3. Firmware Architectural Audit & Safety Constraints

### 3.1 Existing Working G2 Release (`firmware/releases/g2_candidate_20261117`)
- Defined in `firmware/components/g1/include/g1.h`:
  ```c
  #define G1_TARGET_SAMPLES 480000U  /* 10.0 seconds at 48 kHz */
  ```
- Defined in `firmware/components/g1/g1.c` (line 191–196):
  ```c
  if ((s->state == G1_STREAMING || s->state == G1_STOPPING) &&
      now - s->reference_us > 40000000U) {  /* 40.0 second safety watchdog */
      s->telemetry.stop_reason = STOP_REASON_TIMEOUT;
      g1_transport_fault(s);
      return;
  }
  ```

### 3.2 Why Firmware Cannot Be Modified In-Place Before Tomorrow's Lab
1. **P0 Priority Rule:** The primary objective for Wednesday morning 25 November 2026 is **P0 Phantom S1/S2 Gating** with the existing validated G2 firmware.
2. **Watchdog Conflict:** Simply increasing `G1_TARGET_SAMPLES` to 86,400,000 without altering the 40-second watchdog will abort the session at second 40.
3. **Flashing Risk:** Compiling and flashing an experimental firmware onto the single available ESP32-S3 board on the eve of the lab session would introduce unverified regressions and destroy the G2 physical attestation state (`g2_physical_attestation.json`).
4. **Resolution:** Maintain the current flashed G2 candidate for tomorrow's P0 experiments. Provide the endurance host tooling and firmware profile candidate as an isolated post-P0 verification step.

---

## 4. Host Streaming Architecture (`tools/hardware/run_endurance_session.py`)

To prevent host Out-Of-Memory (OOM) crashes when ingesting 86.4M samples:
- **`IncrementalWavWriter`:** Streams chunks directly to disk via incremental block writes with an $O(1)$ memory footprint. RIFF header byte lengths are patched only upon clean session completion.
- **Continuity Accounting:** Every Profile B frame is checked for:
  - Strict sequence incrementation (`seq == last_seq + 1`).
  - CRC-32 integrity.
  - Microsecond timestamp monotonicity (`ts_us`).
- **Telemetry Manifest:** Emits `endurance_manifest.json` containing exact sample counts, elapsed times, packet drop rates, and file SHA-256.

---

## 5. Verification Commands

### 5.1 Host Accelerated Self-Test (Zero Hardware Required)
```powershell
.\.venv\Scripts\python.exe tools/hardware/run_endurance_session.py --simulate --accelerated --target-seconds 1800 --output-dir experiments/sessions/endurance_simulated_accelerated
```
*Validates that 86,400,000 samples, 337,500 frames, and standard RIFF WAV formatting complete without memory growth.*

### 5.2 Physical Endurance Execution (Post-P0 Operator Authorized)
```powershell
.\.venv\Scripts\python.exe tools/hardware/run_endurance_session.py --port COM3 --target-seconds 1800 --output-dir experiments/sessions/endurance_physical_20261125
```
