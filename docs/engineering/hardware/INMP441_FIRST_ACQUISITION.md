# First single-INMP441 electrical and qualification plan

G2 is separate from deterministic G1. Ege handles firmware/software integration;
Kaan confirms physical assembly. Ozan can peer-review acquisition/alignment.
Physical microphone acquisition and acoustic qualification remain NOT_EXECUTED.

For morning operation use [START_HERE_TOMORROW](START_HERE_TOMORROW.md), the
[preliminary pin plan](PRELIMINARY_PIN_PLAN.md) and the separate
[physical confirmation form](PHYSICAL_INSPECTION_CHECKLIST.md).

## Electrical boundary

Use the [TDK INMP441 datasheet](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf)
for the component. The purchased breakout can have different labels and layout;
photograph both sides and identify every actual pin before soldering/wiring.
The component supply specification is 1.62..3.63 V; this project uses regulated
**3.3 V only**, with 3.3 V logic. Never connect VDD or logic to 5 V.
L/R selects the left slot at GND and right slot at VDD. A 48 kHz stereo-slot bus
with 32 bits per slot needs 3.072 MHz BCLK; INMP441 specifies up to 3.2 MHz BCLK.
No MCLK connection is required for this interface. These are design values,
not measurements of the purchased module.

| INMP441 breakout label to confirm | Electrical connection | Initial profile proposal |
| --- | --- | --- |
| VDD / VCC | ESP board regulated 3V3, measured before connection | Never 5V/VBUS |
| GND | Same ground as ESP32 | Short common ground |
| SCK / BCLK | ESP32 clock output | GPIO4, PROVISIONAL |
| WS / LRCLK | ESP32 word-select output | GPIO5, PROVISIONAL |
| SD / DOUT | Microphone output -> ESP32 DIN | GPIO6, PROVISIONAL |
| L/R | GND for left; 3V3 only if right configured | GND, left slot |

This is a logical net list, **not a verified physical header/breadboard diagram**.
No breadboard hole positions are supplied until actual PCB/header orientation is
confirmed. Review G0 photographs, then annotate the actual header labels and draw
that physical diagram in the board evidence folder. Do not count from a generic
DevKitC photograph. The board dossier records this remaining physical gate.

| GPIO group | Reservation |
| --- | --- |
| 19/20 | Native USB D-/D+, never microphone |
| 26..37 | Conservative flash/PSRAM exclusion; N16R8 includes 35..37 octal PSRAM |
| 0/3/45/46 | Straps/boot, excluded |
| 43/44 | UART0 debug, preserve recovery/log access |
| 38/48 (and variant-sensitive 47) | LED/voltage/revision concerns; excluded initial profile |
| 4/5/6 | Only a proposal, usable after actual header/conflict confirmation |

Power off before wiring. If headers are not soldered, use a stable jig, correct
orientation and proper solder joints; inspect for bridges/cold joints with power
removed, and continuity-check each connection. Do not wedge loose unsoldered pins
into the board as a reliable connection. Keep the microphone's bottom acoustic
port unobstructed. Add/verify local decoupling according to the breakout design.
Never connect a PAM8403 amplifier to any INMP441 digital pin.

## Activate the independent source adapter only after electrical review

Default release: deterministic source 1 only, bootable without sensors. Live mode
0 returns unsupported. After G1 passes and wiring is checked, in the exported IDF
shell run `idf.py menuconfig` from firmware. Under AuscultaForge board profile,
enable the physically reviewed INMP441 profile, enter the confirmed BCLK/WS/DIN
pins and selected slot. Then use `bringup.py build`, review source_modes in the
new manifest and use the explicit-confirmation flash workflow again.

The live path uses IDF 5.5.1 `i2s_std`, 48 kHz Philips I²S, two 32-bit slots,
8 DMA descriptors of 256 frames and an eight-block bounded task queue. A dedicated
RX task reads DMA; no USB call occurs in its ISR. The selected 24-bit sample is
shifted from bits 31..8 and explicitly sign-extended to the canonical LSB S32
container. Portable edge-vector tests cover negative full scale, -1, zero and
positive full scale. Source 0 has no synthetic fallback and no simulated flag.

Acquisition start resets its bounded queue; STOP disables RX, waits for the owner
task and accounts for completed blocks discarded at stop as drops. DMA overflow
is reported; an unknowable hardware sample loss is not converted into an invented
exact sample count. `generated_samples` in this adapter counts read DMA samples,
not independently measured acoustic conversions. Live timestamps estimate first
sample from observed block completion minus nominal block duration; scheduler,
buffer latency and the microphone digital-filter delay remain unmeasured.

The separate I2S-enabled compile-check binary is **NOT FOR FLASHING**: provisional
4/5/6 were enabled only to compile that code path, not to attest physical wiring.

## G2 and G3 acceptance record

1. Photograph and measure VDD before powering the module; check ground and
   continuity with power removed. Record multimeter ID and uncertainty.
2. Confirm WS near 48 kHz and BCLK near 3.072 MHz with a scope/logic analyzer;
   preserve captures, probe points and instrument timebase uncertainty.
3. Use Device Center HELLO, then source 0. Record a ten-second raw session.
   Save unprocessed WAV and metadata; check actual accepted/recorded sample counts
   and source provenance. All-zero data does not establish a functioning mic:
   inspect VDD/GND, slot selection, clocks, SD and alignment. Digital silence
   cannot by itself distinguish quiet conditions from a disconnected microphone.
4. Reopen the raw session. Compare DC mean, RMS, peak, clipping fraction, waveform
   and Welch PSD for quiet-room and controlled nearby sound. Preserve processing
   settings and separate processed outputs. A clap/voice checks functionality only.
5. Inspect recording/DSP/display queue health, CPU and UART heap/stack logs;
   repeat start/stop and unplug/recovery with fresh sessions. Failed recordings
   must remain failed evidence. Display decimation must not change the raw file.
6. For low-frequency work, specify a calibrated reference excitation, placement,
   coupling, reference sensor and uncertainty. INMP441's typical low-frequency
   roll-off is around 60 Hz; talking/music cannot validate 20–60 Hz PCG response.
   Chestpiece/phantom characterization is a later independent gate.

No clinical interpretation and no automatic MurmurMIL prediction on this sensor
domain. Export a support bundle and a fault hypothesis for noise, not a medical
finding. Never filter or overwrite the original raw recording as evidence.

## Executable raw-recording screen

After source0 START in Device Center, immediately start recording in Live Workspace.
Record quiet background and then a separate documented sound stimulus. STOP
acquisition finalizes an active recording; alternatively stop recording explicitly
first. Record accepted versus recorded counts: a recording started after START
does not contain the earlier frames. Supply/clock/UART and signal evidence are
separate. A bounded target is ten seconds; repeat a fresh session for each condition.

From the repo root replace SESSION_ID with the actual saved session directory:

```powershell
.\.venv\Scripts\python.exe tools/hardware/bringup.py qualify --session experiments/sessions/SESSION_ID --output experiments/hardware/g2-quiet.json
```

This validates session integrity/hash and reopens **raw** mono float32 WAV. It
reports exact sample count, nominal rate, duration from count, zero/constant input,
DC/RMS/peak in full-scale units, saturation fraction and linear Welch PSD in
FS²/Hz. Output must be a new file. Compare the controlled-sound report without
replacing originals. The report explicitly does not certify physical origin,
clock accuracy or acoustic response. UI errors/UART DMA and drop counters must
be inspected independently; zero input cannot diagnose absent versus quiet mic.

Recording buffers accepted normalized samples in RAM and writes WAV on STOP;
use short bounded sessions and orderly STOP. Process/power loss before STOP can
leave an incomplete marker without durable audio. This is a known limit, not a
claim of continuous crash-proof disk acquisition.
