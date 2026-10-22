# G1 source-of-truth audit — 2026-10-22

Implementation ownership: Ege and the AuscultaForge team. Existing authorship and
historical review credits in the protocol laboratory are preserved; they do not
imply that Ozan is implementing this firmware.

Read before implementation: `software/pcg_app/canonical/{codec,session,engine,simulator}.py`,
`tools/protocol_lab/c/{include,src}`, Python protocol laboratory and physical
acceptance tests, canonical specification, and original physical bring-up guide.
The C explicit field serializers and Python decoder agree on the wire contract.
Host protocol code is not changed by this operation.

| Original guide statement | Reconciled contract / action |
| --- | --- |
| Profile B ID 1 | START payload profile ID **2**; HELLO profile mask **2** |
| LSB S32 encoding 2 | Encoding **1**; encoding 2 means MSB alignment |
| HELLO nonce 64 bits | **uint32**, request payload 4 bytes, exact echo |
| HELLO opcodes 1/2 | **0x10/0x11**; 1/2 are AUDIO/STATUS |
| START/STOP written as 16-bit opcodes | Header opcode is one byte: **3/4/5/6** |
| LCG 1103515245 + 12345 | **(n * 16807 + 7) & 0xffffff**, signed 24-bit |
| Live mode already available | Mode 0 is rejected; only deterministic mode 1 is implemented |
| Connect both USB ports | Inspect purchased PCB routing and power paths first |
| Debug UART and USB Serial/JTAG treated interchangeably | S3 internal PHY is shared by USB OTG and Serial/JTAG; use UART0 console, no eFuse changes |
| USB described as high-speed | ESP32-S3 native USB is **full-speed 12 Mbit/s** |
| HELLO badge proves hardware | HELLO proves wire interoperability only; full G1 evidence is separate |
| Fixed endpoint addresses / invented telemetry fields | Use actual descriptors and canonical 72-byte telemetry names |
| Ozan assigned active implementation | Ege/team firmware ownership; Kaan assists physical/acoustic inspection |
| Forced termination of every python.exe | Close only the identified COM-port owner |
| Synthetic timing proves acquisition clock | Analytical timestamps and monotonic pacing do not measure an I2S clock |

Additional source issues: the lab `GEN_SIGNAL_RAMP_COUNTER` is a simple incrementing
ramp, not normative source mode 1. Firmware therefore implements the normative
formula separately while reusing `packet_framing.c` unchanged. The lab parser also
accepts legacy Profile A and calibration frames; firmware uses a bounded
command-only Profile B parser, reusing header decoding and CRC. No legacy wire
profile is advertised. Specification prose calling HELLO/ERROR layouts "proposed"
is historical: the current C/Python serializers implement the stated 24/8-byte
layouts. Capability flag meanings and ERROR code meanings are not normatively
assigned; firmware advertises capability_flags=0 and documents local error codes.

Host session engine requires STOP_ACK only after host STOP_REQ. At target the
firmware stops generation, drains AUDIO, and waits for STOP_REQ; no unsolicited
STOP_ACK. START has no nonce field: the device echoes the HELLO nonce, and the host
checks it. A device cannot validate a nonexistent START nonce. Session IDs protect
STOP, and every reconnect requires a fresh HELLO.

Scope: firmware core, ESP-IDF entry/transport/config/manifests, host-buildable C
tests, Python cross-language tests/goldens, physical guide and evidence. Existing
host callers, exports, fixtures and wire format remain compatible. Main risks:
uncompiled ESP-specific adapter, purchased-board routing, sustained physical USB
throughput. No flashing, pin wiring, eFuse writes, secure boot or encryption.
