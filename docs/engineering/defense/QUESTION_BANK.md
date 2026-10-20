# AuscultaForge — Comprehensive Academic Defense Question Bank (105 Questions)
**Document ID:** `AF-DEFENSE-QBANK-V01`  
**Classification:** `ACADEMIC_DEFENSE` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Target Candidate:** Ege Çağın Tepe (Module C Owner)  
**Total Formulated Questions:** **105 Questions** (Categorized across 10 Technical Domains)

---

## Domain Index
1. [Domain 1: C Programming & Bitwise Arithmetic (Q1–Q12)](#domain-1-c-programming--bitwise-arithmetic)
2. [Domain 2: Embedded Systems, ESP32-S3 & FreeRTOS (Q13–Q24)](#domain-2-embedded-systems-esp32-s3--freertos)
3. [Domain 3: USB Protocol & Transport Engineering (Q25–Q34)](#domain-3-usb-protocol--transport-engineering)
4. [Domain 4: Digital Signal Processing (DSP) & Filtering (Q35–Q48)](#domain-4-digital-signal-processing-dsp--filtering)
5. [Domain 5: Spectral Analysis & Welch PSD (Q49–Q58)](#domain-5-spectral-analysis--welch-psd)
6. [Domain 6: Acoustic Metrology & SISO System ID (Q59–Q70)](#domain-6-acoustic-metrology--siso-system-id)
7. [Domain 7: Heart Sound Segmentation & Machine Learning (Q71–Q82)](#domain-7-heart-sound-segmentation--machine-learning)
8. [Domain 8: Python Backend & FastAPI Architecture (Q83–Q92)](#domain-8-python-backend--fastapi-architecture)
9. [Domain 9: Frontend Architecture & Real-Time Canvas (Q93–Q100)](#domain-9-frontend-architecture--real-time-canvas)
10. [Domain 10: Academic Governance, Ethics & Ownership (Q101–Q105)](#domain-10-academic-governance-ethics--ownership)

---

## Domain 1: C Programming & Bitwise Arithmetic

### Q1: What is the exact difference between `int32_t` and `long` in standard C?
* **Difficulty:** Foundation
* **Expected Answer:** `int32_t` (from `<stdint.h>`) is guaranteed by the ISO C standard to be an exact-width signed two's-complement integer of exactly 32 bits across all conforming platforms. `long` has an architecture-dependent width (32 bits on 32-bit platforms and Windows 64-bit LLP64, but 64 bits on Linux 64-bit LP64).
* **Underlying Concept:** Fixed-width integer portability.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h`
* **Follow-up Question:** What happens if you serialize `long` directly into a binary file shared across Linux and Windows?
* **Common Incorrect Response:** "They are always identical 32-bit integers." (Incorrect: on 64-bit Linux, `long` is 64 bits).

### Q2: Why is left-shifting a negative signed integer undefined behavior in C99/C11?
* **Difficulty:** Advanced
* **Expected Answer:** Under ISO C99 §6.5.7/4 and C11 §6.5.7/4, if the operand has a signed type and negative value, the behavior of `<<` is undefined because early computer architectures supported one's-complement and sign-magnitude arithmetic where shifting a sign bit could trigger hardware trap representations.
* **Underlying Concept:** C standard undefined behavior.
* **Code Reference:** `docs/engineering/code-atlas/C_LANGUAGE_FOUNDATIONS.md`
* **Follow-up Question:** How does AuscultaForge avoid this trap when manipulating 24-bit audio?
* **Common Incorrect Response:** "It just shifts in ones." (Incorrect: it is undefined; optimizing compilers can legally eliminate the code).

### Q3: How do you sign-extend a 24-bit negative integer stored in a 32-bit variable without invoking undefined behavior?
* **Difficulty:** Intermediate
* **Expected Answer:** Cast the 24-bit value to `uint32_t`, test if bit 23 is set (`raw & 0x00800000U`), and if true, bitwise OR with `0xFF000000U` to set bits 31..24 to 1s, then cast the result to `int32_t`.
* **Underlying Concept:** Two's-complement sign extension.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h` (`pack_and_align_sample`)
* **Follow-up Question:** What is the hexadecimal representation of $-1$ in a 24-bit integer, and what does it become after 32-bit sign extension?
* **Common Incorrect Response:** "You just do `val << 8 >> 8` on an `int32_t`." (Incorrect: invokes undefined behavior if `val < 0`).

### Q4: Explain the difference between Little-Endian and Big-Endian byte layout for `0x12345678`.
* **Difficulty:** Foundation
* **Expected Answer:** In Little-Endian (ESP32-S3 and x86-64), the least significant byte `0x78` is stored at the lowest byte address ($A$), followed by `0x56` ($A+1$), `0x34` ($A+2$), and `0x12` ($A+3$). In Big-Endian, the most significant byte `0x12` is stored at address $A$.
* **Underlying Concept:** Endianness in memory and wire serialization.
* **Code Reference:** `docs/engineering/code-atlas/C_LANGUAGE_FOUNDATIONS.md`
* **Follow-up Question:** How does our Python Layer 3 unpacker specify Little-Endian byte order?
* **Common Incorrect Response:** "Little-Endian means the smallest number comes first." (Imprecise: it refers to byte significance, not numerical magnitude).

### Q5: What is the purpose of the `U` suffix in integer literals like `0x00FFFFFFU`?
* **Difficulty:** Foundation
* **Expected Answer:** The `U` suffix explicitly declares the literal as having an `unsigned` integer type, preventing accidental signed integer promotion and avoiding compiler warnings when performing bitwise operations with `uint32_t`.
* **Underlying Concept:** Literal typing and implicit type promotion.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h`
* **Follow-up Question:** What warning does GCC emit if you bitwise-AND a signed integer with a large hex literal without `U`?
* **Common Incorrect Response:** "It means universal." (Incorrect: it stands for unsigned).

### Q6: How does two's-complement arithmetic handle overflow?
* **Difficulty:** Intermediate
* **Expected Answer:** In two's complement, adding two large positive numbers whose sum exceeds $+2^{N-1}-1$ sets the MSB to 1, wrapping the result around into a large negative number. In standard C, signed integer overflow is undefined behavior, whereas unsigned integer overflow is guaranteed to wrap modulo $2^N$.
* **Underlying Concept:** Arithmetic overflow vs. modular wraparound.
* **Code Reference:** `docs/engineering/code-atlas/C_LANGUAGE_FOUNDATIONS.md`
* **Follow-up Question:** Why are packet sequence counters always declared as `uint16_t` or `uint32_t` rather than signed types?
* **Common Incorrect Response:** "Signed overflow always wraps around safely." (Incorrect: signed overflow is undefined in C).

### Q7: What is the difference between a static array allocation and a dynamic `malloc()` on an embedded microcontroller?
* **Difficulty:** Foundation
* **Expected Answer:** Static arrays are allocated at compile time in the BSS or Data segment with fixed memory addresses, guaranteeing zero runtime allocation failure and zero heap fragmentation. `malloc()` allocates from the heap at runtime, which can fail if memory is exhausted and causes heap fragmentation over prolonged continuous streaming.
* **Underlying Concept:** Embedded memory management.
* **Code Reference:** `tools/esp32_bench_example/main/main.c`
* **Follow-up Question:** Why does our firmware use static queues for audio buffers?
* **Common Incorrect Response:** "Malloc is always better because it saves RAM when not running." (Incorrect: memory fragmentation can crash an MCU after hours of streaming).

### Q8: What does the `volatile` keyword tell a C compiler in the context of DMA descriptors?
* **Difficulty:** Advanced
* **Expected Answer:** `volatile` informs the compiler that the value of the variable may be changed at any time by hardware outside the control of the current code thread (such as a DMA controller or an ISR). It forces the compiler to re-read the variable from physical memory on every access rather than caching it in a CPU register.
* **Underlying Concept:** Compiler optimization and hardware memory synchronization.
* **Code Reference:** `docs/engineering/code-atlas/ESP32_RUNTIME_ARCHITECTURE.md`
* **Follow-up Question:** What bug occurs if a DMA descriptor's `owner` bit is NOT marked `volatile`?
* **Common Incorrect Response:** "It makes the variable thread-safe." (Incorrect: volatile does not provide atomicity or mutex locks).

### Q9: Why is `sin()` evaluated using modulo reduction (`sample_index % period`) in `generate_sine_100hz_sample()`?
* **Difficulty:** Intermediate
* **Expected Answer:** Because `sample_index` grows continuously. As double-precision floats grow large ($> 10^7$), the spacing between representable floats increases, causing loss of precision in the lower bits when evaluating $\sin(2\pi f t)$. Modulo reduction onto $[0, 479]$ guarantees identical, cyclic numerical precision indefinitely.
* **Underlying Concept:** Floating-point precision degradation over time.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h`
* **Follow-up Question:** What is the exact period in samples of a 100 Hz tone sampled at 48,000 Hz?
* **Common Incorrect Response:** "To save CPU time." (Incorrect: it is for floating-point phase accuracy).

### Q10: What is a strict-aliasing violation in C?
* **Difficulty:** Expert
* **Expected Answer:** ISO C (§6.5/7) specifies that two pointers of different types (with few exceptions, like `char*`) cannot point to the same memory location. Casting `uint8_t*` buffer directly to `int32_t*` and dereferencing it violates strict aliasing, allowing optimizing compilers to reorder reads and writes, generating corrupted machine code.
* **Underlying Concept:** C strict-aliasing rules.
* **Code Reference:** `docs/engineering/code-atlas/C_LANGUAGE_FOUNDATIONS.md`
* **Follow-up Question:** How should you portably extract a 32-bit integer from a byte buffer?
* **Common Incorrect Response:** "Just cast `(int32_t*)ptr`." (Incorrect: violates aliasing and can cause unaligned bus faults).

### Q11: Explain how the symmetric rounding formula `val >= 0.0 ? (int32_t)(val + 0.5) : (int32_t)(val - 0.5)` works.
* **Difficulty:** Intermediate
* **Expected Answer:** Standard C type-casting `(int32_t)val` truncates towards zero (e.g. $+1.9 \to +1$, $-1.9 \to -1$). Adding $+0.5$ to positive numbers shifts values $\ge 0.5$ across the integer threshold, rounding to nearest. Subtracting $0.5$ from negative numbers shifts values $\le -0.5$ downwards, ensuring symmetrical rounding around zero without DC bias.
* **Underlying Concept:** Symmetrical integer quantization.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h`
* **Follow-up Question:** What happens to $-0.6$ if you just do `(int32_t)(val + 0.5)`?
* **Common Incorrect Response:** "It truncates properly." (Incorrect: $+0.5$ on $-0.6$ gives $-0.1$, which truncates to $0$, biasing the wave upwards).

### Q12: Why are header guards (`#ifndef HEADER_H ... #endif`) mandatory in C?
* **Difficulty:** Foundation
* **Expected Answer:** To prevent recursive or multiple inclusion of the same header file within a single translation unit, which causes duplicate typedef, struct, or macro definition errors during compilation.
* **Underlying Concept:** C preprocessor compilation mechanics.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h`
* **Follow-up Question:** What is the non-standard but widely supported alternative directive?
* **Common Incorrect Response:** "To prevent linking errors." (Incorrect: preprocessor prevents compilation errors, not linker errors).

---

## Domain 2: Embedded Systems, ESP32-S3 & FreeRTOS

### Q13: Why is `512 samples + vTaskDelay(11 ms)` in software NOT guaranteed 48 kHz acquisition?
* **Difficulty:** Advanced
* **Expected Answer:** `vTaskDelay` delays by an integer number of FreeRTOS ticks. At standard $100 \text{ Hz}$ tick rate (`portTICK_PERIOD_MS = 10 ms`), an 11 ms delay rounds to 20 ms (2 ticks) or fluctuates with scheduler jitter. True 48.000 kHz continuous sampling requires hardware I2S bit clocks and DMA interrupts to pace acquisition.
* **Underlying Concept:** FreeRTOS tick quantization vs. hardware DMA pacing.
* **Code Reference:** `tools/esp32_bench_example/README.md`
* **Follow-up Question:** How does the production firmware in Module B achieve strict 48.000 kHz pacing?
* **Common Incorrect Response:** "Because 11 ms equals 512 / 48000." (Incorrect: 512 / 48000 is 10.667 ms, and software delays suffer from tick quantization).

### Q14: How does linked-list DMA ping-pong buffering work on the ESP32-S3?
* **Difficulty:** Advanced
* **Expected Answer:** Two DMA descriptors (A and B) point to separate SRAM buffers. Descriptor A's `next` pointer references B, and B's references A. The hardware I2S DMA fills Buffer A; upon completion, it asserts an interrupt and automatically begins filling Buffer B without CPU intervention. The CPU processes Buffer A while Buffer B is filling.
* **Underlying Concept:** Zero-copy hardware double-buffering.
* **Code Reference:** `docs/engineering/code-atlas/ESP32_RUNTIME_ARCHITECTURE.md`
* **Follow-up Question:** What happens if the CPU takes longer than $10.67 \text{ ms}$ to process Buffer A?
* **Common Incorrect Response:** "DMA waits for the CPU to finish." (Incorrect: DMA continues and overwrites the buffer, causing data loss).

### Q15: Why are tasks pinned to specific cores (`Core 0` vs `Core 1`) in the ESP32-S3 architecture?
* **Difficulty:** Intermediate
* **Expected Answer:** Core 1 is dedicated to time-critical I2S DMA interrupt handling and audio acquisition. Core 0 is dedicated to the TinyUSB stack, system housekeeping, and background tasks. Pining tasks prevents USB packet bursts on Core 0 from interrupting real-time audio sampling on Core 1.
* **Underlying Concept:** Asymmetric task pinning in SMP FreeRTOS.
* **Code Reference:** `docs/engineering/code-atlas/ESP32_RUNTIME_ARCHITECTURE.md`
* **Follow-up Question:** Which FreeRTOS function is used to pin a task to a core?
* **Common Incorrect Response:** "FreeRTOS automatically balances tasks evenly." (Incorrect: automatic balancing can cause cache thrashing and interrupt latency).

### Q16: What is the exact frequency of the I2S Bit Clock (`SCK`) for a mono 24-bit microphone transmitting in standard 32-bit dual-slot format at 48 kHz?
* **Difficulty:** Intermediate
* **Expected Answer:** Standard I2S frames contain two slots (Left and Right), each 32 bits wide. Therefore:
  $$f_{\text{SCK}} = 2 \times 32 \times 48,000 = 3,072,000 \text{ Hz} = 3.072 \text{ MHz}$$
* **Underlying Concept:** I2S bus timing and clock division.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** What is the frequency of the Word Select (`WS`) line?
* **Common Incorrect Response:** "$1.152 \text{ MHz}$ because it's 24 bits times 48 kHz." (Incorrect: I2S uses 32-bit channel slots and always clocks two channels).

### Q17: What physical pin routing issue must be checked on the DirencNet N16R8 DevKit board?
* **Difficulty:** Intermediate
* **Expected Answer:** Many commercial ESP32-S3 clone boards only route out the USB-UART bridge (CH340/CP2102) to a single Type-C connector, leaving the native USB OTG PHY (`GPIO 19` D- and `GPIO 20` D+) unconnected. Physical continuity must be verified to ensure the second "USB" port connects directly to GPIO 19/20.
* **Underlying Concept:** Hardware bring-up and commercial clone verification.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** What is the workaround if the DirencNet board has only a single USB-UART port?
* **Common Incorrect Response:** "All ESP32-S3 DevKits have functional dual USB ports." (Incorrect: clones frequently omit native USB routing).

### Q18: What is the purpose of DTR line state checking in `tools/esp32_bench_example/main/main.c`?
* **Difficulty:** Intermediate
* **Expected Answer:** It pauses USB streaming when the host PC application is closed. The firmware calls `tud_cdc_connected()` to check if the host has asserted Data Terminal Ready (DTR). If DTR is false, the MCU sleeps, preventing USB FIFO buffer saturation and dropped packet storms.
* **Underlying Concept:** Hardware flow control and connection state synchronization.
* **Code Reference:** `tools/esp32_bench_example/main/main.c`
* **Follow-up Question:** What happens if the MCU streams continuously without checking DTR?
* **Common Incorrect Response:** "DTR controls baud rate." (Incorrect: DTR is a virtual modem control line).

### Q19: Why does the INMP441 MEMS microphone have an `L/R` pin, and what should it be tied to?
* **Difficulty:** Foundation
* **Expected Answer:** The `L/R` pin configures whether the microphone outputs its 24-bit data during the Left Channel phase (`WS = 0`) or Right Channel phase (`WS = 1`). Tying `L/R` to GND configures it for the Left Channel.
* **Underlying Concept:** I2S channel selection.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** What does the microphone do during the opposite channel phase?
* **Common Incorrect Response:** "It ties left and right audio together into mono." (Incorrect: it tri-states its output pin during the other channel).

### Q20: What is the voltage level of the ESP32-S3 I/O pins, and is the INMP441 compatible with 5V?
* **Difficulty:** Foundation
* **Expected Answer:** ESP32-S3 I/O pins operate at $3.3 \text{ V}$ CMOS logic. The INMP441 requires a $3.3 \text{ V}$ power supply ($1.62 \text{ V to } 3.63 \text{ V}$). Connecting 5V VBUS directly to the INMP441 will permanently destroy the MEMS sensor.
* **Underlying Concept:** Power rails and logic level compatibility.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** Where on the DevKit should the INMP441 VDD pin be connected?
* **Common Incorrect Response:** "5V pin because USB is 5V." (Incorrect: 5V destroys the 3.3V MEMS IC).

### Q21: What is the difference between internal SRAM and Octal PSRAM on the ESP32-S3?
* **Difficulty:** Advanced
* **Expected Answer:** Internal SRAM ($512 \text{ KB}$) is on-chip memory capable of single-cycle access and direct DMA operations. PSRAM ($8 \text{ MB}$ on N16R8) is external RAM accessed via high-speed SPI cache; it has higher latency and cannot directly support I2S DMA transfers without specific cache alignment.
* **Underlying Concept:** Embedded memory hierarchy and DMA constraints.
* **Code Reference:** `docs/engineering/code-atlas/ESP32_RUNTIME_ARCHITECTURE.md`
* **Follow-up Question:** Where must DMA buffers be allocated in memory?
* **Common Incorrect Response:** "In PSRAM because it is bigger." (Incorrect: DMA controllers require internal DMA-capable SRAM).

### Q22: What is an ISR (Interrupt Service Routine) and what are its execution restrictions in FreeRTOS?
* **Difficulty:** Intermediate
* **Expected Answer:** An ISR is a hardware-triggered function that executes immediately upon an event (e.g. DMA buffer full). Restrictions: It must not call blocking FreeRTOS APIs (must use `FromISR` variants like `xQueueSendFromISR`), must not allocate dynamic memory (`malloc`), and must execute as quickly as possible to avoid priority inversion.
* **Underlying Concept:** Real-time interrupt servicing.
* **Code Reference:** `docs/engineering/code-atlas/ESP32_RUNTIME_ARCHITECTURE.md`
* **Follow-up Question:** What happens if you call `vTaskDelay()` inside an ISR?
* **Common Incorrect Response:** "It delays the interrupt." (Incorrect: crashes the operating system immediately).

### Q23: Why do we recommend jumper wires $< 10 \text{ cm}$ between INMP441 and ESP32-S3?
* **Difficulty:** Intermediate
* **Expected Answer:** The I2S bit clock operates at $3.072 \text{ MHz}$ with fast sub-nanosecond rise times. Long breadboard wires introduce parasitic inductance and capacitance, causing transmission line reflections, clock ringing, and double-triggering of bit transitions.
* **Underlying Concept:** High-speed digital signal integrity.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** What artifact appears in the audio if `SCK` has reflections?
* **Common Incorrect Response:** "The sound gets quieter." (Incorrect: causes bit-slip, creating loud random digital crackling noise).

### Q24: What is the purpose of the watchdog timer in FreeRTOS?
* **Difficulty:** Intermediate
* **Expected Answer:** To detect and recover from software deadlocks, infinite loops, or starved tasks. If a high-priority task fails to yield or kick the watchdog within the configured timeout, the watchdog triggers a system reset.
* **Underlying Concept:** Embedded fault recovery.
* **Code Reference:** `docs/engineering/architecture/FAILURE_RECOVERY.md`
* **Follow-up Question:** Which task feeds the IDLE task watchdog?
* **Common Incorrect Response:** "It shuts down the board to save power." (Incorrect: it resets the MCU to recover from crashes).

---

## Domain 3: USB Protocol & Transport Engineering

### Q25: Why did AuscultaForge select USB CDC-ACM instead of USB Audio Class (UAC)?
* **Difficulty:** Advanced
* **Expected Answer:** USB Audio Class (UAC) exposes the device as a Windows microphone, subjecting the stream to OS-level sample rate conversion, automatic gain control (AGC), and volume scaling, corrupting raw scientific integer words. Furthermore, UAC cannot easily carry custom telemetry (packet sequence numbers, drop flags, and hardware timestamps). CDC-ACM provides direct, unadulterated byte access.
* **Underlying Concept:** OS audio stack corruption vs. virtual COM port transparency.
* **Code Reference:** `docs/engineering/decisions/ADR-0003-usb-cdc-acm-transport.md`
* **Follow-up Question:** Which Windows in-box driver binds to CDC-ACM?
* **Common Incorrect Response:** "UAC is too slow." (Incorrect: UAC has plenty of bandwidth, but corrupts scientific signal integrity).

### Q26: What is the mathematical polynomial of CRC-16-CCITT and what errors does it detect?
* **Difficulty:** Advanced
* **Expected Answer:** Polynomial $G(x) = x^{16} + x^{12} + x^5 + 1$ (hexadecimal `0x1021`, init `0xFFFF`). It detects 100% of all single-bit errors, 100% of all double-bit errors, 100% of all odd numbers of bit errors, and all burst errors up to 16 bits in length.
* **Underlying Concept:** Cyclic Redundancy Checks and error detection theory.
* **Code Reference:** `tools/c_golden_vectors/golden_common.h`
* **Follow-up Question:** Can CRC-16 correct corrupted bits?
* **Common Incorrect Response:** "It detects and fixes errors." (Incorrect: CRC detects errors, it does not correct them like ECC/Reed-Solomon).

### Q27: How does the Layer 2 Frame Decoder recover when garbage bytes are received on the wire?
* **Difficulty:** Intermediate
* **Expected Answer:** The decoder drops the corrupted frame, increments `corrupt_frame_count`, advances its read pointer by 1 byte, and hunts forward through the byte buffer scanning for the 2-byte preamble sync word `0xAA55`. Once found, it realigns frame parsing to the new boundary.
* **Underlying Concept:** Frame synchronization and resynchronization.
* **Code Reference:** `software/pcg_app/transport.py`
* **Follow-up Question:** What test verifies this behavior?
* **Common Incorrect Response:** "It resets the COM port." (Incorrect: port remains open; stream resynchronizes in software).

### Q28: What is the gross signaling bitrate of USB 2.0 Full-Speed, and what percentage is used by AuscultaForge?
* **Difficulty:** Intermediate
* **Expected Answer:** Full-Speed USB operates at $12.000 \text{ Mbps}$. AuscultaForge streams 48,000 samples/s at 4 bytes/sample ($1.536 \text{ Mbps}$ payload). With proposed 40-byte framing overhead, data rate is $1.92 \text{ Mbps}$. This consumes $\approx 16\text{--}20\%$ of bus capacity, leaving $> 80\%$ bandwidth margin.
* **Underlying Concept:** USB bandwidth budgeting.
* **Code Reference:** `docs/engineering/architecture/SYSTEM_ARCHITECTURE.md`
* **Follow-up Question:** What is the maximum packet size for Full-Speed bulk endpoints?
* **Common Incorrect Response:** "$480 \text{ Mbps}$." (Incorrect: $480 \text{ Mbps}$ is High-Speed USB; ESP32-S3 internal PHY is Full-Speed $12 \text{ Mbps}$).

### Q29: What Win32 error occurs when a USB cable is pulled mid-stream?
* **Difficulty:** Intermediate
* **Expected Answer:** The Windows kernel invalidates the file handle, returning `ERROR_DEVICE_NOT_CONNECTED` (Win32 error code 1167). `pyserial` translates this into `serial.SerialException`.
* **Underlying Concept:** OS device disconnect handling.
* **Code Reference:** `software/pcg_app/device_runtime.py`
* **Follow-up Question:** How does `DeviceRuntime` react to `SerialException`?
* **Common Incorrect Response:** "The read function just returns 0 bytes." (Incorrect: raises an exception that must be trapped).

### Q30: What is bit-stuffing in USB physical signaling?
* **Difficulty:** Advanced
* **Expected Answer:** Because USB uses Non-Return-to-Zero Inverted (NRZI) encoding where clock transitions only occur on zero bits, a long sequence of consecutive ones would cause receiver clock drift. The USB transmitter automatically stuffs a `0` bit after any sequence of six consecutive `1`s.
* **Underlying Concept:** Physical line coding and clock recovery.
* **Code Reference:** `docs/engineering/code-atlas/USB_PROTOCOL_ENGINEERING.md`
* **Follow-up Question:** Is bit-stuffing handled in C code or hardware?
* **Common Incorrect Response:** "It encrypts the data." (Incorrect: it guarantees clock synchronization transitions).

### Q31: What are USB Endpoints, and which endpoints are used in AuscultaForge?
* **Difficulty:** Intermediate
* **Expected Answer:** Endpoints are hardware FIFO buffers in the USB peripheral acting as sources or sinks of communication. AuscultaForge uses Endpoint 0 (EP0 IN/OUT) for USB enumeration and control requests, and Endpoint 1 IN (EP1 IN) as a bulk endpoint for streaming audio packets to the host.
* **Underlying Concept:** USB endpoint architecture.
* **Code Reference:** `docs/engineering/code-atlas/USB_PROTOCOL_ENGINEERING.md`
* **Follow-up Question:** What is the difference between an IN endpoint and an OUT endpoint?
* **Common Incorrect Response:** "IN means into the MCU." (Incorrect: USB naming is host-centric; IN means into the host PC).

### Q32: What is the role of Vendor ID (VID) and Product ID (PID) in USB enumeration?
* **Difficulty:** Foundation
* **Expected Answer:** VID (16-bit) identifies the silicon manufacturer (assigned by USB-IF; `0x303A` for Espressif Systems). PID (16-bit) identifies the specific product model (`0x4001` for TinyUSB CDC). The host OS uses VID/PID to match drivers.
* **Underlying Concept:** USB device identification.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** Where in Windows Device Manager do you view VID and PID?
* **Common Incorrect Response:** "They are randomly generated on boot." (Incorrect: fixed in USB device descriptors).

### Q33: Why does `ByteTransportReader` handle chunked/partial reads?
* **Difficulty:** Intermediate
* **Expected Answer:** Serial port `read(N)` operations over USB are non-atomic; the operating system returns whatever bytes are currently in the kernel serial FIFO. If 40 bytes are requested, `read()` may return 12 bytes. The transport layer must buffer partial reads until a full frame is assembled.
* **Underlying Concept:** Non-blocking streaming I/O.
* **Code Reference:** `software/pcg_app/transport.py`
* **Follow-up Question:** What happens if code assumes `read(40)` always returns exactly 40 bytes?
* **Common Incorrect Response:** "Serial reads always wait until all bytes arrive." (Incorrect: partial reads cause corrupted framing).

### Q34: What is the purpose of the 2-byte `0xAA55` sync word?
* **Difficulty:** Foundation
* **Expected Answer:** To provide a distinctive bit pattern ($1010101001010101_2$) with alternating transitions that rarely appears in natural audio data, allowing the parser to locate the start of a packet in an arbitrary byte stream.
* **Underlying Concept:** Frame synchronization.
* **Code Reference:** `docs/protocol/PROTOCOL_DRAFT.md`
* **Follow-up Question:** What happens if the payload randomly contains `0xAA55`?
* **Common Incorrect Response:** "The parser crashes." (Incorrect: the parser validates packet length and CRC before accepting a frame).

---

## Domain 4: Digital Signal Processing (DSP) & Filtering

### Q35: Why does AuscultaForge use Second-Order Sections (SOS) instead of direct-form $[b, a]$ filter transfer functions?
* **Difficulty:** Advanced
* **Expected Answer:** Direct-form higher-order IIR filters have coefficients that span orders of magnitude. Small rounding errors in high-order polynomial roots cause poles to shift outside the unit circle, resulting in instability. SOS cascades second-order biquads, isolating pole pairs and guaranteeing numerical stability.
* **Underlying Concept:** Finite word-length effects and IIR filter stability.
* **Code Reference:** `software/pcg_core/dsp.py`
* **Follow-up Question:** Which SciPy function converts $[b, a]$ into SOS?
* **Common Incorrect Response:** "SOS is faster." (Incorrect: direct form is slightly faster, but SOS is numerically stable).

### Q36: How does `StreamingBandpass` maintain filter state across contiguous 512-sample blocks?
* **Difficulty:** Advanced
* **Expected Answer:** It stores the final delay state vector $z_k$ returned by `scipy.signal.sosfilt(sos, x, zi=self._zi)` and passes it as the initial condition $z_i$ into the next block. This ensures identical output to filtering the entire continuous waveform in one batch, preventing edge transients.
* **Underlying Concept:** Causal block-based IIR filtering.
* **Code Reference:** `software/pcg_core/dsp.py`
* **Follow-up Question:** What artifact appears at block edges if $z_k$ is reset to zero between blocks?
* **Common Incorrect Response:** "It averages adjacent blocks." (Incorrect: it preserves the internal filter delay line registers).

### Q37: What is the difference between causal streaming filtering (`sosfilt`) and zero-phase offline filtering (`sosfiltfilt`)?
* **Difficulty:** Intermediate
* **Expected Answer:** `sosfilt` operates forward in real-time on incoming samples, introducing causal phase shift and group delay ($\approx 3.2 \text{ ms}$). `sosfiltfilt` filters forward and backward in time, squaring the magnitude response ($|H(f)|^2$) and completely eliminating phase distortion ($\phi(f) = 0$), but can only be run offline on recorded files.
* **Underlying Concept:** Filter causality and phase linearity.
* **Code Reference:** `docs/engineering/science/DSP_MATHEMATICS.md`
* **Follow-up Question:** Why can `sosfiltfilt` not be run in real-time streaming?
* **Common Incorrect Response:** "They produce identical outputs." (Incorrect: zero-phase filtering requires future samples).

### Q38: Define Root Mean Square (RMS) and explain how it differs from peak amplitude.
* **Difficulty:** Foundation
* **Expected Answer:** RMS is the square root of the mean squared sample values ($x_{\text{RMS}} = \sqrt{\frac{1}{N} \sum x^2[n]}$), representing the continuous electrical or acoustic energy of the signal. Peak amplitude is the maximum absolute sample value ($\max |x[n]|$).
* **Underlying Concept:** Signal energy vs. instantaneous extremum.
* **Code Reference:** `software/pcg_core/scientific/signal_quality.py`
* **Follow-up Question:** What is the ratio between peak and RMS called?
* **Common Incorrect Response:** "RMS is just the average value." (Incorrect: mean value of zero-centered audio is zero).

### Q39: What is Crest Factor and what does a high crest factor indicate in a phonocardiogram?
* **Difficulty:** Intermediate
* **Expected Answer:** Crest Factor is $C = x_{\text{peak}} / x_{\text{RMS}}$ (or $20 \log_{10}(C)$ in dB). In cardiac PCG, a high crest factor ($12\text{--}18 \text{ dB}$) indicates clean impulsive valve closures ($S_1, S_2$) separated by quiet intervals. A low crest factor ($< 8 \text{ dB}$) indicates continuous background friction or rubbing noise.
* **Underlying Concept:** Morphological signal quality metrics.
* **Code Reference:** `software/pcg_core/scientific/signal_quality.py`
* **Follow-up Question:** What is the crest factor of a pure sine wave?
* **Common Incorrect Response:** "High crest factor means the signal is clipped." (Incorrect: clipped signals have low crest factors near $0 \text{ dB}$).

### Q40: Formulate the Teager-Kaiser Energy Operator (TKEO) and state its mathematical property.
* **Difficulty:** Advanced
* **Expected Answer:** $\Psi[x[n]] = x^2[n] - x[n-1]x[n+1]$. For a sine wave $A \cos(\omega_0 n)$, $\Psi[x[n]] \approx A^2 \omega_0^2$. It reflects both the square of amplitude AND the square of frequency, making it sensitive to high-frequency murmurs and transient valve snaps.
* **Underlying Concept:** Non-linear energy operators.
* **Code Reference:** `software/pcg_core/scientific/envelopes.py`
* **Follow-up Question:** How many samples are lost at the boundary when evaluating TKEO?
* **Common Incorrect Response:** "It is just $x[n]^2$." (Incorrect: standard energy is $x^2$; TKEO uses three adjacent samples).

### Q41: What is the Hilbert transform and how is the analytic signal formed?
* **Difficulty:** Advanced
* **Expected Answer:** The Hilbert transform $\mathcal{H}\{x(t)\}$ shifts all positive frequency components by $-90^\circ$ ($-\pi/2$). The complex analytic signal is $z(t) = x(t) + j\mathcal{H}\{x(t)\} = A(t)e^{j\theta(t)}$. The Hilbert envelope is its magnitude $|z(t)| = \sqrt{x^2 + (\mathcal{H}\{x\})^2}$.
* **Underlying Concept:** Analytic signals and instantaneous envelope extraction.
* **Code Reference:** `software/pcg_core/scientific/envelopes.py`
* **Follow-up Question:** What is the spectrum of the analytic signal for negative frequencies?
* **Common Incorrect Response:** "It is a Fourier transform." (Incorrect: Hilbert transform operates in time domain and outputs a 90-degree phase-shifted time signal).

### Q42: What is the passband of the primary AuscultaForge bandpass filter and why?
* **Difficulty:** Foundation
* **Expected Answer:** $20 \text{ Hz}$ to $500 \text{ Hz}$. $20 \text{ Hz}$ rejects respiratory chest wall movement and handling friction. $500 \text{ Hz}$ captures all clinically relevant cardiac frequencies ($S_1, S_2$, murmurs) while attenuating ambient room noise and high-frequency harmonics.
* **Underlying Concept:** Acoustic bandpass selection.
* **Code Reference:** `software/pcg_core/dsp.py`
* **Follow-up Question:** Why are lung sounds ($> 500 \text{ Hz}$) excluded?
* **Common Incorrect Response:** "$0$ to $20,000 \text{ Hz}$." (Incorrect: audio above 500 Hz contains no cardiac information and elevates noise).

### Q43: What digital clipping threshold is enforced in `signal_quality.py`?
* **Difficulty:** Intermediate
* **Expected Answer:** A sample is flagged as clipped if $|x[n]| \ge 1.0 - 10^{-5}$ ($\approx 0.99999$ in normalized float scale).
* **Underlying Concept:** Digital full-scale boundary detection.
* **Code Reference:** `software/pcg_core/scientific/signal_quality.py`
* **Follow-up Question:** Why is the threshold $1.0 - 10^{-5}$ rather than strictly $1.0$?
* **Common Incorrect Response:** "Because 0.5 is full scale." (Incorrect: floating-point precision can place full-scale samples slightly below 1.0).

### Q44: What is the group delay of a digital filter?
* **Difficulty:** Intermediate
* **Expected Answer:** Group delay is the negative derivative of the filter phase response with respect to angular frequency: $\tau_g(\omega) = -\frac{d\phi(\omega)}{d\omega}$. It represents the temporal delay experienced by different frequency packets passing through the filter.
* **Underlying Concept:** Phase linearity and dispersion.
* **Code Reference:** `docs/engineering/science/DSP_MATHEMATICS.md`
* **Follow-up Question:** What type of filter has constant group delay?
* **Common Incorrect Response:** "It is the time it takes the computer to calculate the filter." (Incorrect: group delay is an intrinsic mathematical property of the filter transfer function).

### Q45: How does polyphase rational resampling work in `scipy.signal.resample_poly`?
* **Difficulty:** Advanced
* **Expected Answer:** To resample by rational factor $P/Q$, the algorithm conceptually upsamples by integer $P$ (zero-padding), filters with an anti-aliasing low-pass filter, and downsamples by integer $Q$ (decimating). Polyphase decomposition commutes filtering and decimation, executing filtering only at the lower rate for high efficiency.
* **Underlying Concept:** Multirate digital signal processing.
* **Code Reference:** `software/pcg_core/segmentation/preprocessing.py`
* **Follow-up Question:** What are $P$ and $Q$ when downsampling 48,000 Hz to 1,000 Hz?
* **Common Incorrect Response:** "It does linear interpolation between points." (Incorrect: linear interpolation causes aliasing; polyphase resampling applies ideal low-pass filtering).

### Q46: What is a homomorphic envelope and why is it used in heart sound analysis?
* **Difficulty:** Advanced
* **Expected Answer:** The homomorphic envelope transforms multiplicative signal components (excitation $\times$ vocal/chest tract) into additive components using the logarithm ($\ln(|x|)$), applies a low-pass filter to extract the slow amplitude modulation, and inverts via exponential ($\exp(\cdot)$).
* **Underlying Concept:** Homomorphic deconvolution.
* **Code Reference:** `software/pcg_core/segmentation/features.py`
* **Follow-up Question:** Who proposed this for PCG segmentation?
* **Common Incorrect Response:** "It is a Fourier transform." (Incorrect: it is log-envelope filtering).

### Q47: What is the Schmidt spike removal algorithm?
* **Difficulty:** Intermediate
* **Expected Answer:** It identifies high-amplitude impulse artifacts caused by sensor movement. It computes window maxima across 500 ms windows, finds the median of these maxima, and attenuates any sample exceeding $3 \times \text{median}$, preventing impulse spikes from dominating subsequent normalization.
* **Underlying Concept:** Non-linear artifact rejection.
* **Code Reference:** `software/pcg_core/segmentation/preprocessing.py`
* **Follow-up Question:** Why use the median of window maxima instead of the mean?
* **Common Incorrect Response:** "It deletes the noisy section." (Incorrect: it clips the spike amplitude while preserving time continuity).

### Q48: What is the difference between IIR and FIR filters in biomedical acoustics?
* **Difficulty:** Intermediate
* **Expected Answer:** FIR filters have finite impulse responses, are inherently stable, and can achieve exact linear phase, but require high orders ($N > 200$) and high compute latency. IIR filters achieve sharp roll-offs with much lower orders ($N = 4\text{--}8$), but introduce non-linear phase and require careful implementation (SOS) to avoid instability.
* **Underlying Concept:** Filter design trade-offs.
* **Code Reference:** `software/pcg_core/dsp.py`
* **Follow-up Question:** Why did AuscultaForge choose IIR Butterworth for streaming?
* **Common Incorrect Response:** "FIR filters are always better." (Incorrect: FIR latency is too high for real-time 60 FPS display).

---

## Domain 5: Spectral Analysis & Welch PSD

### Q49: Why is the Welch method superior to a single raw FFT periodogram for estimating Power Spectral Density?
* **Difficulty:** Intermediate
* **Expected Answer:** A single raw FFT periodogram is an inconsistent estimator whose variance does not decay to zero as record length increases ($\text{Var} \approx S^2$). Welch's method divides the signal into $K$ overlapping windowed segments and averages their periodograms, reducing variance by approximately $1/K$ and yielding a smooth, consistent PSD.
* **Underlying Concept:** Non-parametric spectral estimation consistency.
* **Code Reference:** `software/pcg_core/scientific/spectral.py`
* **Follow-up Question:** What is the trade-off of averaging $K$ segments?
* **Common Incorrect Response:** "It calculates higher frequencies." (Incorrect: it reduces variance at the expense of frequency resolution).

### Q50: Calculate the exact frequency bin resolution $\Delta f$ for $f_s = 48,000 \text{ Hz}$ and $N_{\text{FFT}} = 4,096$.
* **Difficulty:** Foundation
* **Expected Answer:**
  $$\Delta f = \frac{f_s}{N_{\text{FFT}}} = \frac{48,000 \text{ Hz}}{4,096} = 11.71875 \text{ Hz/bin}$$
* **Underlying Concept:** Fourier frequency quantization.
* **Code Reference:** `docs/engineering/science/SPECTRAL_ANALYSIS.md`
* **Follow-up Question:** Which bin index $k$ corresponds to $100 \text{ Hz}$?
* **Common Incorrect Response:** "$10 \text{ Hz}$." (Incorrect: $48000 / 4096 = 11.71875 \text{ Hz}$).

### Q51: Why is the Hann window chosen as the standard window in AuscultaForge spectral analysis?
* **Difficulty:** Intermediate
* **Expected Answer:** The Hann window provides a moderate main-lobe width ($1.44 \Delta f$) combined with a fast sidelobe roll-off rate of $-18 \text{ dB/octave}$ (first sidelobe at $-31.5 \text{ dB}$). This rapid decay prevents powerful low-frequency heart sounds ($S_1/S_2$ at $50 \text{ Hz}$) from leaking across into higher-frequency bins ($> 200 \text{ Hz}$).
* **Underlying Concept:** Window sidelobe leakage trade-offs.
* **Code Reference:** `software/pcg_core/scientific/spectral.py`
* **Follow-up Question:** What is the sidelobe roll-off rate of a rectangular window?
* **Common Incorrect Response:** "Hamming window has better sidelobes." (Incorrect: Hamming first sidelobe is lower, but rolls off at only $-6 \text{ dB/octave}$).

### Q52: What is the Short-Time Fourier Transform (STFT) and what governs its time-frequency resolution?
* **Difficulty:** Intermediate
* **Expected Answer:** STFT segments a continuous signal with a sliding window $w[n-m]$ and computes the Fourier transform for each time step, yielding a 2D time-frequency spectrogram $X(m, \omega)$. Resolution is governed by the Gabor uncertainty principle: narrowing the window improves time resolution $\Delta t$ but degrades frequency resolution $\Delta f$ ($\Delta t \cdot \Delta f \ge 1/4\pi$).
* **Underlying Concept:** Time-frequency duality.
* **Code Reference:** `software/pcg_core/analysis.py`
* **Follow-up Question:** What window size is used in our spectrogram display?
* **Common Incorrect Response:** "You can have perfect time and frequency resolution simultaneously." (Incorrect: violates the Heisenberg-Gabor limit).

### Q53: How is power mains interference quantified in `pcg_core.scientific.spectral`?
* **Difficulty:** Advanced
* **Expected Answer:** By evaluating narrow spectral integration windows ($\pm 2.5 \text{ Hz}$) centered at $50 \text{ Hz}$ and its harmonics ($100, 150, 200, 250 \text{ Hz}$), and comparing them against adjacent baseline shoulder bands ($[f_k - 7.5, f_k - 2.5] \cup [f_k + 2.5, f_k + 7.5]$) to compute the Mains-to-Background Ratio (MBR) in dB.
* **Underlying Concept:** Harmonic spectral peak extraction.
* **Code Reference:** `software/pcg_core/scientific/spectral.py`
* **Follow-up Question:** What is the target threshold for 50 Hz interference on the phantom bench?
* **Common Incorrect Response:** "It just measures total power below 60 Hz." (Incorrect: broad band power confuses cardiac S1 energy with mains hum).

### Q54: What is Parseval's theorem and how does it relate time-domain energy to frequency-domain power?
* **Difficulty:** Intermediate
* **Expected Answer:** Parseval's theorem states that the total energy of a signal in the time domain equals the total energy in the frequency domain:
  $$\sum_{n=0}^{N-1} |x[n]|^2 = \frac{1}{N} \sum_{k=0}^{N-1} |X[k]|^2$$
* **Underlying Concept:** Energy conservation under unitary transforms.
* **Code Reference:** `docs/engineering/science/SPECTRAL_ANALYSIS.md`
* **Follow-up Question:** Why is window power compensation ($U = \frac{1}{M} \sum w^2[n]$) required in Welch PSD?
* **Common Incorrect Response:** "Energy is always higher in frequency domain." (Incorrect: energy is identically conserved).

### Q55: Why must zero-padding in an FFT NOT be confused with increasing true physical frequency resolution?
* **Difficulty:** Advanced
* **Expected Answer:** Zero-padding interpolates the DTFT spectrum by evaluating more points along the unit circle, yielding closer visual bin spacing, but it does NOT increase true physical frequency resolution. Physical resolution is bounded strictly by the time duration of the acquired signal ($\Delta f \approx 1/T$).
* **Underlying Concept:** Spectral interpolation vs. Rayleigh resolution.
* **Code Reference:** `docs/engineering/science/SPECTRAL_ANALYSIS.md`
* **Follow-up Question:** If you have 100 ms of audio, can zero-padding resolve two sine waves separated by 1 Hz?
* **Common Incorrect Response:** "Zero-padding gives higher resolution." (Incorrect: it only interpolates the sinc sidelobes).

### Q56: What is the Gabor limit?
* **Difficulty:** Advanced
* **Expected Answer:** The mathematical inequality $\Delta t \cdot \Delta f \ge \frac{1}{4\pi}$, stating that a signal cannot be simultaneously arbitrarily localized in both the time and frequency domains.
* **Underlying Concept:** Uncertainty principle in signal processing.
* **Code Reference:** `docs/engineering/science/SPECTRAL_ANALYSIS.md`
* **Follow-up Question:** Which window function achieves the theoretical minimum Gabor bound?
* **Common Incorrect Response:** "It only applies to quantum mechanics." (Incorrect: it is a fundamental property of all Fourier transform pairs).

### Q57: What is spectral leakage and what causes it?
* **Difficulty:** Foundation
* **Expected Answer:** The spreading of energy from a single frequency component into adjacent frequency bins, caused by truncating a continuous-time signal with a finite-length time window (convolution with the window's Dirichlet/sinc spectrum).
* **Underlying Concept:** Window truncation in the Fourier domain.
* **Code Reference:** `docs/engineering/science/SPECTRAL_ANALYSIS.md`
* **Follow-up Question:** How do we minimize spectral leakage?
* **Common Incorrect Response:** "It is caused by electrical noise." (Incorrect: it is an inherent mathematical property of finite-length Fourier transforms).

### Q58: Why does a 50% overlap in Welch's method recover lost information?
* **Difficulty:** Intermediate
* **Expected Answer:** Tapered windows (like Hann) attenuate samples near the block edges down to zero, effectively ignoring transient events that occur near boundaries. A 50% overlap places the center (maximum gain) of the subsequent window directly over the attenuated edge of the previous window, ensuring all samples contribute equally to the spectral estimate.
* **Underlying Concept:** Window tapering compensation.
* **Code Reference:** `software/pcg_core/scientific/spectral.py`
* **Follow-up Question:** What is the equivalent number of independent segments for 50% overlap?
* **Common Incorrect Response:** "To make the FFT run twice as fast." (Incorrect: it recovers energy attenuated by window boundaries).

---

## Domain 6: Acoustic Metrology & SISO System ID

### Q59: Define the SISO $H_1(f)$ transfer function estimator and explain why it is chosen over $H_2(f)$.
* **Difficulty:** Advanced
* **Expected Answer:** $H_1(f) = \frac{S_{xy}(f)}{S_{xx}(f)}$ is the cross-spectral density divided by the input auto-spectral density. It assumes observation noise is concentrated on the output sensor ($y[n]$), which matches our acoustic setup where ambient room noise corrupts the microphone. $H_2(f) = \frac{S_{yy}(f)}{S_{yx}(f)}$ assumes noise on the input stimulus.
* **Underlying Concept:** System identification noise models.
* **Code Reference:** `software/pcg_core/phantom.py`
* **Follow-up Question:** What does $H_1(f)$ equal if the system is completely noiseless?
* **Common Incorrect Response:** "H1 is for single input, H2 is for two inputs." (Incorrect: both are SISO estimators with different noise assumptions).

### Q60: What is Magnitude-Squared Coherence $\gamma_{xy}^2(f)$ and what does a value of 0.3 indicate?
* **Difficulty:** Advanced
* **Expected Answer:** $\gamma_{xy}^2(f) = \frac{|S_{xy}(f)|^2}{S_{xx}(f)S_{yy}(f)}$, bounded in $[0, 1]$. A value of $0.3$ indicates very low coherence, meaning the captured signal at that frequency is NOT linearly related to the stimulus. Causes: heavy ambient room noise, severe non-linear distortion (amplifier/exciter clipping), or uncorrected timebase drift.
* **Underlying Concept:** Coherence function and linear system validity.
* **Code Reference:** `software/pcg_core/scientific/system_id.py`
* **Follow-up Question:** What coherence threshold is required for a valid frequency response measurement?
* **Common Incorrect Response:** "It means 30% amplitude." (Incorrect: coherence measures linear correlation in frequency domain, not amplitude).

### Q61: How does AuscultaForge estimate the propagation delay $\tau$ between electrical stimulus and microphone capture?
* **Difficulty:** Intermediate
* **Expected Answer:** By computing the normalized cross-correlation sequence $R_{xy}[m] = \mathcal{F}^{-1}\{X^*(f)Y(f)\}$ and finding the discrete sample lag $D = \arg\max_m R_{xy}[m]$. Delay is $\tau = D / f_s$.
* **Underlying Concept:** Time-of-flight estimation via cross-correlation.
* **Code Reference:** `software/pcg_core/phantom.py`
* **Follow-up Question:** What is the discrete temporal resolution of this estimate at 48 kHz?
* **Common Incorrect Response:** "By subtracting the start timestamps." (Incorrect: timestamps suffer from USB jitter; cross-correlation aligns the acoustic waveforms directly).

### Q62: How is scalar path gain estimated under additive noise?
* **Difficulty:** Intermediate
* **Expected Answer:** Via least-squares regression between the stimulus $x[n]$ and aligned capture $y_{\text{aligned}}[n]$:
  $$\hat{g}_{\text{LS}} = \frac{\sum x[n] y_{\text{aligned}}[n]}{\sum x^2[n]}$$
* **Underlying Concept:** Least-squares gain estimation.
* **Code Reference:** `software/pcg_core/validation.py`
* **Follow-up Question:** What does `PhantomStimulusEngine` do if $\sum x^2[n] = 0$?
* **Common Incorrect Response:** "By taking the ratio of peak values." (Incorrect: peak ratio is sensitive to noise spikes; least-squares uses all samples).

### Q63: List the six mandatory physical measurements required by the course advisor.
* **Difficulty:** Foundation
* **Expected Answer:**
  1. Phantom Frequency Response ($20\text{--}500\text{ Hz}$) via $H_1(f)$ and $\gamma_{xy}^2(f)$.
  2. Signal-to-Noise Ratio (SNR) in relative dB.
  3. Measurement Repeatability ($\ge 10$ runs).
  4. Mains Interference Level (50 Hz and harmonics).
  5. End-to-End Latency.
  6. Dropped-Packet Rate during continuous streaming ($\ge 30$ minutes).
* **Underlying Concept:** Senior design course deliverables.
* **Code Reference:** `docs/engineering/verification/SOFTWARE_VS_HARDWARE_EVIDENCE.md`
* **Follow-up Question:** What is the current measurement status of all six physical metrics?
* **Common Incorrect Response:** "Heart rate, blood pressure, murmur classification..." (Incorrect: those are medical metrics; course requires physical acoustic characterization).

### Q64: What is the Coefficient of Variation ($\text{CV}$) and what target threshold is enforced?
* **Difficulty:** Intermediate
* **Expected Answer:** $\text{CV} = \frac{s}{|\bar{m}|} \times 100\%$, where $s$ is the sample standard deviation and $\bar{m}$ is the sample mean across $\ge 10$ runs. The target threshold is $\text{CV} \le 5.0\%$.
* **Underlying Concept:** Repeatability and statistical dispersion.
* **Code Reference:** `software/pcg_core/metrology/workflows.py`
* **Follow-up Question:** If $\text{CV} > 10\%$, what does that signify in the lab?
* **Common Incorrect Response:** "It is the error percentage of the sensor." (Incorrect: it measures relative variability between repeated trials).

### Q65: Why is a dead-weight clamping fixture (e.g. 500 g) recommended during acoustic phantom testing?
* **Difficulty:** Intermediate
* **Expected Answer:** Human hand pressure holding a stethoscope against a silicone phantom fluctuates significantly across runs, altering contact impedance and air cavity volume. A fixed 500 g dead-weight ensures identical contact force, isolating sensor repeatability from user handling error.
* **Underlying Concept:** Experimental repeatability control.
* **Code Reference:** `docs/engineering/science/MEASUREMENT_UNCERTAINTY.md`
* **Follow-up Question:** How does contact pressure alter low-frequency bass response?
* **Common Incorrect Response:** "To stop the phantom from falling over." (Incorrect: it standardizes mechanical acoustic coupling pressure).

### Q66: What acoustic components constitute the bench test phantom?
* **Difficulty:** Foundation
* **Expected Answer:** An audio power amplifier (PAM8403), an electrodynamic acoustic exciter / tactile transducer, a compliant silicone/gel tissue-mimicking layer, and a rigid mounting frame.
* **Underlying Concept:** Acoustic phantom construction.
* **Code Reference:** `docs/engineering/architecture/SYSTEM_ARCHITECTURE.md`
* **Follow-up Question:** Who owns phantom fabrication in the team?
* **Common Incorrect Response:** "A human patient." (Incorrect: human subjects are explicitly out of scope).

### Q67: What is the purpose of the 5-minute warm-up period in metrology workflows?
* **Difficulty:** Intermediate
* **Expected Answer:** Continuous audio drive causes electrical voice-coil heating in the exciter, increasing copper resistance and slightly shifting amplifier gain. A warm-up period reaches thermal equilibrium before recording the 10-run repeatability sequence.
* **Underlying Concept:** Thermal drift in electroacoustic transducers.
* **Code Reference:** `docs/engineering/science/MEASUREMENT_UNCERTAINTY.md`
* **Follow-up Question:** How much can gain shift due to thermal voice-coil heating?
* **Common Incorrect Response:** "To warm up the software." (Incorrect: voice coil resistance rises with temperature, shifting gain by $\approx 0.2\text{--}0.5\text{ dB}$).

### Q68: How is Signal-to-Noise Ratio (SNR) calculated in `pcg_core.scientific.signal_quality`?
* **Difficulty:** Intermediate
* **Expected Answer:** By taking the ratio of active band-limited signal power ($20\text{--}500\text{ Hz}$) during acoustic excitation to the quiescent noise floor power measured when the exciter is silent:
  $$\text{SNR}_{\text{dB}} = 10 \log_{10}\left( \frac{P_{\text{active}}}{P_{\text{quiescent}}} \right)$$
* **Underlying Concept:** Signal-to-Noise Ratio measurement.
* **Code Reference:** `software/pcg_core/scientific/signal_quality.py`
* **Follow-up Question:** What is the course target for bench SNR?
* **Common Incorrect Response:** "By dividing peak voltage by RMS voltage." (Incorrect: peak over RMS is crest factor, not SNR).

### Q69: Why can we NOT claim sound pressure measurements in calibrated Pascals or dB SPL?
* **Difficulty:** Advanced
* **Expected Answer:** Because our acquisition chain lacks end-to-end absolute calibration against an acoustic pressure standard (e.g. an IEC 60318 artificial ear with a calibrated laboratory condenser microphone). Our measurements are strictly relative digital levels (dBFS).
* **Underlying Concept:** Metrological traceability and calibration standards.
* **Code Reference:** `docs/engineering/science/PCG_SIGNAL_FOUNDATIONS.md`
* **Follow-up Question:** What would happen during an academic defense if you claimed your stethoscope measured $85 \text{ dB SPL}$?
* **Common Incorrect Response:** "Because Pascals are for weather." (Incorrect: sound pressure is measured in Pascals, but requires certified acoustic calibration).

### Q70: What is the minimum acceptable streaming continuity during the Week 8 stress test?
* **Difficulty:** Foundation
* **Expected Answer:** $100.0\%$ continuity (exactly **zero dropped blocks**) over 30 minutes of continuous acquisition ($86,400,000$ samples).
* **Underlying Concept:** Stress testing and data integrity.
* **Code Reference:** `docs/engineering/verification/SOFTWARE_VS_HARDWARE_EVIDENCE.md`
* **Follow-up Question:** How many total samples are acquired in 30 minutes at 48 kHz?
* **Common Incorrect Response:** "99% is acceptable." (Incorrect: course standard requires 100% sample continuity).

---

## Domain 7: Heart Sound Segmentation & Machine Learning

### Q71: What are the four states modeled in Springer's LR-HSMM segmentation algorithm?
* **Difficulty:** Foundation
* **Expected Answer:** State 1: $S_1$ (First heart sound), State 2: Systole, State 3: $S_2$ (Second heart sound), State 4: Diastole.
* **Underlying Concept:** Cardiac phonocardiogram state modeling.
* **Code Reference:** `software/pcg_core/segmentation/springer_hsmm.py`
* **Follow-up Question:** What is the strict transition topology between these states?
* **Common Incorrect Response:** "Systole, Diastole, Murmur, Noise." (Incorrect: those are acoustic categories, not the 4 cyclic states).

### Q72: Why is a Hidden Semi-Markov Model (HSMM) necessary instead of a standard Hidden Markov Model (HMM)?
* **Difficulty:** Advanced
* **Expected Answer:** Standard HMMs have memoryless geometric/exponential state duration distributions, predicting that the most probable duration for $S_1$ or $S_2$ is $1 \text{ ms}$. An HSMM explicitly parameterizes duration distributions (Gaussian/Poisson), enforcing realistic physiological durations ($80\text{--}150 \text{ ms}$).
* **Underlying Concept:** Semi-Markov duration modeling.
* **Code Reference:** `software/pcg_core/segmentation/springer_hsmm.py`
* **Follow-up Question:** How are duration distributions conditioned in Springer's model?
* **Common Incorrect Response:** "HMM cannot handle four states." (Incorrect: HMM handles any number of states, but models duration exponentially).

### Q73: What four features are extracted in the Springer segmentation pipeline?
* **Difficulty:** Intermediate
* **Expected Answer:**
  1. Homomorphic envelope.
  2. Hilbert analytic envelope.
  3. Wavelet energy envelope (Daubechies-4 / Morlet).
  4. Power Spectral Density envelope ($40\text{--}250 \text{ Hz}$).
* **Underlying Concept:** Multi-feature acoustic envelope extraction.
* **Code Reference:** `software/pcg_core/segmentation/features.py`
* **Follow-up Question:** To what sampling frequency is the audio resampled before feature extraction?
* **Common Incorrect Response:** "MFCCs, Chroma, Spectrogram, Zero Crossing." (Incorrect: those are speech features; Springer uses 4 specific envelopes).

### Q74: How are state emission probabilities calculated in Springer's LR-HSMM?
* **Difficulty:** Advanced
* **Expected Answer:** Using four One-vs-Rest (OvR) logistic regression classifiers to estimate posterior state probabilities $P(q_t = j \mid \mathbf{O}_t) = \frac{1}{1 + e^{-(\mathbf{w}_j^T \mathbf{O}_t + b_j)}}$, then applying Bayes' rule: $b_j(\mathbf{O}_t) \propto \frac{P(q_t = j \mid \mathbf{O}_t)}{P(q_t = j)}$.
* **Underlying Concept:** Logistic regression emission modeling in HSMM.
* **Code Reference:** `software/pcg_core/segmentation/springer_logistic.py`
* **Follow-up Question:** Why use logistic regression instead of Gaussian Mixture Models (GMM)?
* **Common Incorrect Response:** "Using neural networks." (Incorrect: Springer 2016 specifically uses logistic regression).

### Q75: How does the extended Viterbi algorithm enforce the cyclic cardiac constraint?
* **Difficulty:** Advanced
* **Expected Answer:** By constraining the state transition matrix $A$ such that $A_{1,2} = 1, A_{2,3} = 1, A_{3,4} = 1, A_{4,1} = 1$, and all other transitions are zero ($-\infty$ in log-space). Any path attempting to transition from $S_1$ directly to $S_2$ or diastole is pruned.
* **Underlying Concept:** Dynamic programming with constrained transition matrices.
* **Code Reference:** `software/pcg_core/segmentation/springer_hsmm.py`
* **Follow-up Question:** Can the algorithm start in any state?
* **Common Incorrect Response:** "By sorting the outputs by time." (Incorrect: the constraint is enforced inside the forward Viterbi trellis).

### Q76: What is subject-level splitting and why is record-level splitting a fatal error in biomedical validation?
* **Difficulty:** Expert
* **Expected Answer:** Record-level splitting places different recordings from the SAME patient into both the training and test sets. This causes severe data leakage: the model memorizes patient-specific acoustic chest impedance, producing artificially inflated accuracy. Subject-level splitting strictly isolates all patient recordings into either train or test folds.
* **Underlying Concept:** Data leakage and cross-validation integrity.
* **Code Reference:** `software/pcg_core/segmentation/validation/`
* **Follow-up Question:** Which test verifies zero subject leakage in our codebase?
* **Common Incorrect Response:** "Record-level splitting is fine if shuffled randomly." (Incorrect: random shuffling causes patient leakage).

### Q77: What open-access dataset is used in AuscultaForge for segmentation benchmarking?
* **Difficulty:** Foundation
* **Expected Answer:** The PhysioNet CirCor DigiScope Pediatric PCG Dataset (PhysioNet Challenge 2022, Source R008).
* **Underlying Concept:** Benchmark dataset provenance.
* **Code Reference:** `software/pcg_core/segmentation/circor.py`
* **Follow-up Question:** Why is this dataset appropriate?
* **Common Incorrect Response:** "MIT-BIH Arrhythmia Database." (Incorrect: MIT-BIH is an ECG database, not PCG).

### Q78: Define the event matching tolerance window and explain how True Positives are scored.
* **Difficulty:** Intermediate
* **Expected Answer:** A predicted event ($S_1$ or $S_2$) is scored as a True Positive ($TP$) if its center falls within $\pm \delta$ (typically $\pm 50 \text{ ms}$ or $\pm 100 \text{ ms}$) of an unmatched reference annotation. If no reference annotation exists within $\pm \delta$, it is a False Positive ($FP$).
* **Underlying Concept:** Temporal event matching metrics.
* **Code Reference:** `software/pcg_core/segmentation/matching.py`
* **Follow-up Question:** What prevents two predictions from claiming the same reference event?
* **Common Incorrect Response:** "By calculating mean squared error." (Incorrect: discrete event detection uses temporal matching windows).

### Q79: What is the official role of machine learning in the EEE495/EEE496 course grading criteria?
* **Difficulty:** Foundation
* **Expected Answer:** Machine learning is an **OPTIONAL SUPPORTING RESEARCH EXTENSION**. It does NOT fulfill or substitute for the mandatory physical acquisition hardware, acoustic phantom characterization, and six physical measurements required by the course.
* **Underlying Concept:** Academic scope and course deliverables.
* **Code Reference:** `README.md`
* **Follow-up Question:** What should you say if an examiner asks if your project is an "AI project"?
* **Common Incorrect Response:** "Machine learning is our main course deliverable." (Incorrect: physical hardware and metrology are the core criteria).

### Q80: How does autocorrelation estimate heart rate in `pcg_core.segmentation.heart_rate`?
* **Difficulty:** Intermediate
* **Expected Answer:** By evaluating the autocorrelation of the envelope signal and finding the peak lag within the physiologically plausible cardiac period window ($T \in [300\text{ ms}, 1500\text{ ms}]$, corresponding to $40\text{--}200 \text{ BPM}$).
* **Underlying Concept:** Autocorrelation pitch/period estimation.
* **Code Reference:** `software/pcg_core/segmentation/heart_rate.py`
* **Follow-up Question:** What happens if the peak falls outside the physiological range?
* **Common Incorrect Response:** "By counting S1 peaks." (Incorrect: peak counting is vulnerable to noise; autocorrelation finds the fundamental period).

### Q81: What is the $F_1$-score and why is accuracy an inappropriate metric for imbalanced cardiac states?
* **Difficulty:** Intermediate
* **Expected Answer:** $F_1 = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$. Accuracy is misleading because cardiac states have imbalanced durations: diastole occupies $\approx 50\%$ of the cycle, while $S_1$ and $S_2$ occupy only $\approx 10\%$ each. A trivial model predicting "diastole" everywhere would achieve $50\%$ accuracy while detecting zero heart sounds.
* **Underlying Concept:** Class imbalance in medical time-series.
* **Code Reference:** `software/pcg_core/segmentation/evaluation.py`
* **Follow-up Question:** What is the formula for Sensitivity?
* **Common Incorrect Response:** "Accuracy is always the best metric." (Incorrect: accuracy fails under class imbalance).

### Q82: What is duration conditioning in Springer's HSMM?
* **Difficulty:** Advanced
* **Expected Answer:** State duration means ($\mu_{\text{sys}}, \mu_{\text{dia}}$) scale dynamically as a function of heart rate. At elevated heart rates (e.g. 120 BPM), diastole shortens dramatically, while $S_1$ and $S_2$ durations remain relatively constant. Springer's model adjusts duration distributions based on estimated heart rate.
* **Underlying Concept:** Physiological duration scaling.
* **Code Reference:** `software/pcg_core/segmentation/durations.py`
* **Follow-up Question:** Which cardiac phase shortens the most during tachycardia?
* **Common Incorrect Response:** "All states scale equally." (Incorrect: diastole shortens significantly more than systole).

---

## Domain 8: Python Backend & FastAPI Architecture

### Q83: Why does `software/pcg_app/app.py` use an application factory (`create_app`) instead of a global `app = FastAPI()`?
* **Difficulty:** Intermediate
* **Expected Answer:** A global `app` object creates shared state across test runs, causing race conditions and database/session directory pollution. `create_app()` allows test harnesses to instantiate isolated application instances with custom session directories, enabling parallel testing.
* **Underlying Concept:** Software design patterns and test isolation.
* **Code Reference:** `software/pcg_app/app.py`
* **Follow-up Question:** How does this affect the Uvicorn command-line syntax?
* **Common Incorrect Response:** "It is required by FastAPI." (Incorrect: FastAPI supports global instances, but factories improve testing).

### Q84: How many total routes are registered in the AuscultaForge FastAPI backend?
* **Difficulty:** Foundation
* **Expected Answer:** Exactly **57 routes** (programmatically verified in `create_app()`).
* **Underlying Concept:** API surface audit.
* **Code Reference:** `docs/engineering/code-atlas/FASTAPI_API_REFERENCE.md`
* **Follow-up Question:** How many of those routes are directly exercised in HTTP smoke tests?
* **Common Incorrect Response:** "Around 10 or 15." (Incorrect: exact count is 57 registered routes).

### Q85: What is the correct endpoint for polling physical USB devices?
* **Difficulty:** Foundation
* **Expected Answer:** `POST /api/device/poll` (Note: `/api/device/detect` was an outdated documentation draft corrected during the Master Integration Gate acceptance patch).
* **Underlying Concept:** API route accuracy.
* **Code Reference:** `software/pcg_app/app.py`
* **Follow-up Question:** What does `POST /api/device/poll` return?
* **Common Incorrect Response:** "`GET /api/device/detect`." (Incorrect: route is POST `/api/device/poll`).

### Q86: How does `StreamManager` prevent slow WebSocket clients from stalling the background audio recorder?
* **Difficulty:** Advanced
* **Expected Answer:** By maintaining completely separate queues. The audio recorder writes synchronously to the OS disk buffer, while the WebSocket broadcast queue has a bounded size ($32$ frames). If a client is slow, the WebSocket queue drops *display* frames, while disk recording remains 100% intact.
* **Underlying Concept:** Asynchronous queue isolation and backpressure decoupling.
* **Code Reference:** `software/pcg_app/state.py`
* **Follow-up Question:** What test verifies that disk recordings are not corrupted by slow clients?
* **Common Incorrect Response:** "By pausing the audio stream." (Incorrect: pausing audio drops real samples from disk).

### Q87: What are the eight states of the `DeviceRuntime` lifecycle state machine?
* **Difficulty:** Intermediate
* **Expected Answer:** `ABSENT`, `DETECTED`, `OPENING`, `HANDSHAKING`, `READY`, `STREAMING`, `CLOSING`, `INTERRUPTED`.
* **Underlying Concept:** Finite state machine design.
* **Code Reference:** `software/pcg_app/device_runtime.py`
* **Follow-up Question:** Can the device transition directly from `ABSENT` to `STREAMING`?
* **Common Incorrect Response:** "Connected and Disconnected." (Incorrect: those are binary flags, not the full 8-state machine).

### Q88: How does `SessionRecorder` guarantee that recorded WAV files are valid even if the cable is disconnected mid-stream?
* **Difficulty:** Advanced
* **Expected Answer:** It writes placeholder headers at start, appends raw PCM bytes continuously, and traps `SerialException` in an emergency disconnect handler that rewrites the RIFF header chunk sizes to match the exact byte count written before the disconnect occurred.
* **Underlying Concept:** Emergency file finalization.
* **Code Reference:** `software/pcg_core/recording.py`
* **Follow-up Question:** What happens if the WAV header chunk size is NOT rewritten?
* **Common Incorrect Response:** "The operating system automatically fixes it." (Incorrect: leaving 0xFFFFFFFF makes the WAV unreadable in standard players).

### Q89: Why is SHA-256 computed only over the audio samples and NOT the entire WAV file?
* **Difficulty:** Intermediate
* **Expected Answer:** The 44-byte RIFF container header contains file-length metadata and chunk headers that may be updated or reordered by audio software. Computing the hash strictly over the PCM audio samples ensures the cryptographic digest reflects the acoustic data payload itself.
* **Underlying Concept:** Cryptographic payload integrity.
* **Code Reference:** `software/pcg_core/recording.py`
* **Follow-up Question:** Where is this hash stored?
* **Common Incorrect Response:** "Because hashing headers is illegal." (Incorrect: it ensures hash invariance to container metadata).

### Q90: What is the purpose of `RollingBuffer` in `pcg_core/buffers.py`?
* **Difficulty:** Intermediate
* **Expected Answer:** It provides a thread-safe circular FIFO buffer holding the latest $5.0 \text{ seconds}$ of audio ($240,000 \text{ samples}$ at $48\text{ kHz}$) in memory, allowing instant extraction of overlapping windows for Welch PSD and real-time spectrogram generation without disk I/O.
* **Underlying Concept:** Circular memory buffers.
* **Code Reference:** `software/pcg_core/buffers.py`
* **Follow-up Question:** How does it achieve zero runtime memory allocation?
* **Common Incorrect Response:** "To save audio files to disk." (Incorrect: SessionRecorder writes to disk; RollingBuffer is an in-memory sliding window).

### Q91: What is the difference between synchronous code and asynchronous coroutines in FastAPI?
* **Difficulty:** Foundation
* **Expected Answer:** Synchronous functions (`def`) block the worker thread while waiting for I/O (disk/network). Asynchronous coroutines (`async def`) use `await` to yield control back to the event loop, allowing the server to service other requests and WebSockets while waiting for I/O.
* **Underlying Concept:** Asyncio event-loop concurrency.
* **Code Reference:** `software/pcg_app/app.py`
* **Follow-up Question:** What happens if you call a blocking `time.sleep(5)` inside an `async def` route?
* **Common Incorrect Response:** "Async makes code run on multiple CPU cores." (Incorrect: asyncio is single-threaded cooperative multitasking).

### Q92: What is the purpose of CORS middleware in `pcg_app/app.py`?
* **Difficulty:** Foundation
* **Expected Answer:** Cross-Origin Resource Sharing (CORS) middleware allows the React frontend running on `http://127.0.0.1:3000` to make HTTP requests and WebSocket connections to the Python backend running on `http://127.0.0.1:8000` without being blocked by the browser's same-origin security policy.
* **Underlying Concept:** Web browser security and origin policies.
* **Code Reference:** `software/pcg_app/app.py`
* **Follow-up Question:** Why is this needed if both run on localhost?
* **Common Incorrect Response:** "It encrypts the traffic." (Incorrect: port numbers 3000 and 8000 represent different origins under browser security rules).

---

## Domain 9: Frontend Architecture & Real-Time Canvas

### Q93: Why does the frontend waveform display use an HTML5 Canvas instead of React SVG/DOM elements?
* **Difficulty:** Intermediate
* **Expected Answer:** Audio waveforms require updating hundreds of data points 60 times per second. Rendering with SVG or React state causes thousands of DOM node reconciliations per second, causing severe frame drops and garbage collection freezing. The HTML5 Canvas provides immediate-mode hardware-accelerated 2D rendering.
* **Underlying Concept:** Immediate-mode vs. retained-mode graphics.
* **Code Reference:** `software/frontend/src/components/LiveWorkspace.tsx`
* **Follow-up Question:** Which browser API drives the render loop?
* **Common Incorrect Response:** "SVG is faster for lines." (Incorrect: SVG creates DOM nodes for every segment, which exhausts browser memory at 60 FPS).

### Q94: How does `DisplayDecimator` preserve transient clicks while decimating 512 samples to $\le 600$ points?
* **Difficulty:** Intermediate
* **Expected Answer:** By partitioning the block into buckets and extracting both the minimum and maximum sample in each bucket. If a sharp transient spike (1 sample wide) occurs, it is guaranteed to become the bucket maximum or minimum and is preserved in the interleaved output.
* **Underlying Concept:** Peak-preserving envelope reduction.
* **Code Reference:** `software/pcg_app/display_pipeline.py`
* **Follow-up Question:** What would happen if we used simple subsampling (every N-th point)?
* **Common Incorrect Response:** "It takes the average." (Incorrect: averaging blurs sharp clicks; min/max preserves extremum).

### Q95: Explain the distinction between `mcu_drops` and `display_drops` on the user interface.
* **Difficulty:** Intermediate
* **Expected Answer:** `mcu_drops` (red badge) indicates genuine packet loss over the physical USB bus detected via sequence counter gaps. `display_drops` (amber badge) indicates that the host computer skipped a UI rendering frame due to local CPU load, while background audio recording remained 100% intact.
* **Underlying Concept:** Telemetry truthfulness and fault isolation.
* **Code Reference:** `software/frontend/src/components/LiveWorkspace.tsx`
* **Follow-up Question:** Why is this distinction crucial during a live examination demo?
* **Common Incorrect Response:** "They both mean the stethoscope is dropping data." (Incorrect: display drops mean the browser was busy; audio file on disk was lossless).

### Q96: What unit test file verifies frontend mathematical logic?
* **Difficulty:** Foundation
* **Expected Answer:** `software/frontend/src/tests/live_workspace_math.test.ts`, executed via `npm test`.
* **Underlying Concept:** Frontend unit testing.
* **Code Reference:** `software/frontend/src/tests/live_workspace_math.test.ts`
* **Follow-up Question:** What 4 tests are in that suite?
* **Common Incorrect Response:** "Jest tests." (Incorrect: executed via `tsx` script testing circular window indexing and telemetry).

### Q97: What is the 15x scale distortion bug prevented in `live_workspace_math.test.ts`?
* **Difficulty:** Advanced
* **Expected Answer:** In early frontend prototyping, mapping circular buffer sample indices to screen pixels incorrectly used the raw buffer capacity ($240,000$) instead of the active display window length ($16,000$), compressing the waveform by 15x onto the left edge of the screen. The test verifies exact index mapping.
* **Underlying Concept:** Coordinate transformation testing.
* **Code Reference:** `software/frontend/src/tests/live_workspace_math.test.ts`
* **Follow-up Question:** How was this verified?
* **Common Incorrect Response:** "It was an audio pitch bug." (Incorrect: it was a screen pixel coordinate scaling bug).

### Q98: How does `BridgeClient` handle automatic WebSocket reconnection?
* **Difficulty:** Intermediate
* **Expected Answer:** If the WebSocket connection drops, `BridgeClient` sets state to disconnected, initiates an exponential backoff timer, and attempts reconnection periodically. When the backend restarts, it re-establishes communication and resynchronizes telemetry without requiring a browser refresh.
* **Underlying Concept:** Resilient client networking.
* **Code Reference:** `software/frontend/src/bridgeClient.ts`
* **Follow-up Question:** What prevents reconnect storms?
* **Common Incorrect Response:** "The browser automatically reconnects WebSockets." (Incorrect: browsers do not auto-reconnect WebSockets; application code must implement it).

### Q99: What is TypeScript compile-time type checking and what command runs it?
* **Difficulty:** Foundation
* **Expected Answer:** `tsc --noEmit` (executed via `npm run lint`). It verifies type safety, interface conformance, and null-safety across all TypeScript files without emitting JavaScript build output, catching contract mismatches before runtime.
* **Underlying Concept:** Static type analysis.
* **Code Reference:** `software/frontend/package.json`
* **Follow-up Question:** How many errors did `tsc --noEmit` report on our codebase?
* **Common Incorrect Response:** "0 errors." (Correct: 0 errors).

### Q100: What tool bundles the React application for production?
* **Difficulty:** Foundation
* **Expected Answer:** **Vite** (version 6.4.3), using Rollup for production bundling and minification. Build is executed via `npm run build` and completes in $\approx 3.5 \text{ seconds}$.
* **Underlying Concept:** Modern frontend build tooling.
* **Code Reference:** `software/frontend/package.json`
* **Follow-up Question:** What directory does Vite output production assets to?
* **Common Incorrect Response:** "Webpack." (Incorrect: AuscultaForge uses Vite).

---

## Domain 10: Academic Governance, Ethics & Ownership

### Q101: What are the primary ownership boundaries between Kaan, Ozan, and Ege?
* **Difficulty:** Foundation
* **Expected Answer:**
  * **Kaan (Module A):** Acoustic chestpiece, transducer evaluation (ECM vs MEMS), phantom fabrication, and acoustic characterization.
  * **Ozan (Module B):** Embedded firmware under `firmware/`, FreeRTOS task scheduling, I2S DMA drivers, and BOM component procurement.
  * **Ege (Module C):** Host software runtime (`pcg_app`), DSP algorithms (`pcg_core`), metrology automation, Springer segmentation lab, and master integration.
* **Underlying Concept:** Academic module allocation and individual assessment.
* **Code Reference:** `README.md`
* **Follow-up Question:** Why are module boundaries strictly enforced by the faculty?
* **Common Incorrect Response:** "Everyone worked on everything together equally." (Incorrect: faculty requires clear individual ownership for ABET evaluation).

### Q102: Why does AuscultaForge explicitly prohibit clinical diagnostic claims?
* **Difficulty:** Foundation
* **Expected Answer:** The project is an undergraduate engineering capstone prototype evaluated on acoustic bench phantoms. Making medical diagnostic claims without certified clinical trials, medical device certification (CE/FDA), and Institutional Review Board (IRB) ethics approval is scientifically fraudulent and legally prohibited.
* **Underlying Concept:** Medical device ethics and engineering boundaries.
* **Code Reference:** `docs/engineering/decisions/ADR-0018-engineering-metrology-vs-clinical-diagnosis.md`
* **Follow-up Question:** What does the platform evaluate instead of diagnosis?
* **Common Incorrect Response:** "Because our AI is not accurate enough yet." (Incorrect: even with 100% accuracy, clinical claims are illegal without clinical trials).

### Q103: What was the Master Integration Gate (PR #31)?
* **Difficulty:** Intermediate
* **Expected Answer:** A rigorous integration operation that consolidated 10 agile software sprints (PR #18–26) with Kaan's and Ozan's Week 4 deliverables into `main`, resolving 8 overlapping files semantically, applying bring-up acceptance patches, and verifying 394 automated tests.
* **Underlying Concept:** Continuous integration and repository governance.
* **Code Reference:** `docs/engineering/history/DEVELOPMENT_CHRONICLE.md`
* **Follow-up Question:** Why was PR #31 merged using a merge commit rather than squashing?
* **Common Incorrect Response:** "It added new firmware features." (Incorrect: it was an integration and verification gate).

### Q104: What is the difference between Academic Week 10 and Software Sprint 10?
* **Difficulty:** Foundation
* **Expected Answer:** Academic Week 10 is a calendar milestone in the university semester (currently at Week 04/05). Software Sprint 10 was an agile software engineering iteration for Module C focused on portable C golden vectors and bring-up checklists. They must never be confused.
* **Underlying Concept:** Project timeline disambiguation.
* **Code Reference:** `docs/hardware/ESP32_S3_BRINGUP_CHECKLIST.md`
* **Follow-up Question:** In which academic week was Sprint 10 executed?
* **Common Incorrect Response:** "They are the same thing." (Incorrect: confusing them misrepresents project schedule).

### Q105: How does AuscultaForge ensure reproducibility in published research?
* **Difficulty:** Intermediate
* **Expected Answer:** By embedding the exact Git commit SHA in all generated JSON session sidecars and metrology reports, maintaining cryptographic SHA-256 hashes of audio files, providing automated CLI experiment runners (`pcg_core.experiment`), and maintaining 394 automated regression tests.
* **Underlying Concept:** Open science and reproducible research engineering.
* **Code Reference:** `docs/engineering/verification/REPRODUCIBILITY_GUIDE.md`
* **Follow-up Question:** Where are baseline experiment configurations stored?
* **Common Incorrect Response:** "By taking screenshots." (Incorrect: scientific reproducibility requires cryptographic versioned artifacts).
