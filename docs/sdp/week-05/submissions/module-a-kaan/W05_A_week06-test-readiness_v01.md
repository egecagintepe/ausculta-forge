## 8) A5 - Week 6 test checklist

All results are **PENDING**. ESP32 receipt removes that item’s delivery blocker; it does not establish a working chain. Each test requires its own verified prerequisites.

| ID / status | Action | Prerequisite / retained evidence |
| --- | --- | --- |
| W6-A01 / PENDING | Power / wiring | Exact board pinout, grounds, shorts, polarity and measured rails; photo. No 5 V on INMP441 power/signals. |
| W6-A02 / PENDING | First I²S capture | Agree Module B profile; verify clocks/channel, sign extension, sample alignment, timebase and loss count. Raw data + firmware version. |
| W6-A03 / PENDING | Quiet baseline | Fixed mounting; amplifier on/off separately. Duration, filtering, RMS/PSD and environment. System noise, not isolated microphone self-noise. |
| W6-A04 / PENDING | 50 / 100 / 200 / 500 Hz | Approved low-level drive; fixed source/mount. Fundamental, harmonics, peaks and anomalies with actual drive settings. |
| W6-A05 / PENDING | 20 / 30 / 40 / 50 / 60 Hz | Controlled drive; track source/amplifier/exciter behaviour. An independent reference is needed to isolate microphone attenuation. |
| W6-A06 / PENDING | Contact / mounting | Change one variable: remount, force or same-grade thickness. Ten-remount method on page 5. Retain valid and flagged runs. |
| W6-A07 / PENDING | S1/S2 reference PCG | Use the team-selected dataset/file; retain segment, sample rate, scaling and playback path. No new dataset was selected here. |
| W6-A08 / PENDING | ECM gain / bandwidth | Reviewed AFE/ADC, correct generator attenuation/bias and verified instruments. Do not inject a generator signal into I²S. |

Last documented Module B baseline [4]: nominal 48 kHz, 64 BCLK periods/frame (3.072 MHz), proposed GPIO4/5/6 and 3.3 V microphone supply. This historical handoff is not a new pin approval. Ozan must confirm actual board mapping, firmware and USB routing before connection.

Student project; phantom-only work; no diagnostic claim.

## Source key

Bracketed source numbers refer to the reference list on page 10 of the [English report](W05_A_acoustic-hardware-preparation-report_v01.pdf). These notes are companion extracts; proposed dimensions and PENDING tests are not measurement results.
