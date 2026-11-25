# Module A - Acquisition Hardware and Characterisation
## Week 6 submission - Kaan

**Status: PARTIAL - first-transducer integration documented; controlled gain and bandwidth measurements remain OPEN.**

**Updated:** 25 November 2026. Laboratory work is recorded on its actual dates (18 and 25 November), after the original Week 6 window of 26 October-1 November. The later work is not backdated.

## Deliverables

- [Required Week 6 task record](W06_A_first-transducer-gain-bandwidth.md) - objective, dependencies, individual work, evidence, results, risks and handoff.
- [English laboratory update report](W06_A_first-transducer-lab-update-report_v01.pdf) - approved report, internal revision 2.0; first repository file version v01; nine pages and four supplied laboratory photographs.
- [Open work and later-week completion register](W06_A_open-work-and-handoff_v01.md) - original task week, current status, owner/support and required closure evidence.

## Current evidence

INMP441/ESP32-S3 integration was documented. On 25 November, an exciter/cardboard/RTV-2 silicone/stethoscope phantom path was assembled and exercised with a reference PCG. The positive exploratory run supports initial physical transmission. Q01 remains FAIL and P01 remains NOT YET ACCEPTED in the team's recorded protocol. Controlled acquisition gain/bandwidth and the Week 8 swept whole-chain response remain unmeasured.

The gain/bandwidth task is not closed by publication of this report. The advisor direction reported by Kaan on 19 November excludes a separate analogue measurement exercise for the current Week 6 task; the digital/acoustic characterisation remains open.

The [shared laboratory PR #36](https://github.com/egecagintepe/ausculta-forge/pull/36) was open at this update. Its evidence is linked by immutable commit below and is not represented as a merged weekly submission:
- [Laboratory milestone record](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/LAB_MILESTONE_REPORT.md)
- [Experiment results](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/EXPERIMENT_RESULTS.md)
- [As-built hardware](https://github.com/egecagintepe/ausculta-forge/blob/dc62651d4ed5b1b1cd02c03d67979135c4df66aa/docs/lab/2026-11-25/HARDWARE_AS_BUILT.md)

Raw WAV and analysis JSON files were not independently reanalysed for this submission. The PDF reports source results and their limitations; its charts reproduce reported summaries rather than new raw-data calculations.

## Submission conventions

Versioned deliverables follow `W06_A_<short-description>_vNN.<ext>`. The required existing Markdown template is maintained in place. Original source/report versions are preserved; future revised deliverables receive a new version suffix.

PDF SHA-256: `e1088b64b9a6ceea5a3bfc69c1232354defba09e0540eaae981568a9907d4b61`.

Student project; phantom-only testing; no diagnostic claim.
