# W06 Module A: First Transducer Gain and Bandwidth

**Week:** 6  
**Module:** A - Acquisition Hardware and Characterisation  
**Owner:** Kaan  
**Status:** PARTIAL - integration documented; controlled gain and bandwidth OPEN  
**Updated:** 25 November 2026  
**Original reporting window:** 26 October-1 November 2026  
**Actual laboratory evidence dates:** 18 and 25 November 2026

## Objective

The advisor's Week 6 Module A task is to connect the first transducer and measure gain and bandwidth using a function generator. First-transducer integration was documented; a controlled gain/bandwidth result is not yet available.

Kaan reported on 19 November that the advisor did not require a separate analogue measurement exercise for the current Week 6 task. The present scope therefore concerns the INMP441 digital acquisition path and its acoustic characterisation. This scope clarification does not establish that a particular alternative measurement method was approved or performed.

This is a dated follow-up to the original Week 6 task. Later phantom work is included as supporting evidence and is not presented as completed during the original reporting window, or as automatic closure of the separate Week 7/8 submissions.

## Inputs / Dependencies

- Module A hardware: INMP441 MEMS microphone, ESP32-S3 breadboard assembly, stethoscope/chestpiece and sealed Y-tubing.
- Reported excitation path: Realtek AUX -> independently powered PAM8403 (regulated 5 V / 2 A supply rating) -> 30 mm / 12 ohm exciter -> suspended cardboard plate -> cured RTV-2 silicone phantom -> chestpiece.
- Module B support: stable I2S acquisition/start behaviour, wiring verification and transport metadata.
- Module C support: reference playback, raw recording, declared processing settings and reproducible analysis.
- Recorded interface: BCLK GPIO4, WS GPIO5, SD GPIO6, L/R GND; 48 kHz; left channel; 24-bit data in 32-bit I2S slots.
- A documented input/reference method and valid quiet baseline remain necessary for quantitative characterisation. Silicone thickness/hardness, actual fixture dimensions and contact load were not established by the supplied records.

The amplifier is part of the exciter playback path, not an analogue microphone front end. Neither PAM8403 BTL output is connected to ground.

## Work Performed

### 18 November - first-transducer integration

Kaan assembled the INMP441/ESP32-S3 breadboard connection. Ozan performed the supply/acquisition work reported in the earlier laboratory record. The [18 November release evidence](https://github.com/egecagintepe/ausculta-forge/blob/316f003f7986338e854b929bfe3b62c420c3eb53/docs/engineering/release/WEEK9_18NOV2026_PHYSICAL_G2_ACCEPTANCE.md) is retained as historical evidence. Its broad acceptance labels are not substituted for a controlled Module A gain or bandwidth measurement.

### 25 November - physical phantom integration and exploratory tests

Kaan's recorded contribution covered silicone handling/integration, suspended cardboard support assembly, exciter positioning/mounting, chestpiece coupling, sealing of the Y-tubing interface and collaborative documentation review.

Ozan performed the amplifier power/signal integration and AUX conductor identification. Ege provided the host workflow, guided diagnostics, analysis and evidence organisation. Shared software/acquisition results are cited as team evidence, not attributed to Kaan as independently executed software tests.

An initial SCK connection to GPIO3 produced an all-zero recording. Nonzero microphone data were recovered after correction to GPIO4. Two guided diagnostic sessions detected three of three prescribed taps. Three cardboard-supported PCG trials and two direct-silicone attempts were reported. The unsuccessful records were retained.

## Evidence

- [English Module A report](W06_A_first-transducer-lab-update-report_v01.pdf) - nine pages; hardware path, photographs, reported metrics, limits and roadmap audit. Internal revision 2.0 dated 25 November; repository version v01.
- [Open work / handoff register](W06_A_open-work-and-handoff_v01.md).
- [As-built hardware](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/HARDWARE_AS_BUILT.md).
- [Experiment results register](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/EXPERIMENT_RESULTS.md).
- [Laboratory milestone and roles](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/LAB_MILESTONE_REPORT.md).
- [Known issues and proposed retests](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/KNOWN_ISSUES_AND_NEXT_STEPS.md).
- [Evidence manifest](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/EVIDENCE_MANIFEST.json) - indexes 12 local raw recordings; paths/hashes do not provide the raw audio files themselves.
- [Evidence commit dc62651](https://github.com/egecagintepe/ausculta-forge/commit/dc62651d4ed5b1b1cd02c03d67979135c4df66aa) includes a Kaan co-author credit.
- The [laboratory PR #36](https://github.com/egecagintepe/ausculta-forge/pull/36) was OPEN at preparation. Source links above are pinned to its inspected commit.

The source WAVs and analysis JSON files were not available for independent reanalysis of this submission. Numerical values were checked against the versioned summaries. This report does not claim new raw-data calculations.

## Results

| Item | Reported evidence | Bounded interpretation |
|---|---|---|
| Corrected microphone connection | Session `session_20261125_075205_9923da49`: 479,784 nonzero samples out of 480,000 | Microphone data recovered after SCK correction; not gain/bandwidth calibration. |
| Guided coupling diagnostics | Sessions `session_20261125_083848_02ff521c` and `session_20261125_100542_a818e843`: 3/3 taps each | Response through the coupled path was demonstrated; frequency response was not measured. |
| Q01 quiet baseline | `session_20261125_093843_959d7eb0`: full 0-10 s, 20-500 Hz RMS 0.045325 FS; 254 samples above absolute 0.98 FS (0.0529%) | **FAIL** under the recorded team protocol. Later 1-10 s RMS 0.001469 FS is supplementary, not a replacement pass. |
| Primary exploratory PCG | Trial `trial_20261125_095717_275ae8`; session `session_20261125_095718_2d385ca8`; 20% Windows playback setting | Initial physical PCG transmission evidence; software volume is not calibrated acoustic input. |
| Primary full record | 480,000 samples at 48 kHz; zero reported in-stream drops/CRC errors; 243 samples above absolute 0.98 FS (0.0506%), all in the first second | Transport continuity does not remove the startup transient. The 0.98 FS indicator is near-clipping, not proof of saturation. |
| Primary supplementary 1-10 s segment | RMS 0.010761 FS over 20-500 Hz; coherence 0.8820 over 20-250 Hz; NCC 0.1772 at +142.08 ms; S1/S2 10/16 (62.5%) | **P01 NOT YET ACCEPTED**: Q01 prerequisite, NCC and event-match criteria remain unmet. |
| Contextual level comparison | +17.30 dB against the later Q01 segment | Not measured gain, microphone sensitivity or calibrated acoustic SNR. |
| Direct-silicone attempts | Trials `trial_20261125_100205_921544` and `trial_20261125_100747_443db6`: exact-zero recordings | Invalid acoustic A/B evidence; no claim that silicone performed worse. |
| Controlled gain/bandwidth | No controlled result or measured cutoff identified | **OPEN / NOT YET MEASURED.** |
| Whole-chain swept response | No 20-500 Hz sweep result identified | **OPEN / NOT YET MEASURED**; original Week 8 task. |

The quoted Q01/P01 thresholds belong to the team's protocol and are not advisor grading thresholds. Internal proof-of-concept acceptance is not a passed academic gate.

## Open Decisions / Risks

- **OPEN:** controlled input/reference method, stated reference level and measurable gain/bandwidth acceptance criteria for the digital/acoustic path.
- **OPEN:** full-chain 20-500 Hz response, including the 20-60 Hz region; neither a single 120 Hz tactile check nor PCG playback is a frequency sweep.
- **OPEN:** startup transient and intermittent all-zero captures. Clock restart and contact disturbances are possible explanations, not established sole causes.
- **OPEN:** valid Q01 baseline and P01 acceptance. A settling interval must be declared before the new test; removing a failed portion afterwards does not convert the original test to PASS.
- **OPEN:** actual phantom dimensions, material properties, mounting and contact conditions. Earlier proposed dimensions are not as-built measurements.
- **OPEN:** reproducibility from preserved raw recordings and exact analysis settings. A table or PDF alone does not reproduce a result.
- **OPEN:** valid matched-condition material comparison after acquisition stability is demonstrated.

No shared team decision was closed by this submission.

## Next Week Handoff

The [carry-over register](W06_A_open-work-and-handoff_v01.md) records original task weeks and evidence required for closure.

1. Kaan: document the actual phantom and coupling geometry; preserve the positive-trial arrangement as a baseline and add cable restraint.
2. Ozan with Ege: investigate startup/all-zero capture behaviour; provide a predeclared settling/evaluation capture procedure and valid baseline analysis.
3. Kaan with Modules B/C: execute a fixed-condition 20-500 Hz swept test, preserve source/capture files and settings, and report the bounded whole-chain response. Relate a defined input/output measurement to the open Week 6 gain/bandwidth task.
4. Team: repeat PCG verification after an accepted quiet baseline; retain failed and successful records.
5. When deferred work is actually completed, record its true completion date in that week's report and link it back here. Do not backdate it or close it based on report publication.

The Week 10 two-transducer comparison and Week 11 ten-repeat study remain later roadmap tasks; they are not labelled overdue Week 8 work.

Student project; phantom-only testing; no diagnostic claim.
