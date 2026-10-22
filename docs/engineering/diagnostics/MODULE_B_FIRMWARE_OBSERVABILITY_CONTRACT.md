# AuscultaForge — Module B Firmware Observability Contract
## Host Diagnostic Mapping for Canonical Protocol v0.1 Wire Telemetry & Error Notifications

- **Joint Authors:** Ege (Module C — Host Architecture) & Ozan (Module B — ESP32-S3 Firmware)
- **Status:** Canonical Release Proposal / Active Workstation Baseline
- **Wire Specification Version:** Canonical B/C Protocol v0.1
- **Target Microcontroller:** ESP32-S3-WROOM-1 / N16R8 (Dual-Core Xtensa LX7 @ 240 MHz)

---

## 1. PURPOSE & PRINCIPLES

When AuscultaForge connects to the ESP32-S3 over USB CDC-ACM and an acquisition fails or degrades, host software must not guess. It must present verifiable evidence.

This document defines:
1. How Module C maps the approved 72-byte wire telemetry fields into host fault events.
2. How Ozan can emit explicit error frames (`MSG_TYPE_ERROR_NOTIFICATION = 0x07`).
3. Proposed C-compatible error codes for Ozan's firmware diagnostics.
4. How host desktop software displays and persists these events in the Flight Recorder.

> **CRITICAL RULE:**
> This contract **does not modify or extend** the 40-byte header or 72-byte telemetry payload of Canonical Protocol v0.1. All fields referenced are from the joint Wire Specification v0.1.

---

## 2. 72-BYTE TELEMETRY FIELD MAPPING TO HOST FAULT CATALOG

Canonical Protocol v0.1 packets `MSG_TYPE_HEARTBEAT_STATUS (0x04)` and `MSG_TYPE_STREAM_STOP_ACK (0x06)` contain an identical 72-byte telemetry payload:

```c
typedef struct __attribute__((packed)) {
    uint64_t session_id;               // Active session identifier (must match host)
    uint64_t generated_samples;        // Total samples DMA'd from I2S hardware
    uint64_t fully_queued_samples;     // Total samples buffered for USB CDC
    uint64_t dropped_samples;          // Samples discarded due to buffer overflow
    uint32_t audio_frames_queued;      // Number of 256-sample audio packets generated
    uint32_t dma_overflow_events;      // Hardware I2S DMA descriptor exhaustion count
    uint32_t ring_overflow_events;     // FreeRTOS stream buffer / ring full count
    uint32_t usb_partial_write_events; // tud_cdc_write returned < requested bytes
    uint32_t usb_timeout_events;       // USB CDC flush timed out
    uint32_t usb_disconnect_events;    // USB VBUS / cable unplug events observed
    uint32_t audio_bytes_queued;       // Total payload bytes buffered
    uint16_t stop_reason;              // 0=HOST_STOP, 1=TARGET_REACHED, 2=ERROR
    uint16_t error_code;               // Firmware diagnostic error code
} af_status_telemetry_t;               // Exactly 72 bytes
```

### Telemetry Field Diagnostic Triggers

| Firmware Telemetry Field | Trigger Condition | Host Fault Code | Host Severity | Subsystem | Evidence Origin | Host Action & Display |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dropped_samples` | `> 0` | `AF-STR-005` | `WARNING` | `STREAMING` | `REPORTED_BY_FIRMWARE` | Flags audio loss in timeline; recalculates effective sample count; highlights USB bandwidth or ring buffer congestion. |
| `dma_overflow_events` | `> 0` | `AF-STR-006` | `ERROR` | `STREAMING` | `REPORTED_BY_FIRMWARE` | Identifies I2S ISR or DMA descriptor exhaustion. Suggests increasing DMA descriptor buffer count in ESP-IDF `i2s_channel_config`. |
| `ring_overflow_events` | `> 0` | `AF-STR-007` | `ERROR` | `STREAMING` | `REPORTED_BY_FIRMWARE` | Identifies host backpressure or FreeRTOS task starvation. Suggests increasing inter-task ring buffer size or checking USB hub congestion. |
| `usb_partial_write_events` | `> 0` | `AF-STR-008` | `WARNING` | `STREAMING` | `REPORTED_BY_FIRMWARE` | USB CDC endpoint backpressure. Distinguishes harmless recoverable partial writes from unserviced stalled writes. |
| `usb_timeout_events` | `> 0` | `AF-USB-005` | `ERROR` | `USB` | `REPORTED_BY_FIRMWARE` | Records transmission stall on MCU side. Points to host CDC endpoint consumer pausing. |
| `usb_disconnect_events` | `> 0` | `AF-USB-004` | `ERROR` | `USB` | `REPORTED_BY_FIRMWARE` | Corroborates physical cable disconnect or USB VBUS drop observed by ESP32-S3 PHY. |
| `session_id` | `!= active_session_id` | `AF-PRT-006` | `ERROR` | `PROTOCOL` | `REPORTED_BY_FIRMWARE` | Rejects stale or corrupt packet; invalidates current session; forces handshake re-negotiation. |
| `error_code` | `!= 0` | `AF-PRT-009` | `ERROR` | `PROTOCOL` | `REPORTED_BY_FIRMWARE` | Decodes firmware-reported error code into human-readable fault definition in timeline. |

---

## 3. FIRMWARE ERROR NOTIFICATION WIRE FORMAT

When an unrecoverable condition occurs on the ESP32-S3, firmware emits `MSG_TYPE_ERROR_NOTIFICATION (0x07)` with a 32-byte control payload:

```c
typedef struct __attribute__((packed)) {
    uint32_t error_code;               // Error enumeration code (see Section 4)
    uint32_t error_context;            // Additional context (e.g. opcode, sample_idx)
    char     human_readable_msg[24];   // ASCII debug string (null-terminated)
} af_error_notification_t;             // Exactly 32 bytes
```

### Proposed C-Compatible Error Code Definitions (`af_firmware_faults.h`)

Ozan can define these constants in the firmware build tree:

```c
#ifndef AF_FIRMWARE_FAULTS_H
#define AF_FIRMWARE_FAULTS_H

#include <stdint.h>

/**
 * @brief AuscultaForge Firmware Diagnostic Error Codes
 * Compatible with Canonical Protocol v0.1 af_error_notification_t.error_code
 */
typedef enum {
    AF_FW_OK                          = 0x00000000,
    
    /* Hardware Initialization & Sensor Faults (0x0001 - 0x00FF) */
    AF_FW_ERR_I2S_INIT_FAILED         = 0x00000001,  // esp_err_t from i2s_new_channel
    AF_FW_ERR_INMP441_NO_CLOCK        = 0x00000002,  // BCLK / WS pin routing or crystal failure
    AF_FW_ERR_DMA_ALLOC_FAILED        = 0x00000003,  // PSRAM / SRAM DMA descriptor allocation fail
    AF_FW_ERR_USB_PHY_INIT_FAILED     = 0x00000004,  // TinyUSB USB-OTG PHY configuration failure
    
    /* Protocol & State Machine Faults (0x0100 - 0x01FF) */
    AF_FW_ERR_UNEXPECTED_OPCODE       = 0x00000101,  // Opcode received in invalid FSM state
    AF_FW_ERR_STALE_SESSION_ID        = 0x00000102,  // START/STOP referenced obsolete session
    AF_FW_ERR_UNSUPPORTED_PROFILE     = 0x00000103,  // Host requested Profile not supported
    AF_FW_ERR_UNSUPPORTED_SAMPLE_RATE = 0x00000104,  // Host requested rate != 48000 Hz
    AF_FW_ERR_UNSUPPORTED_ENCODING    = 0x00000105,  // Host requested encoding != PCM16_LE
    
    /* Streaming Buffer & Acquisition Overflows (0x0200 - 0x02FF) */
    AF_FW_ERR_RING_BUFFER_EXHAUSTED   = 0x00000201,  // Ring buffer full; dropping audio samples
    AF_FW_ERR_DMA_QUEUE_OVERFLOW      = 0x00000202,  // DMA descriptors exhausted
    AF_FW_ERR_USB_TX_STALLED          = 0x00000203,  // tud_cdc_write stalled for > 100ms
    
    /* System & Memory Faults (0x0300 - 0x03FF) */
    AF_FW_ERR_FREE_HEAP_CRITICAL      = 0x00000301,  // Free heap < 16 KB threshold
    AF_FW_ERR_TASK_WATCHDOG_TRIGGERED = 0x00000302,  // Acquisition task missed TWDT deadline
} af_firmware_fault_code_t;

#endif /* AF_FIRMWARE_FAULTS_H */
```

---

## 4. HOW OZAN EMITS A FAULT & HOW EGE'S WORKSTATION LOGS IT

### Step-by-Step Scenario: DMA Descriptor Exhaustion

1. **Firmware Execution (Ozan):**
   - The I2S DMA driver receives an overflow event `I2S_EVENT_DMA_ERROR`.
   - Firmware increments `telemetry.dma_overflow_events++`.
   - If severe, firmware calls:
     ```c
     af_emit_error_notification(
         AF_FW_ERR_DMA_QUEUE_OVERFLOW, 
         overflow_count, 
         "I2S DMA exhausted"
     );
     ```
2. **Host Wire Ingestion (Ege):**
   - `HostProtocolSession._dispatch_packet()` receives the packet and validates CRC-32.
   - It sees opcode `MSG_TYPE_ERROR_NOTIFICATION` (or `dma_overflow_events > 0` in telemetry).
   - It emits an internal diagnostic event mapping to `AF-STR-006` (`DMA_OVERFLOW_REPORTED`).
3. **Flight Recorder Persistence:**
   - The event is appended to `flight_recorder.jsonl`:
     ```json
     {
       "event_id": "af-evt-b4c9e1",
       "timestamp_utc": "2026-10-22T16:40:00.000Z",
       "severity": "ERROR",
       "subsystem": "STREAMING",
       "fault_code": "AF-STR-006",
       "message": "Firmware reported 1 DMA overflow events",
       "evidence_origin": "REPORTED_BY_FIRMWARE",
       "relevant_counter_snapshot": {"dma_overflow_events": 1}
     }
     ```
4. **Desktop UI Display:**
   - Red badge `AF-STR-006 [STREAMING] REPORTED_BY_FIRMWARE` appears in Diagnostics Drawer.
   - Root-Cause Assistant displays:
     > *"Hypothesis: ESP-IDF I2S DMA descriptor queue exhausted during 48 kHz ingestion."*
     > *"Action: Increase `dma_desc_num` from 4 to 8 in firmware config."*

---

## 5. PHYSICAL USB-OTG VS USB SERIAL/JTAG CONNECTOR GUIDELINES

On purchased ESP32-S3 development boards (such as N16R8 dual-Type-C boards):
- **Port labeled "USB" (GPIO 19/20):** Native USB-OTG CDC-ACM. This is the **target interface** for Canonical Protocol v0.1 (`0x303A:0x1001`).
- **Port labeled "UART" / "COM":** USB Serial/JTAG PHY (`0x303A:0x1002`) or external CH340/CP2102.
  - Used for firmware flashing (`idf.py flash`) and bootloader monitor.
  - Does **not** carry 48 kHz audio stream.

If the board is plugged into the UART port during bring-up, the Host USB Discovery Doctor detects `0x1002` or `CH340` and prompts:
> *"ESP32-S3 Serial/JTAG port detected on COMx. If this is a dual-USB board, connect USB cable to the native USB-OTG port for 48 kHz audio acquisition."*

---

## 6. JOINT BRING-UP CHECKLIST FOR HARDWARE ARRIVAL

1. [ ] Connect data-capable USB cable to ESP32-S3 Native USB port.
2. [ ] Open AuscultaForge Desktop -> Device View -> Click **"Scan USB Bus"**.
3. [ ] Verify `0x303A:0x1001` appears under "Enumerated Serial Hardware".
4. [ ] In Protocol Lab, run:
   ```bash
   python tools/protocol_lab/module_b_package/verify_g1_bringup.py --port COMx --seconds 5
   ```
5. [ ] Confirm HELLO handshake nonce matches and session transitions to `READY`.
6. [ ] Confirm START handshake establishes `session_id != 0`.
7. [ ] Ingest 5 seconds of audio frames; verify zero CRC failures and zero sequence gaps.
8. [ ] Verify STOP_ACK reconciles exact sample counts (`accepted_samples == queued_samples`).
9. [ ] Export diagnostics support bundle (`POST /api/diagnostics/export`) as physical G1 artifact.
