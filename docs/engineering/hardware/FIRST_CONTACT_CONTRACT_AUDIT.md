# First Contact contract audit — 2026-10-23

Baseline: main 15b863b. Ege: software/firmware integration; Kaan: physical assembly;
Ozan: embedded/acquisition peer review where appropriate. No physical gate passed.

| Interface inspected | Baseline | Required action |
| --- | --- | --- |
| C/Python magic, header, CRC and all nine opcodes | PASS | Reuse existing serializers |
| HELLO uint32 nonce, profile 2, encoding 1 | PASS | Add capability checks at host trust boundary |
| 48000/mono/24-in-S32, 256 samples/1068 bytes | PASS | Check all frames in acceptance observer |
| Normative source 1 formula / 480000 / 1875 | PASS | Retain independent host verification |
| ESP-IDF project, TinyUSB API and genuine component lock | PASS (source) | Actual cross compilation still required |
| Physical boot / USB / G1 | NOT_EXECUTED | No positively identified attached board |
| Engine G1 pass policy | FAIL | Previously allowed >=target, ignored CRC/sequence/final counters |
| Engine reconnect/repeated session / live validator | FAIL | Reset state, validate G1 only in mode 1 |
| Serial error propagation | FAIL | Error state must reach the engine instead of empty reads forever |
| Device Center API/types/rendering | FAIL | Stale state/counter/evidence field names; wrong start argument |
| USB doctor available-port identity | FAIL | An open port is not verified canonical firmware |
| Board-specific connector/pin knowledge | PHYSICAL_INSPECTION_REQUIRED | Seller page is not proof of delivered PCB |
| I2S mode 0 | NOT_IMPLEMENTED | Add default-disabled, reviewed-profile-only DMA adapter |
| Evidence / preflight / guided release and flash | NOT_IMPLEMENTED | Add thin workflows around production engine |

Normative source: canonical Python/C codecs reconciled with
`B_C_CANONICAL_PROTOCOL_V0_1.md`, not historical lab-package headers or obsolete
bring-up prose. Header/control layouts and host wire format remain unchanged.
The earlier guide was corrected; no alternate waveform or 64-bit nonce is used.

Scope reaches firmware source/controller/build config and tests; canonical engine,
session, transport and shared acceptance; existing DeviceRuntime/StreamManager
integration, REST endpoints, frontend types/client/Device Center; hardware CLI,
evidence, tests and lab documents. No dataset/model migration, raw recording
rewrite, driver installation, global PATH edit, automatic flash or medical inference.

Final interface results and exact executed gates are recorded in FIRST_CONTACT_RELEASE.md.
