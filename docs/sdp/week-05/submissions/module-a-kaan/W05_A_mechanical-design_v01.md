## 3) A2 - INMP441 acoustic mounting

A removable insulated cassette linked to the existing chestpiece outlet through a short tube was proposed. The cassette will be restrained on the frame; the loading screw will act on the chestpiece rim, never on the microphone. Cable strain relief and a slack loop will limit pulling and vibration. Acoustic improvement has not been validated.

Dimensioned drawing: see the [English report](W05_A_acoustic-hardware-preparation-report_v01.pdf), page 3.

**Before fabrication:** measure PCB outline, component/header heights, port coordinates, head size and outlet diameter. The 40 × 40 × 12 mm cassette is a conditional envelope, not the breakout datasheet size. Enlarge it if necessary. Tube bore must fit the actual outlet; the nominal 20 mm tube must not kink. [5, 6]

The acoustic opening must clear the port diameter plus twice the alignment uncertainty. A nominal 2 mm bore is only a starting proposal. A 1 mm annular gasket is proposed around the port, leaving the hole open. Glue and fasteners must not enter it. Compression stops and insulated edge supports will limit PCB bending. This gasket is distinct from the 3 mm phantom layer. [6]

Record tube/cavity geometry, gasket compression and orientation. The INMP441 typical acoustic lower corner is about 60 Hz; the 20-60 Hz risk remains open. Its internal digital high-pass corner is a different specification. A seal alone does not prove low-frequency suitability. [5]

## 4) A3 - Dimensioned phantom proposal

All dimensions are design proposals, not measurements of received parts. A removable prototype was defined. Fabrication must wait for the actual-part fit checks on page 5.

Dimensioned drawing: see the [English report](W05_A_acoustic-hardware-preparation-report_v01.pdf), page 4.

The base thickness was increased from the Week 4 proposal of 6 mm to a nominal 12 mm to provide more material for fixture attachments; stiffness remains untested. M8 posts set coarse height; the central M6 screw and swivel foot load the head rim. The microphone cassette is outside the loading path.

## 5) Build list and ten-repeat method

| Proposed part | Nominal size / quantity | Condition |
| --- | --- | --- |
| Plywood base | 200 × 150 × 12 / 1 | Flat base; four Ø9 holes as drawn. |
| Rails / bridge | 30 × 150 × 18 / 2; 190 × 40 × 18 / 1 | Rail centres x=20/180; bridge y=75. M6 connections at (20,75)/(180,75). |
| Posts / loading | M8 × 180 / 4; M6 × 100 / 1 | Nuts/washers, captive M6 nut, swivel foot, rim collar; verify travel. |
| Stage / drive plate | 80 × 80 × 30 ring; opening 40 × 40; plate 60 × 60 × 2 | Exciter centred underneath; consistent edge support and removable clips. |
| Coupling layer | Silicone 60 × 60 × 3 | Same-grade 2 and 5 mm alternatives; gel only in a sealed thickness-controlled pouch. |
| Other mounting | Cassette, tube, gasket, clamps | M3 screws, insulated supports, cable ties and position stops. |

**Fit conditions (mm):** exciter body-plus-lead height ≤25 within the 30 mm stage retains 5 mm clearance; otherwise raise the stage/bridge. Confirm the head fits the 60 mm coupon without clip interference. Rail underside height is provisionally adjustable over 70-120 mm; measured head/foot sizes determine the setting. The 2 mm acrylic drive plate requires crack, deflection and resonance checks. Receipt of these mechanical items is unconfirmed.

### Ten independent remounts - all results PENDING

Use the same coupon, orientation, tube route, waveform, level and acquisition profile. Each run requires removal, replacement against stops, force adjustment and the same recorded settling time. Initial 1 N force is an engineering proposal, not an accepted limit. Use a force gauge or tared scale supporting the whole stage; screw turns do not establish force. Agree force tolerance and settling time before tests.

Runs 01-10 retain before/after force, thickness, mount ID, raw-file ID and anomalies. Fixed-mount repeats must be reported separately. Record silicone grade/hardness and measured thickness; no material has been acoustically qualified.

**Availability / potential missing items:** verify chestpiece, tube, gasket, silicone, base/rails, fasteners, force gauge or scale, caliper, multimeter, regulated supply, oscilloscope, function generator and PC audio output in lab stock before procurement. Their absence has not yet been confirmed; only unresolved availability is recorded.

## 6) First low-level excitation procedure

**PC analogue output → PAM8403 → 30 mm / 12 Ω exciter → drive plate + silicone → chestpiece → INMP441.** The amplifier drives the exciter; it is not the microphone AFE. If no PC analogue output is available, an available USB audio device/DAC must be verified.

**BTL connection:** use L+ and L- of one complete channel. Neither terminal is ground. Do not connect either to ground, another output channel or an oscilloscope ground clip. Source ground belongs only to the amplifier input reference. Output measurements require an appropriate differential/isolated method and verified instrument limits. [7]

| Step | Planned procedure / stop conditions |
| --- | --- |
| 1 - Unpowered | Inspect labels, polarity, soldering and continuity. Confirm exact exciter model, rated power and nominal impedance. DC resistance is not AC impedance. |
| 2 - Supply | Verify the actual board supply/input circuit. Use regulated power within rating; current limit depends on the verified load/board. Nominal 5 V is proposed. Begin with PC and amplifier levels at minimum. |
| 3 - Connect | Connect the exciter before power. Do not parallel outputs or drive the exciter directly from the PC jack. Secure the assembly and wiring. |
| 4 - Start | Apply a short low-level 100 Hz sine. Increase only until a usable response is observed. Stop for heating, buzzing, loose contact, excessive motion, current limiting or clipping. |
| 5 - Extend | Only after the initial check, proceed to the frequency list. Do not increase low-frequency drive simply to compensate for microphone attenuation. Check fixture and ratings each time. |
| 6 - Record / change | Set volume to zero and remove power before rewiring. Retain waveform, settings, supply/current observations, wiring photo and aborted-run notes. All steps: PENDING. |

No maximum safe drive voltage was assigned because the exact exciter power rating is unconfirmed. The 30 mm / 12 Ω label and amplifier headline power do not prove 20-500 Hz performance or a safe displacement limit. No initial drive test was performed.

Student project; phantom-only work; no diagnostic claim.

## Source key

Bracketed source numbers refer to the reference list on page 10 of the [English report](W05_A_acoustic-hardware-preparation-report_v01.pdf). These notes are companion extracts; proposed dimensions and PENDING tests are not measurement results.
