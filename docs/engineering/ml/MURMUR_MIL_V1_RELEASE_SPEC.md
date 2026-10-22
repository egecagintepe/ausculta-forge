# AUSCULTAFORGE — MURMUR_MIL V1.0 MODEL RELEASE SPECIFICATION
## Versioned GitHub Release Workflow & Artifact Management

**Model ID:** `af_murmur_mil_1.0`  
**Task:** Patient-Level Murmur Present vs Absent Research Classifier  
**Status:** Software Verified · Local Offline CPU Inference Ready  
**Associated Git Commit on `main`:** Current HEAD  
**Release Asset Filename:** `AuscultaForge_MurmurMIL_v1.0.zip`  
**Release Asset SHA-256:** `997947a00d0d525c1fde344f925edfd78206c69f8f316e48b82bacdef98a62b2`

---

## 1. RELEASE ASSET PACKAGING

Binary weight files (`*.pt`, `*.onnx`) are deliberately excluded from regular Git repository commits to keep Git history lightweight and prevent repository bloat. Model binaries are distributed as a versioned GitHub Release Asset:

### 1.1 Archive Structure & Checksums
Inside `AuscultaForge_MurmurMIL_v1.0.zip`:

| File | Size | SHA-256 Checksum | Description |
| :--- | :--- | :--- | :--- |
| `murmur_mil_cpu.pt` | 1,034,108 B | `60ee906eb204c5c5bc94d0285e0f6b25f7d2c9532b6394939d902813a86a49e0` | TorchScript CPU deployment model |
| `weights.pt` | 951,023 B | `63728ddc49dc24399fc4c523ced67d3cf7aeb8046bca8a742a68f64609256280` | PyTorch `state_dict` weights |
| `manifest.json` | 944 B | `efb961e529cba6df4825860d8e375ac3d0c49569cdc699e1f246c4aee602e1ea` | Formal model specification contract |
| `metrics.json` | 1,589 B | `7c788a5fef982eead586e3de44c16c2216481b45eb94100becccfadf8c245a30` | Validated test and validation metrics |
| `model_card.md` | 425 B | `4ff6a4df9c686de9c243f6de28b615bb2d4105f675c8d4fa6be2904e5aa3669c` | Model card summary |
| `training_config.yaml` | 422 B | `a764ed5583c240c92cdf0c4e23d1bbe03c66f9ae438312ba5c462189373fb78d` | Pinned training hyperparameters |

---

## 2. TEAM INSTALLATION INSTRUCTIONS (NO RETRAINING REQUIRED)

Any team member (Ozan, Ege, Kaan) can install and activate the trained model locally without running training in Colab:

### Automated Installation via Python:
```bash
# Run installer pointing to the provided zip artifact
python scripts/install_research_model.py --archive path/to/AuscultaForge_MurmurMIL_v1.0.zip
```

The script automatically:
1. Verifies the SHA-256 digest against `997947a00d0d525c1fde344f925edfd78206c69f8f316e48b82bacdef98a62b2`.
2. Extracts the files into the local Git-ignored directory:
   `research/ml/artifacts/circor_mil_v1/`
3. Runs `tools/verify_ml_model.py` to test CPU execution, numerical agreement, and CirCor test cases.

### Manual Installation:
1. Extract `AuscultaForge_MurmurMIL_v1.0.zip` directly into:
   `research/ml/artifacts/circor_mil_v1/`
2. Run offline verification:
   ```bash
   python tools/verify_ml_model.py --artifact-dir research/ml/artifacts/circor_mil_v1
   ```
3. Launch AuscultaForge Desktop and navigate to **AI Research Lab** in the navigation bar.

---

## 3. SUMMARY OF REAL COLAB TRAINING RESULTS

- **Trained Model Architecture:** `MurmurMIL` (Multi-Instance Attention CNN)
- **Dataset:** CirCor 1.0.3 Public Training Subset (610 train / 132 val / 132 test subjects)
- **Best Epoch:** Epoch 6
- **Operating Threshold:** $\tau^* = 0.52$
- **Held-Out Test Results (Unseen 132 Patients):**
  - AUROC: `0.8735`
  - Average Precision: `0.7611`
  - F1 Score: `0.5714`
  - Balanced Accuracy: `0.7778`
  - Confusion Matrix (TN/FP/FN/TP): `87 / 21 / 6 / 18`
  - Sensitivity: `75.0%`
  - Specificity: `80.56%`

---

## 4. STRICT NON-CLINICAL DISCLAIMER & DOMAIN BOUNDARIES

1. **Non-Clinical Research Purpose:**
   This model is intended solely for academic research and engineering acoustic investigation. It is **not** a clinical diagnostic tool and must not be used for medical decisions, cardiac risk stratification, or clinical triage.
2. **Pediatric Bias:**
   Trained on CirCor data representing pediatric and adolescent populations. Extrapolation to adults is unvalidated.
3. **Hardware Domain Shift:**
   Trained on electronic stethoscopes. Direct evaluation on AuscultaForge ESP32-S3 / INMP441 MEMS microphone hardware is currently **unvalidated** and requires paired acoustic transfer studies.
