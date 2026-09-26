# Team Meeting & Hardware Engineering Decisions

**Date:** 2026-09-26  
**Scope:** Phase-1 Hardware Baseline, Responsibilities, Wire Protocol Scope, and Sprint-1 Execution Plan  
**Status:** Approved Team Decisions  

---

## 1. Hardware Baseline Decisions

The team has officially agreed on the following baseline decisions for Phase 1:

1. **MCU Platform:**
   - Finalized as **ESP32-S3-WROOM**.
2. **Phase-1 Transport:**
   - **Wired Native USB only.**
   - Wireless transport (**Wi-Fi and BLE**) is explicitly **out of scope** for Phase 1.
3. **Initial Prototype Signal Chain:**
   $$\text{I2S MEMS Microphone Breakout} \longrightarrow \text{ESP32-S3 Development Board} \longrightarrow \text{Native USB} \longrightarrow \text{Host PC}$$
4. **Microphone Candidates for Physical Bench Comparison:**
   - **INMP441**
   - **ICS-43434** or **ICS-43432**
   - *Note:* The final microphone model is **NOT** selected yet. Bench acoustic evaluation will govern the final choice.
5. **Acoustic Head & PCB Interfacing:**
   - The future custom PCB will provide a configurable **~6-pin I2S microphone header/jumper arrangement** to support candidate swapping rather than locking down one microphone footprint prematurely.
6. **Sampling & Stream Parameters:**
   - Initial acquisition target: **~4 kHz** sample rate.
   - Bit depth: **16-bit** or **24-bit** candidate (not finalized).
   - DMA block size / frame length: **Not finalized**; will be experimentally selected based on DMA FIFO behavior and end-to-end latency.
7. **Fabrication Milestone Gate:**
   - Custom PCB fabrication tape-out will occur **only after** the dev-board + acoustic phantom proof-of-concept succeeds.

---

## 2. USB Transport & Framing Decisions

- **Transport Technology:** Finalized as **Native USB** (ESP32-S3 USB OTG / USB Serial/JTAG or TinyUSB).
- **USB Device Class & Wire Encoding:** **NOT finalized.**
- **Framing & Protocol Design:**
   - Host/device framing remains Ege's responsibility as a protocol design task.
   - Conceptual packet fields identified:
     1. Start / Sync Word
     2. Sequence Number
     3. Timestamp
     4. Sample Payload
     5. Status / Error Flags
     6. CRC
   - Byte widths, endianness, fixed vs variable packet size, CRC polynomial, USB endpoint type (CDC-ACM vs vendor bulk), and delimiter rules remain **unresolved protocol design items** pending initial testing.

---

## 3. Updated Team Ownership & Responsibilities

| Team Member | Area | Core Responsibilities |
|---|---|---|
| **Ozan** | Hardware & Schematic | - Hardware component selection<br>- Altium schematic / digital hardware skeleton<br>- Native USB hardware routing<br>- I2S routing and configurable header<br>- LDO / power regulation<br>- PCB layout<br>- Dev-board / breadboard physical integration |
| **Kaan** | Power & Acoustic Phantom | - MCP73831 + PFET + Schottky power-path reference design & integration support<br>- Acoustic phantom physical system & test chamber<br>- Speaker / exciter setup<br>- Acoustic / mechanical coupling<br>- Reference PCG playback setup<br>- Phantom test procedure & repeatability |
| **Ege** | Firmware, PC Core, DSP & QA | - ESP32 firmware development<br>- I2S + DMA acquisition firmware<br>- Native USB firmware & PC data transport<br>- MCU-to-PC packet/protocol design<br>- PC software/backend architecture<br>- Real-time DSP & metrics<br>- UI integration & state management<br>- CRC & data integrity validation<br>- GitHub repository management |

---

## 4. Phase-1 Milestone

- **Target Date:** Last week of October 2026
- **Milestone Goal:**
  A known reference PCG signal played through the acoustic phantom must be acquired by the physical prototype (I2S microphone + ESP32-S3 dev board + Native USB) and displayed/recorded on the PC without clipping or sample loss.
- **Verification Gate:**
  Quantitative reference-vs-capture metrics (cross-correlation, spectral similarity, SNR, latency) must be generated using the existing AuscultaForge validation framework (`software/pcg_core/validation.py`) before authorizing PCB tape-out.

---

## 5. Sprint-1 Commitments

- **Ozan:**
  - Obtain candidate microphone breakout modules (INMP441, ICS-43434/43432) and ESP32-S3 development board.
  - Complete ERC-clean Altium schematic for relevant Phase-1 hardware (ESP32-S3 skeleton, LDO, I2S microphone header, Native USB connector).
- **Kaan:**
  - Deliver MCP73831 + PFET + Schottky power-path reference schematic and integration notes.
  - Source acoustic phantom materials and assemble speaker/exciter setup.
  - Conduct first acoustic isolation and coupling experiment.
- **Ege:**
  - Maintain repository foundation and software architecture.
  - Develop ESP32-S3 Native USB dummy-data streaming firmware.
  - Build/adapt PC application ingestion pipeline capable of receiving, parsing, and plotting the dummy stream.

---

## 6. Unresolved Technical Items & Open Questions

1. **Wire Encoding & Endpoint:** TinyUSB CDC-ACM virtual serial stream vs Vendor-specific Bulk transfer.
2. **Audio Sample Bit Depth:** 16-bit signed PCM vs 24-bit/32-bit unpacked PCM over I2S DMA.
3. **Packet Sizing:** Determining optimal chunk size (~64 to 256 samples per packet) balancing packet overhead against host audio buffer latency.
4. **CRC Scheme:** CRC-16 vs CRC-32 trade-off on MCU computation cycles vs error detection guarantees.
5. **Microphone Evaluation:** Empirical SNR and frequency response comparison between INMP441 and ICS-43434 inside the phantom test rig.
