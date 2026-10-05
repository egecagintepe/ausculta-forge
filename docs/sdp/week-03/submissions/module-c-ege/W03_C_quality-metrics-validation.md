# W03 Module C: Quality Metrics Validation

**Week:** 3  
**Module:** C — Computer Application & Quality Assessment  
**Owner:** Ege  
**Status:** COMPLETE — software / known-condition validation complete; physical hardware validation pending

## Objective

Verify the minimum Module-C recording/stream quality mechanisms against deterministic known-condition inputs and define the host-side requirements needed for the Week-3 Module-B-to-Module-C interface draft.

This Week-3 activity verifies software behavior only. It does **not** claim that physical stethoscope quality thresholds, SNR limits, contact-loss thresholds, or phantom performance have been calibrated. Those require the real acquisition chain and phantom measurements in later weeks.

## Inputs / Dependencies

- Week-02 Module-C status and measurement/quality plan.
- Week-02 Module-B-to-Module-C interface requirements.
- Existing `pcg_core` signal-quality, streaming-quality, and recording modules.
- Existing deterministic automated tests using synthetic signals and known sequence/sample counts.
- Module-B Week-3 frame/transport draft remains a joint dependency for final device-to-host integration.
- Real hardware capture is **not yet available** and is not required for this software-level verification.

## Work Performed

### 1. Signal level / RMS validation

The existing scientific signal-quality implementation computes RMS, peak magnitude, peak-to-peak value, crest factor, digital full-scale utilization, and related scalar quantities on full-rate arrays.

Known-condition verification uses a deterministic 100 Hz sine wave with amplitude 0.5. The automated test checks the analytical reference:

```text
RMS = A / sqrt(2)
    = 0.5 / sqrt(2)
    ≈ 0.353553
```

The same test checks approximately zero DC mean, peak magnitude = 0.5, peak-to-peak = 1.0, crest factor = sqrt(2), and zero digital-saturation samples.

### 2. Digital clipping / saturation validation

Digital clipping is treated strictly as normalized digital full-scale utilization, **not** as proof of acoustic microphone overload.

A deterministic test sequence contains:
- 5 samples at +1.0,
- 3 samples at -1.0,
- 1000 samples total,
- clipping threshold = 0.999.

Expected and asserted result:

```text
digital_saturation_count    = 8
digital_saturation_fraction = 8 / 1000 = 0.008
```

The result provenance explicitly labels this condition as digital full-scale hits only and does not convert it into an acoustic-overload claim.

### 3. Continuity / gap detection validation

`StreamQualityMonitor` checks monotonically increasing block sequence numbers independently of host wall-clock arrival time.

The deterministic gap test injects:

```text
received sequence: 0 -> 3
expected next:      1
missing blocks:     1, 2
```

The monitor is expected to report:
- `dropped_blocks = 2`
- `sequence_discontinuities = 1`
- unhealthy stream state.

Separate automated cases also exercise repeated sequence values, out-of-order blocks, timestamp regression, and mid-stream sample-rate changes.

This validates the Module-C mechanism that will later consume the continuity field supplied by Module B. It does **not** yet validate a physical USB link.

### 4. Recording path / sample-count consistency validation

The existing session recorder is verified with two deterministic `SampleBlock` objects containing four samples each.

Expected and asserted session metadata:
- 2 blocks,
- 8 total samples,
- unchanged sample rate,
- first/last sequence retained,
- WAV file created,
- JSON session sidecar created,
- recorded float32 samples preserved exactly on WAV readback,
- SHA-256 stored for the written WAV.

A separate test rejects a sample-rate change during an active recording rather than silently producing a corrupt single-rate WAV.

### 5. Week-3 host interface requirements carried forward

Module C requires the embedded stream to expose the following conceptual information:

1. protocol/schema version,
2. message/frame type,
3. monotonic sequence or cumulative sample-continuity mechanism,
4. payload sample count,
5. declared sample rate,
6. channel count,
7. explicitly declared sample representation/alignment,
8. device/stream status flags,
9. hardware overflow/drop indication,
10. stream start/stop semantics,
11. device/firmware identification.

Application-level checksum/CRC remains an **OPEN Week-3 joint B/C decision** because native USB already provides lower-layer integrity mechanisms. Packet size, exact wire layout, and final sample container are also not frozen in this document.

## Evidence

Repository evidence:

- `software/pcg_core/scientific/signal_quality.py`
  - deterministic RMS, peak, crest-factor, digital-saturation and related scalar metrics.
- `software/tests/test_scientific_signal_quality.py`
  - analytical sine-wave RMS/crest-factor oracle,
  - amplitude scaling,
  - deterministic digital full-scale hit count/fraction,
  - invalid input rejection.
- `software/pcg_core/streaming.py`
  - `StreamQualityMonitor` sequence continuity, timestamp and sample-rate monitoring.
- `software/tests/test_streaming.py`
  - injected sequence-gap, repeat, out-of-order, timestamp-regression and rate-change cases.
- `software/pcg_core/recording.py`
  - session recording, sample counting, WAV persistence, metadata and hash generation.
- `software/tests/test_recording.py`
  - exact sample preservation, total-sample accounting, replay compatibility and rate-change rejection.
- `docs/sdp/week-02/bc-interface-requirements.md`
  - host interface requirements and Week-3 open decisions.
- `docs/sdp/week-02/measurement-quality-plan.md`
  - separation between software recording-quality indicators and mandatory physical characterization.

Validation traceability note:

- The runtime/software tree used by these tests has not changed since the last validated runtime checkpoint; subsequent changes up to the start of Week 3 are documentation-only.
- The prior runtime checkpoint reported the repository test suite passing with **274 tests passed**.
- No new runtime feature or quality threshold was introduced for this Week-3 task.

## Results

| Verification item | Known condition / oracle | Result |
|---|---|---|
| RMS / signal level | 100 Hz, amplitude 0.5 sine; expected RMS = 0.5/sqrt(2) | PASS — covered by deterministic automated test |
| Digital clipping | 8 full-scale samples in 1000 samples; expected fraction 0.008 | PASS — covered by deterministic automated test |
| Continuity / gap detection | sequence 0 -> 3; expected two missing blocks | PASS — covered by deterministic automated test |
| Recording sample count | two 4-sample blocks; expected total = 8 | PASS — covered by deterministic automated test |
| Exact raw sample preservation | float32 input samples written/read from raw WAV | PASS — covered by deterministic automated test |
| Physical PCG quality thresholds | requires real phantom/hardware recordings | NOT YET CALIBRATED |
| Physical SNR / contact-loss behavior | requires controlled acoustic bench conditions | NOT YET MEASURED |
| Real USB B->C integration | requires Module-B firmware/device stream | PENDING WEEK 5 |

### Interpretation

The minimum Module-C quality/recording mechanisms are already implemented and deterministically verifiable on known software inputs. Therefore Week 3 does not require a new quality-scoring feature.

The remaining risk is integration rather than scalar-metric implementation: Module B must provide an explicit continuity mechanism, sample format, status/error information and stable streaming contract so these mechanisms can be exercised on real acquisition data.

## Open Decisions / Risks

| Item | Status | Module-C position |
|---|---|---|
| USB application transport class: CDC-ACM vs Vendor Bulk | OPEN — joint B/C | Prefer the simplest transport that meets continuous throughput and robust reconnect requirements; freeze only after Module-B review. |
| Final wire-frame byte layout | OPEN — joint B/C | Requirements are known; offsets/magic/version layout must be agreed with Ozan. |
| Packet payload size | OPEN — joint B/C | 128/256/512-sample trade-off remains open. |
| Final sample representation | OPEN — joint B/C | Host requires explicit declared signed-PCM representation; current 24-valid-bit-in-32 baseline is not yet a permanent sensor-independent contract. |
| Application-level CRC/checksum | OPEN — joint B/C | Continuity detection is mandatory regardless; extra CRC must be justified against native USB integrity and implementation complexity. |
| Physical clipping/contact-loss thresholds | OPEN — later bench calibration | Do not freeze numerical thresholds before real phantom data exists. |

## Week-5 Host Acceptance Checklist

When Module B provides the first synthetic device stream, Module C will verify:

- [ ] supported protocol/profile accepted and incompatible profile rejected,
- [ ] known synthetic waveform arrives with correct sample ordering,
- [ ] declared sample rate/channel/sample representation are interpreted correctly,
- [ ] continuity field increments according to the agreed contract,
- [ ] intentional sequence gap is detected and logged,
- [ ] total ingested sample count matches total recorded sample count,
- [ ] raw WAV preserves the accepted sample stream,
- [ ] session metadata contains acquisition/profile and stream-quality information,
- [ ] disconnect/reconnect does not leave a corrupt recording or hung host state.

## Next Week Handoff

For the Week-04 application requirements freeze, Module C will convert the Week-3 joint B/C decisions into a testable host-interface specification.

No additional Module-C feature development is required before those interface decisions are made. The next major empirical milestone is the Week-5 synthetic end-to-end stream from Module B into the existing host display/recording path.
