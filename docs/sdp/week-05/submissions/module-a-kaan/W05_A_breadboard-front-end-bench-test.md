# W05 Module A: Breadboard Front-End Bench Test

**Week:** 5 (19-25 October 2026)
**Module:** A
**Owner:** Kaan
**Status:** PREPARATION DOCUMENTED; PHYSICAL TESTS PENDING
**Updated:** 27 October 2026 (repository reconciliation; report prepared 26 October)

## Objective

Prepare the acquisition hardware, removable INMP441 acoustic mounting and mechanical phantom for integration. Preserve the original advisor's Week 5 analogue front-end and shorted-input-noise task as an explicit outstanding experiment. The new coordination brief defers unapproved analogue construction; advisor confirmation of timing and scope remains required.

## Inputs / Dependencies

- Main path: INMP441 digital I2S microphone and ESP32-S3. PUI was replaced due to supplier lead time.
- Kingstate KECG2740PBJ remains the academic comparison candidate; MCP6022 is a proposed analogue-stage component, not an ADC.
- Latest owner confirmation: all items in the inventory table have arrived except Kingstate, which is awaiting delivery. Ordered quantities do not establish accepted quantities or inspection results.
- Actual board pinouts, head/PCB dimensions, exciter rating, mechanical materials, instruments and current Module B/Module C interfaces require confirmation.
- The report's Module B baseline is historical Week 4 documentation, not a newly approved pin map.

## Work Performed

### Completed design and preparation

A1-A5 were documented: receipt status, dimensioned removable microphone cassette and phantom proposals, coupling alternatives, a ten-remount method, BTL precautions, ECM/ADC research questions and Week 6 test prerequisites. The report is revision 1.1. Page 2 has two columns; all listed items except Kingstate are marked RECEIVED.

### Experiments with physical evidence

**NOT YET MEASURED for Module A.** No Module A measured data, hardware PASS or completed breadboard assembly is claimed. The [shared Week 5 status](../../README.md) records separate 26 October CLI/GUI G1 work; this submission neither repeats that work nor attributes it to Kaan. Real microphone G2 and acoustic characterisation remain pending.

### Work still blocked or not performed

The Kingstate comparison awaits the microphone and an approved bias/AFE/ADC path. The analogue shorted-input-noise experiment remains outstanding. Mechanical fit, fixture availability and all W6-A01 to W6-A08 tests remain unverified or unperformed. Receipt alone does not validate hardware.

## Evidence

- [English report](W05_A_acoustic-hardware-preparation-report_v01.pdf) - 10 pages, internal revision 1.1.
- [Material inventory](W05_A_material-inventory_v01.md).
- [Mechanical design and first-drive procedure](W05_A_mechanical-design_v01.md) - dimensioned drawings in report pages 3-4.
- [Week 6 test checklist](W05_A_week06-test-readiness_v01.md).

These are documentary outputs, not raw experimental evidence. No photographs or measurements were supplied.

## Results

Design/preparation documented. **Physical results: PENDING.** No gain, noise floor, response, clipping or repeatability measurement exists. No original Week 5 milestone completion is claimed.

## Open Decisions / Risks

- OPEN: advisor confirmation of deferred analogue/noise task and revised evidence requirements.
- OPEN: Kingstate receipt; ADC/AFE schematic and defined noise-test point.
- OPEN: actual part dimensions, mechanical fit, exciter power rating and available instrumentation.
- OPEN: INMP441 20-60 Hz response; whole-chain attenuation cannot be assigned to the microphone alone.
- OPEN: numerical acceptance limits, proposed 1 N contact force, proposed 6 dB headroom and current interface confirmation.
- PAM8403 BTL outputs must not be grounded or connected to an oscilloscope ground clip.

## Next Week Handoff

Apply W6-A01 to W6-A08 as their prerequisites become available: verify supplies/wiring, capture first I2S samples, record quiet system noise, test controlled 50/100/200/500 Hz and 20-60 Hz, compare contact conditions and prepare the team-selected S1/S2 PCG playback. Retain raw samples, settings, fixture revision, firmware commit and loss/clipping counts. Retain the original Week 6 electrical AFE gain/bandwidth measurement as a separate approved experiment.

This is a student project with no diagnostic claim. Physical tests are phantom-only. No shared decision or another module owner's work is modified.
