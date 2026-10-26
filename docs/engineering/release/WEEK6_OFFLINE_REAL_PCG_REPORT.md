# Week 6 Offline Real PCG Dataset Acceptance — 2026-10-26

## Result and revision scope

**PARTIAL overall; PASS for the bounded backend recording/spectral/replay acceptance and five-file GUI import.** Local frontend audition does not provide backend Welch history or session recording. Continuous replay has a health-state limitation after EOF wrap. These are not physical or clinical acceptance results.

Baseline: `61cd48a09b5e310a8b99d7ddd0656af79d99b8c7`. Implementation: `06315de5d09f3fef915fd3ba14f84bdaada56d84`. Runs were performed against the baseline plus then-uncommitted changes now in that implementation; session JSON reports the HEAD at recording time (`61cd48a`), which must not be read as clean-tree provenance. The [machine summary](WEEK6_OFFLINE_REAL_PCG_SUMMARY.json) preserves source-file hashes, exact commands, UTC bounds, exit codes and evidence hashes. Only a descriptive source comment changed after the runtime checks.

Previous Week 6 software PASS, physical CLI G1 at `106d3e0` and physical GUI G1 at `59d773e` remain historical results in [the unchanged sprint report](WEEK6_SPRINT_REPORT.md). No COM7 access, physical START, G2, firmware work, installer rebuild or installed-version acceptance occurred in this task. Week 5 and Module A/B files were not changed.

## Collection, access and attribution

Initially `data/raw`, `data/processed` and `experiments/sessions` contained no WAVs. Existing CirCor files were found under `data/external/circor-heart-sound-1.0.3`; four WAV/HEA/TSV triplets were copied unchanged and each file checked against the freshly fetched official SHA256SUMS. One Challenge 2016 WAV was downloaded after discovering its name in the official training-a directory listing and verified against official SHA256SUMS. No full dataset download or unrelated demographic collection was performed.

- Oliveira et al. (2022), [The CirCor DigiScope Phonocardiogram Dataset v1.0.3](https://physionet.org/content/circor-heart-sound/1.0.3/), DOI [10.13026/tshs-mw03](https://doi.org/10.13026/tshs-mw03).
- Clifford et al., [Classification of Normal/Abnormal Heart Sound Recordings: PhysioNet/CinC Challenge 2016 v1.0.0](https://www.physionet.org/content/challenge-2016/1.0.0/). The non-www page timed out; the official www page and official file listings succeeded.
- Access and dataset license checked before collection: **Open Data Commons Attribution License v1.0**. Dataset/license pages, official checksums and the license copy remain local. The separate CC-BY article citation text is not substituted for the dataset license.

Local collection: `data/raw/week6_real_pcg_20261026`; local `manifest.json` records exact URLs, versions, license/attribution, per-file SHA-256, format, fs, channels, N and duration. Technical pseudonymous filenames identify public recordings; no patient names or demographics are reproduced. WAV/HEA/TSV, source audio, session audio, model files and waveform screenshots are excluded from Git.

All source WAVs are mono PCM16. This small selection spans four CirCor auscultation locations and two rates; it is not a representative pathology cohort.

| Record | Source fs (Hz) | N | Duration (s) | Nyquist / final Δf (Hz) | Backend one-pass recording/replay |
|---|---:|---:|---:|---:|---|
| C1 / 40058_AV.wav | 4000 | 47552 | 11.888 | 2000 / 15.625 | PASS |
| C2 / 24160_MV.wav | 4000 | 90368 | 22.592 | 2000 / 15.625 | PASS |
| C3 / 49568_PV.wav | 4000 | 113792 | 28.448 | 2000 / 15.625 | PASS |
| C4 / 49627_TV.wav | 4000 | 127360 | 31.840 | 2000 / 15.625 | PASS |
| P1 / a0001.wav | 2000 | 71332 | 35.666 | 1000 / 7.8125 | PASS |

## Production paths and actual GUI scope

The actual GUI was opened on Windows in the Codex in-app browser at `127.0.0.1:3000`, running current React/Vite source with the Python source backend on loopback `127.0.0.1:8000`. This is browser-rendered application GUI evidence, **not a new packaged Tauri/installer acceptance**. Both task-owned servers were stopped and both listening ports released after testing.

All five WAVs were selected through the real file chooser. Visible filename, FILE AUDITION origin, 4.0/2.0 kHz and rounded durations 11.9/22.6/28.4/31.8/35.7 s were checked. Exact sample counts are verified in production engine/backend tests; the GUI does not expose exact N. Raw and fixed preview waveform canvases rendered. P1 PLAY/PAUSE and paused skip-to-origin / approximately 0.8 s seek worked with output muted. Bell, diaphragm, extended and recommended controls were selected without clobbering P1's 2 kHz source rate. No white screen was observed in these successful paths; malformed-file GUI recovery was not exercised.

| Feature | Local frontend file audition | Backend WAV/session replay |
|---|---|---|
| Decode and rate | PASS, five actual imports; PCM16/IEEE float32 little-endian WAV uses source-preserving parser | PASS, all five files; session selection preserves real fs |
| Waveforms / filtering | Raw and fixed preview rendered; preview is explicitly labeled separately from playback filtering | Production filtered/raw data generated; four presets retain N with finite values for all five sources |
| Welch / timed history | NOT_SUPPORTED in this path; honest empty-state guidance added | PASS numerically on five complete files; actual GUI rendered C1 (4 kHz) and P1 (2 kHz) spectra/history |
| Recording | NOT_SUPPORTED; misleading record button disabled | Five full-file API sessions PASS; separate actual GUI start/stop session PASS below |
| Playback / replay | GUI P1 play, pause and seek observed | API-selected replay rendered in GUI, including the GUI-recorded session; numerical sample replay PASS |
| Errors / labels | No crash on valid inputs; invalid WAV parser rejects truncation/layout/NaN in tests | Replay source names and hardware-disconnected labels verified; no physical-device claim |

Source rates must not become the playback device's 48 kHz. The fix separates source arrays from a playback-only interpolated buffer (minimum playback rate 8 kHz); analysis/export keep source fs and N. Export now writes the actual source rate instead of fixed 4 kHz. PCM16 export is a quantized serialization, not an original-byte hash assertion. Supported source-preserving WAV input is PCM16 or IEEE float32; other WAV encodings are explicitly rejected. Non-WAV fallback still uses WebAudio decoding and may resample.

The local fixed audition preview is **not** a measured bandpass trace and does not follow the selected playback preset; its label and code comment now say so. Browser WebAudio presets (Bell 20–100, diaphragm 100–500, extended 10–2000, recommended 20–200 Hz) differ from backend presets (20–120, 100–500, 20–600, 20–200 Hz). Button selection is not a numerical transfer-function validation, and preset equivalence is not claimed.

## Spectral timing, frequency and source isolation

Five one-pass production display-pipeline runs checked actual window bounds against source N/fs, fs preservation, fs/2 Nyquist, actual fs/nperseg bin spacing and `realtime_wav` origin. Lower time bound tolerance was declared as one source sample (floating subtraction can yield -1.11e-16 at the first window); end bound tolerance is 1e-8 s. The first strict zero-bound test failed on that rounding case, was preserved, then the corrected tolerance run passed. These are Welch recent-data window timestamps, not inferred S1/S2 times or individual STFT hops.

| Record | Spectral frames | First input window (s) | Last input window (s) |
|---|---:|---|---|
| C1 | 47 | 0.000000 → 0.128000 | 10.880000 → 11.888000 |
| C2 | 88 | 0.000000 → 0.128000 | 21.376000 → 22.400000 |
| C3 | 111 | 0.000000 → 0.128000 | 27.264000 → 28.288000 |
| C4 | 124 | 0.000000 → 0.128000 | 30.592000 → 31.616000 |
| P1 | 140 | 0.000000 → 0.128000 | 33.664000 → 35.666000 |

Default final nperseg is 256: Δf 15.625 Hz at 4 kHz and 7.8125 Hz at 2 kHz; early frames may use fewer samples. GUI display bands were 0–2000 Hz and 0–1000 Hz respectively, with correctly labeled PSD reference `1 FS²/Hz`. Existing independent synthetic tone/SciPy oracles and history tests also passed. Real PCG has no known acoustic ground-truth frequency calibration.

Sequential GUI imports and C1→P1→recorded-session replay changed source names/rates and reset the displayed history range. Source selection gets a new display identity and now recreates filtering/quality state; existing production-helper tests verify stale columns, rewind, rate change and missing-update behavior. The stale imported filename previously remaining over a backend replay was reproduced and fixed. Numerical timing/reset checks are stronger than screenshot-only proof; source-switch appearance is not an acoustic calibration.

## Recording, JSON, integrity and provenance

Seven real-data test cases passed: two small source-rate/provenance regressions plus five full-file backend acceptance cases. Production FastAPI handlers, source generators, shared dispatch, recorder, display pipeline and session replay were exercised without lifespan/background pacing, driving exactly one complete source pass. This scope is explicitly API/software, not GUI recording.

For each full file: mono IEEE float32 WAV fs/N matched JSON; duration=N/fs; UTC boundaries ordered; session ID, first/last sequence/timestamps and source origin matched; all five quality error counters were zero; normalized audio equaled original PCM16/32768 exactly; replay preserved those values. Independent final-WAV SHA-256 matched `raw_wav_sha256`. The source PCM16 byte hash is separately stored as `processing_profile.source_wav_sha256` and differs from the reserialized float32 WAV hash. Only copied sessions were tampered with; all five corrupt copies failed integrity checks. Originals remain unchanged.

Separate GUI controls test: source chosen via API, then actual **Record Session / Stop Recording** buttons created `session_20261026_093813_b74580ba`, UTC 09:38:13.852645–09:38:19.343955. This is not a claim that the GUI file chooser starts backend replay. Output: **2 kHz, mono float32, 8192 samples, 4.096 s**, source offset 11136 samples (5.568 s), sequence 87–150. All session error counters were zero. Independent checks matched the exact original normalized source slice, final WAV SHA-256 `5ba8a96bc87ad377c0230044eaf2f0de4071326844642fd416689f2c9622a4f6`, UTC/order/origin and replay values. The recorded session was selected through API and rendered in GUI as SESSION REPLAY with hardware disconnected. Recording-active DOM, replay screenshot/DOM and result hashes are archived locally.

## Separate exploratory S1/S2 reference check

No training, threshold tuning or large benchmark was run. Used the existing non-production-validated `auscultaforge_circor_springer_ref_v1_fold0` model, SHA-256 `abe437aa55664a6e3bf18dede9db3573d9c396028886e4016afcc8d41f7e6674`. The candidate model under `experiments/models/benchmark/...` was empty; the valid saved benchmark model under `experiments/benchmarks/circor_springer_benchmark_20260927_162203/models/fold_0.json` was used unchanged.

Selection reconstructed the historical 50-subject / five-fold / seed-2026 fold-0 split, checked 40 training subjects / 128 training recordings against model metadata and chose four different held-out subjects. This is a reconstructed split with matching counts, **not cryptographic proof of historical training membership**. No broad generalization or clinical claim follows.

Inference received audio, fs and existing model only. Expert TSV was read after predictions; state 0 was excluded from both frame scoring and event evaluation. Predicted onsets outside annotated intervals were ignored, not used to influence the algorithm. Event matching uses 100 ms onset tolerance; annotated-frame agreement is a separate measure. Local `research_check.py`, its command and output are archived by hash.

| Record | Algorithm result | Annotated / ignored frames | S1 onset F1 @100 ms | S2 onset F1 @100 ms |
|---|---|---:|---:|---:|
| C1 | SUCCESS | 423 / 171 | 0.9630 | 1.0000 |
| C2 | SUCCESS | 403 / 727 | 0.9697 | 1.0000 |
| C3 | SUCCESS | 1317 / 105 | 0.9275 | 0.9577 |
| C4 | HEART_RATE_ESTIMATION_FAILED | 153 / 1439 | 0.0000 | 0.0000 |

C1/C2/C3 annotated-frame agreement: 0.8676 / 0.9007 / 0.8914. **C4 failed heart-rate estimation**; no events were produced, each class had five false negatives and F1=0. It is retained in the denominator. P1 had no expert reference acquired in this task and was not reference-scored. These exploratory results are separate from mandatory spectrogram/metadata acceptance and do not authorize diagnosis.

## Commands, failures and archived evidence

Exact command arrays/cwd/UTC bounds/exit codes are in the machine summary and local per-command JSON/TXT. Main checks from repo root (frontend commands from `software/frontend`):

```text
.venv\Scripts\python.exe -B -m pytest software/tests/test_real_pcg_acceptance.py -q --junitxml=experiments/output/week6_real_pcg_20261026/real-backend-v2.xml
  AUSCULTA_PCG_MANIFEST=data/raw/week6_real_pcg_20261026/manifest.json
  AUSCULTA_PCG_EVIDENCE=experiments/output/week6_real_pcg_20261026/backend-v2
.venv\Scripts\python.exe -B -m pytest software/tests -q --junitxml=experiments/output/week6_real_pcg_20261026/final-python-v2.xml
npm.cmd run lint && npm.cmd test && npm.cmd run build
.venv\Scripts\python.exe -B experiments/output/week6_real_pcg_20261026/research_check.py
.venv\Scripts\python.exe -B experiments/output/week6_real_pcg_20261026/verify_gui_recording.py
```

| Run manifest | Actual UTC bounds | Exit |
|---|---|---:|
| frontend-import-red | 2026-10-26T08:59:40.941591+00:00 → 2026-10-26T08:59:41.902115+00:00 | 1 |
| frontend-import-final | 2026-10-26T09:26:36.965804+00:00 → 2026-10-26T09:26:37.247375+00:00 | 0 |
| real-pcg-backend | 2026-10-26T09:19:53.354266+00:00 → 2026-10-26T09:20:04.114286+00:00 | 1 |
| real-pcg-backend-v2 | 2026-10-26T09:23:23.261286+00:00 → 2026-10-26T09:23:33.742529+00:00 | 0 |
| research-s1s2 | 2026-10-26T09:31:56.225560+00:00 → 2026-10-26T09:31:58.573383+00:00 | 0 |
| gui-recording-check | 2026-10-26T09:38:52.186804+00:00 → 2026-10-26T09:38:54.980264+00:00 | 0 |
| final-frontend | 2026-10-26T09:37:36.812994+00:00 → 2026-10-26T09:37:56.399194+00:00 | 0 |
| final-python | 2026-10-26T09:37:26.683935+00:00 → 2026-10-26T09:39:50.929015+00:00 | 1 |
| final-python-v2 | 2026-10-26T09:40:02.627267+00:00 → 2026-10-26T09:41:02.519951+00:00 | 0 |

Final outcomes: **Python 562 passed / 1 intentional real-data-placeholder skip / 2 warnings; real-manifest run 7 passed / 1 warning; frontend typecheck, six tsx programs and production build exit 0**. The real records are not skipped in the separately executed manifest run. Warnings: Starlette/httpx and TorchScript deprecations, existing frontend >500 kB chunk notice.

Preserved failed attempts: frontend source import reported device 48 kHz before fix; backend 2 kHz selection incorrectly reported 4 kHz before fix; initial real-data test used an overly strict zero boundary (6 pass/1 fail); first broad suite had `qualify --help` subprocess timeout at 10 s (561 pass/1 fail/1 skip). After task-owned GUI servers were stopped, the full suite passed without changing that CLI or its timeout. Load sensitivity remains possible; one rerun is not proof it cannot recur. The 4 kHz baseline probe happened to pass despite a filename ending `red`. No physical test retries occurred.

Local evidence root: `experiments/output/week6_real_pcg_20261026`. Includes five per-record backend result/session directories, original unsuccessful attempts, GUI file/FFT/seek/filter/source-switch snapshots, GUI start/stop/replay evidence, manifests, research harness/results, stdout and JUnit. SHA-256 inventory is committed; raw artifacts remain ignored. Existing physical evidence is untouched.

## Remaining Module C limitations

- Local audition still lacks backend Welch history/session recording; use supported backend WAV/session replay. This is a known feature gap, not a GUI PASS for local spectrograms.
- Local audition preview and backend/browser filter presets are not equivalent; numerical browser filter-response validation remains open.
- Continuous replay wraps at EOF and can display FILE PLAYBACK DEGRADED because pipeline sequence/time state spans the rewind; display history resets on rewind. Bounded one-pass integrity passed; looped-session health is not accepted.
- Backend replay runtime reflects the rolling/current stream rather than a full-file seekable archive. Decorative overview ID `L-44100-RAW` remains stale even when actual fs labels correctly show 2/4 kHz. Do not interpret that ID as source metadata.
- GUI malformed-file recovery, exact-N visual display and a native packaged acceptance run of this implementation were not executed. Numeric N and malformed-parser rejection were tested separately.
- C4 S1/S2 inference failure remains open; the small exploratory sample is not a validated clinical benchmark.
- Physical G2, acoustic calibration, installed-version acceptance and Module A/B measurements remain outside this software acceptance. Earlier G1 results retain their original revisions/dates.
