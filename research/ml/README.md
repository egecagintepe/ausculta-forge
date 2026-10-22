# AuscultaForge ML Research Lab — v0.1

**Permanent project component, not a throwaway demo.** This module will eventually host multiple independently versioned research models (murmur acoustic patterns, quality/artefact classification, segmentation, denoising, domain adaptation, safe filter recommendation). First fully specified trainable model: **CirCor patient-level murmur research MIL** with learned attention across auscultation recordings. This is NOT an arrhythmia or disease diagnostic model.

## Boundaries

- Parent project remains a nonclinical engineering-acoustic research platform. Clinical diagnostic AI is out of assessed course scope; advisor signoff required before course claims, public demos with diagnostic implications, or extending to real patient collection.
- No silent disease predictions in the Desktop UI; inference returns `research_only` and warnings.
- Training uses publicly released **CirCor v1.0.3** data (Open Data Commons Attribution v1.0). Source: https://physionet.org/content/circor-heart-sound/1.0.3/ and paper DOI `10.1109/JBHI.2021.3137048`. Respect data and model licenses. Do not commit WAV recordings or private experiment data.
- **Patient-level murmur label**; model combines recordings within an individual. Present/Absent only; Unknown is excluded, never relabeled negative. Do not interpret one recording's label as a confirmed local murmur event.
- `Additional ID` is used to link same-subject recordings across campaigns before freezing independent splits. Training, validation and test belong to disjoint linked individuals. Internal held-out test is a split **within the publicly released subset**, not clinical/external validation.
- A person may have several recording locations. Max 4 included per training example (sorted deterministic or randomly subsampled). Validation/test aggregate three consistent windows (start, middle, end) as logit ensemble. Label relates to the whole person.
- Original recordings remain unchanged; spectrograms are derived at 2 kHz with anti-aliasing.
- No claim that data from clinical electronic stethoscopes transfers to physical INMP441/ECM phantom: sensor domain shift remains unvalidated.

## Repo layout

`research/ml/` is the intended destination inside `egecagintepe/ausculta-forge` on main. It does not edit `firmware/` or production DeviceRuntime.

- `notebooks/AuscultaForge_CirCor_MIL_Colab.ipynb`: Google Colab orchestration (free GPU if available)
- `configs/circor_mil_v1.yaml`: pinned experiment settings
- `ausculta_ml/data.py`: CirCor ingestion, linked-subject splits, STFT cache
- `ausculta_ml/model.py`: patient-level multi-instance attention CNN
- `ausculta_ml/train.py`: training, validation-only threshold selection, checkpoint/resume, heldout evaluation
- `ausculta_ml/export.py`: TorchScript CPU deployment contract
- `ausculta_ml/inference.py`: versioned CPU offline research interface
- `ausculta_ml/filter_advisor.py`: safe deterministic filter *recommendations* and non-destructive previews (not trained noise classifier yet)
- `tests/`: invariants including anti-leakage and immutability

## Colab: first actual training

1. Open the supplied `.ipynb` in Colab via **File → Upload notebook**. GPU runtime recommended (Runtime → Change runtime type → T4 GPU if available).
2. Execute the first code cell; it prompts you to upload **AuscultaForge_ML_RepoDrop.zip**. It unpacks this exact package into `/content/ausculta_lab/`.
3. Mount Google Drive, grant access. It will save `runs/circor_mil_v1/` outputs including checkpoints after **every epoch**. Don't put raw data in GitHub.
4. Download the real CirCor v1.0.3 publicly released dataset using documented PhysioNet S3 public mirror (about 559MB uncompressed); there can be network and quota limits.
5. Precompute spectrogram cache (once per runtime). Run the *real full-dataset* training, not a synthetic sample test.
6. Inspect `metrics.json`, `history.jsonl`, split manifest and model card. Only then export CPU model and check offline inference. Do not use the held-out test during development or hyperparameter selection.
7. To resume, restart Colab, restore the exact training config, linked patient split manifest and checkpoint in Drive, redownload or restore raw data/cache, and run training with `--resume`.

## Command line (Python venv with dependencies)

```bash
cd research/ml
pip install -r requirements.txt
python -m ausculta_ml.train --config configs/circor_mil_v1.yaml \
  --raw /content/ausculta_lab/data/raw/circor/1.0.3 \
  --work /content/ausculta_lab/work/circor \
  --run /content/drive/MyDrive/AuscultaForge_ML/runs/circor_mil_v1
python -m ausculta_ml.export \
  --run /content/drive/MyDrive/AuscultaForge_ML/runs/circor_mil_v1 \
  --out /content/drive/MyDrive/AuscultaForge_ML/artifacts/circor_mil_v1
python -m pytest tests -q
```

## Durable upgrade strategy

Add a new versioned task under `ausculta_ml/` (e.g. `noise_v1`, `denoiser_v1`, `segmentation_v1`) without replacing the dataset registry, split manifest, training metadata, serialization policy or offline inference API. **A future noise classifier must use genuine artefact labels or explicitly simulated corruption classes**; CirCor's present/absent murmur labels are NOT noise classes. Filter advisor remains rule-based until validated ML evidence exists. The final deployment to Device UI is a separate gated task, only with advisor approval and independent data validation.

## Known limitations / work remaining

- This is an **initial, substantive research model** with checkpointed patient-level training, not a complete pre-trained model, not all ML capabilities promised as done.
- Splits contain a single publicly released corpus; independent dataset validation is still required.
- No true calibrated sound-pressure measurements, phantom data, or physical G1 results.
- No benchmark numbers are supplied in advance; results come only from actual Colab run.
- Google Colab free resources and runtime duration are not guaranteed; checkpoint each epoch.
- Future work: external test, baseline model, confidence intervals, calibration, site-specific murmur labels, QC/artefact labels, distortion-aware learned denoising, ONNX parity, desktop rollout and CI.
