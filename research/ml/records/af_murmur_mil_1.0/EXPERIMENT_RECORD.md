# AUSCULTAFORGE RESEARCH EXPERIMENT RECORD
## Model Identifier: `af_murmur_mil_1.0`
### CirCor Patient-Level Multi-Instance Murmur Acoustic Pattern Classifier (v1.0)

**Record Status:** PERMANENT & IMMUTABLE (Frozen Run)  
**Date of Training Completion:** October 2026  
**Training Environment:** Google Colab GPU (Tesla T4)  
**Execution Script:** `research/ml/ausculta_ml/train.py`  
**Configuration Reference:** `research/ml/configs/circor_mil_v1.yaml` (SHA-256: `a764ed5583c240c92cdf0c4e23d1bbe03c66f9ae438312ba5c462189373fb78d`)

---

## 1. RESEARCH & ETHICAL BOUNDARIES (STRICTLY NON-CLINICAL)

> [!CAUTION]
> **RESEARCH USE ONLY — NOT A CLINICAL DIAGNOSTIC DEVICE**
> - AuscultaForge is an engineering acoustic research platform.
> - The output of `af_murmur_mil_1.0` is an acoustic research probability score, **never a medical diagnosis**.
> - It must **never** be used to inform patient triage, clinical diagnosis, or treatment decisions.
> - Murmur detection is **not** an arrhythmia detector and does not predict coronary artery disease, heart failure, or acute myocardial infarction.
> - Model predictions are **unvalidated** for domain transfer to physical stethoscope sensors (e.g. ESP32-S3 / INMP441) and must be explicitly opt-in with displayed caveats.

---

## 2. DATASET ATTRIBUTION & SOURCE PROVENANCE

### 2.1 Primary Corpus
- **Dataset:** The CirCor DigiScope Phonocardiogram Dataset (v1.0.3, PhysioNet)
- **License:** Open Data Commons Attribution License v1.0 (ODC-By v1.0)
- **PhysioNet Link:** [PhysioNet CirCor Heart Sound 1.0.3](https://physionet.org/content/circor-heart-sound/1.0.3/)
- **Academic Citation:**
  > Oliveira, J., Renna, F., Mosquera, V., et al. (2021). The CirCor DigiScope Phonocardiogram Dataset. *IEEE Journal of Biomedical and Health Informatics*, 26(6), 2529-2537. DOI: [10.1109/JBHI.2021.3137048](https://doi.org/10.1109/JBHI.2021.3137048).
  > Goldberger, A., Amaral, L., Glass, L., et al. (2000). PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. *Circulation*, 101(23), e215-e220.

### 2.2 Data Integrity Checksums
- `training_data.csv` SHA-256: `ed10e63a2079639d475f72473d0ca1cee49fa82ea7c23fff9c6c6e8b0621d205`
- Split Manifest SHA-256: `db60aa8b0a4d6be3179849b64b50951c26dca698c1cfbcd23f1dfc667b8db2c3`

---

## 3. EXPERIMENTAL SPLIT ARCHITECTURE (LEAKAGE-SAFE)

The evaluation unit is the **individual patient**, not individual recordings. A single subject often has recordings from multiple auscultation sites (Aortic Valve `AV`, Pulmonic Valve `PV`, Tricuspid Valve `TV`, Mitral Valve `MV`). Cross-campaign duplicate subjects are linked via `Additional ID` to prevent data leakage across splits.

- **Total Analyzed Patient Cohort:** 874 patients with verified Present/Absent murmur annotations (Unknown cases excluded from binary formulation).
- **Group Disjoint Partitioning:**
  - **Training Set:** 610 patients (130 positive / Present, 480 negative / Absent)
  - **Validation Set:** 132 patients (25 positive / Present, 107 negative / Absent)
  - **Internal Held-Out Test Set:** 132 patients (24 positive / Present, 108 negative / Absent)

---

## 4. MODEL ARCHITECTURE & PREPROCESSING SPECIFICATION

- **Model Type:** Multi-Instance Attention Convolutional Neural Network (`MurmurMIL`)
- **Acoustic Preprocessing:**
  - Native resample rate: $2,000\text{ Hz}$ with anti-aliasing filter
  - STFT Window / FFT size: $N_{\text{fft}} = 512$ ($256\text{ ms}$)
  - STFT Hop length: $H = 128$ ($64\text{ ms}$, 75% overlap)
  - Frequency bandpass: $15\text{ Hz} - 650\text{ Hz}$ ($96$ mel/linear frequency bins)
  - Temporal crop: $5.0\text{ seconds}$ ($78$ time frames)
  - Maximum instances per bag: $M = 4$ locations
- **Encoder:** 4-stage residual-style convolutional stack (16, 32, 64, 96 channels) with SiLU activations, batch normalization, and adaptive average pooling.
- **Pooling Mechanism:** Gated multi-instance attention pooling across available recording sites.
- **Inference Temporal Ensembling:** 3 deterministic temporal offsets (0.0, 0.5, 1.0) averaged in logit space.

---

## 5. EMPIRICAL VALIDATION & TEST MEASUREMENTS

### 5.1 Training Convergence
- **Best Epoch:** Epoch 6 (early stopping patience 9, min delta 0.0001)
- **Validation-Selected Optimal Threshold:** $\tau^* = 0.52$ (chosen purely on validation F1/balanced accuracy, never on test data)

### 5.2 Internal Held-Out Test Set Evaluation (Unseen 132 Patients)
- **AUROC (Area Under ROC Curve):** $0.8734567901234568$ ($\approx 0.8735$)
- **Average Precision (PR-AUC):** $0.7610817398389247$ ($\approx 0.7611$)
- **F1 Score (@ $\tau^* = 0.52$):** $0.5714285714285714$ ($\approx 0.5714$)
- **Balanced Accuracy:** $0.7777777777777778$ ($\approx 0.7778$)
- **Confusion Matrix:**
  - True Negatives (TN): $87$
  - False Positives (FP): $21$
  - False Negatives (FN): $6$
  - True Positives (TP): $18$
- **Sensitivity (Recall on Murmur):** $\frac{18}{18 + 6} = 75.0\%$
- **Specificity:** $\frac{87}{87 + 21} = 80.56\%$

### 5.3 Validation Set Benchmark
- **AUROC:** $0.794392523364486$ ($\approx 0.7944$)
- **Average Precision:** $0.6780892511833392$ ($\approx 0.6781$)
- **F1 Score:** $0.6037735849056604$ ($\approx 0.6038$)
- **Confusion Matrix (TN/FP/FN/TP):** $95 / 12 / 9 / 16$

> [!NOTE]
> AUROC measures discriminative ranking capability across all thresholds, not classification accuracy. The operating point at $\tau = 0.52$ yields $75.0\%$ sensitivity and $80.56\%$ specificity on the internal held-out test cohort.

---

## 6. ARTIFACTS & INTEGRITY VERIFICATION

| Artifact Name | Format | Size | SHA-256 Checksum | Git Status |
| :--- | :--- | :--- | :--- | :--- |
| `murmur_mil_cpu.pt` | TorchScript (CPU) | 1,034,108 bytes | `60ee906eb204c5c5bc94d0285e0f6b25f7d2c9532b6394939d902813a86a49e0` | Local / Release Asset |
| `weights.pt` | PyTorch `state_dict` | 951,023 bytes | `63728ddc49dc24399fc4c523ced67d3cf7aeb8046bca8a742a68f64609256280` | Local / Release Asset |
| `manifest.json` | JSON Specification | 944 bytes | `efb961e529cba6df4825860d8e375ac3d0c49569cdc699e1f246c4aee602e1ea` | Committed to Git |
| `metrics.json` | JSON Metrics | 1,589 bytes | `7c788a5fef982eead586e3de44c16c2216481b45eb94100becccfadf8c245a30` | Committed to Git |
| `model_card.md` | Markdown Card | 425 bytes | `4ff6a4df9c686de9c243f6de28b615bb2d4105f675c8d4fa6be2904e5aa3669c` | Committed to Git |
| `training_config.yaml` | YAML Config | 422 bytes | `a764ed5583c240c92cdf0c4e23d1bbe03c66f9ae438312ba5c462189373fb78d` | Committed to Git |
| `AuscultaForge_MurmurMIL_v1.0.zip` | Archive | 1,939,531 bytes | `997947a00d0d525c1fde344f925edfd78206c69f8f316e48b82bacdef98a62b2` | Release Bundle |

---

## 7. KNOWN LIMITATIONS & UNVALIDATED DOMAINS

1. **Pediatric Bias:** The CirCor cohort consists predominantly of pediatric and adolescent subjects; acoustic murmurs and chest cavity resonances in adult or geriatric populations may differ substantially.
2. **Hardware Domain Shift:** CirCor was collected using clinical electronic stethoscopes (DigiScope platform). Transferability to INMP441 MEMS / ECM transducers operating through acoustic 3D-printed bell cavities is currently **untested**.
3. **Internal vs External Validation:** The held-out test set is from the same multi-center CirCor campaign. True independent validation on hospital or phantom benchmarks has not yet been executed.
4. **Binary Target:** Does not discriminate murmur etiology (e.g. aortic stenosis vs mitral regurgitation vs innocent flow murmur).
