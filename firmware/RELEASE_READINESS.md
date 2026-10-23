# Firmware release readiness

Firmware 1.1.0, ESP-IDF 5.5.1. Actual build evidence and current source/release
identities are in [MORNING_RELEASE_REPORT](../docs/engineering/release/MORNING_RELEASE_REPORT.md).
**COMPILED_BUT_NOT_FLASHED. PHYSICAL BOOT/G1/G2: NOT_EXECUTED.**

Reviewed implementation: portable g1.c uses the same packet_framing.c as protocol
lab, explicit serializers/CRC, bounded receive buffer and eight-frame TX queue.
One session task owns parser/state/TX. TinyUSB callbacks only communicate atomic
link state. UART0 logs never enter CDC. No streaming occurs before valid START.
Link loss clears stale queues; fresh HELLO/START and session ID are required.

Monotonic esp_timer deadlines release complete deterministic blocks only at their
last nominal sample time. Target exhaustion stops generation and drains queued
AUDIO; it **waits for host STOP_REQ** before final STOP_ACK. The final ACK cannot
overtake queued audio. Firmware queued counters do not claim host receipt.
CRC/invalid commands do not change acquisition; partial TX advances only written
bytes; bounded backpressure loss/timeout is visible. Session timeout is 40 s;
transport stall timeout 1 s. Physical scheduler/USB timing still requires H3.

I2S source 0: implemented, default disabled, separately compiled. Only a reviewed
Kconfig profile registers the adapter. DMA reads run in a task, not USB ISR;
internal task stack and IDF DMA descriptors are used, no arbitrary PSRAM DMA
buffers. Queue depth eight, DMA descriptors eight x256 stereo32 frames. STOP
disables channel and waits up to100 ms for owner; timeout prevents queue reset.
24-bit conversion boundaries have portable tests; WS/BCLK/slot alignment and
microphone absence behavior require H4. Floating/zero input cannot prove a mic.

G1 does not depend on sensor presence. I2S init failure logs UART and keeps G1
available. Source0 unsupported returns firmware error2; runtime acquisition error6.
Firmware health prints queue, internal heap and task stack watermark once/sec;
no physical heap/stack measurement is claimed. DMA unknown losses remain events,
not invented exact missing samples. Live timestamps are completion-derived estimates.

Recovery assumptions: actual N16R8 marking and native USB route, viable UART/ROM
route and safe single-source power. No OTA/security/eFuse changes. First-day
microphone pins remain provisional and must not be connected from a generic PCB image.
