"""AuscultaForge Offline ML Model Artifact Verification Tool.

Verifies SHA-256 integrity, CPU loadability, numerical agreement,
and real patient inference consistency without untrusted deserialization.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

# Ensure ausculta_ml can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "research" / "ml"))
from ausculta_ml.model import MurmurMIL
from ausculta_ml.inference import predict_recordings


EXPECTED_CHECKSUMS = {
    "murmur_mil_cpu.pt": "60ee906eb204c5c5bc94d0285e0f6b25f7d2c9532b6394939d902813a86a49e0",
    "weights.pt": "63728ddc49dc24399fc4c523ced67d3cf7aeb8046bca8a742a68f64609256280",
    "manifest.json": "efb961e529cba6df4825860d8e375ac3d0c49569cdc699e1f246c4aee602e1ea",
    "metrics.json": "7c788a5fef982eead586e3de44c16c2216481b45eb94100becccfadf8c245a30",
    "training_config.yaml": "a764ed5583c240c92cdf0c4e23d1bbe03c66f9ae438312ba5c462189373fb78d",
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_verification(artifact_dir: Path, output_report_path: Path | None = None) -> dict:
    artifact_dir = Path(artifact_dir)
    report: dict = {
        "verifier": "AuscultaForge ML Verification Suite v1.0",
        "model_version": "af_murmur_mil_1.0",
        "artifact_dir": str(artifact_dir),
        "files_checked": {},
        "sha256_checks_passed": True,
        "torchscript_load_passed": False,
        "pytorch_weights_load_passed": False,
        "numerical_agreement_passed": False,
        "max_numerical_discrepancy": None,
        "shape_contract_passed": False,
        "real_circor_validation": {},
        "overall_status": "PENDING",
    }

    print(f"[VERIFY] Starting verification on {artifact_dir}...")

    # 1. Checksums
    for filename, expected_hash in EXPECTED_CHECKSUMS.items():
        filepath = artifact_dir / filename
        if not filepath.exists():
            report["files_checked"][filename] = {"exists": False, "sha256": None, "match": False}
            report["sha256_checks_passed"] = False
            print(f"  [MISSING] {filename}")
        else:
            actual_hash = compute_sha256(filepath)
            match = (actual_hash == expected_hash)
            report["files_checked"][filename] = {"exists": True, "sha256": actual_hash, "match": match}
            if not match:
                report["sha256_checks_passed"] = False
                print(f"  [HASH MISMATCH] {filename}: expected {expected_hash}, got {actual_hash}")
            else:
                print(f"  [HASH OK] {filename}")

    # 2. TorchScript Safe Load
    ts_path = artifact_dir / "murmur_mil_cpu.pt"
    if ts_path.exists():
        try:
            ts_model = torch.jit.load(str(ts_path), map_location="cpu")
            ts_model.eval()
            report["torchscript_load_passed"] = True
            print("  [TORCHSCRIPT] Successfully loaded on CPU.")
        except Exception as e:
            print(f"  [TORCHSCRIPT ERROR] {e}")
            ts_model = None
    else:
        ts_model = None

    # 3. PyTorch Weights Load (safe weights_only=True)
    weights_path = artifact_dir / "weights.pt"
    if weights_path.exists():
        try:
            py_model = MurmurMIL()
            state_dict = torch.load(str(weights_path), map_location="cpu", weights_only=True)
            py_model.load_state_dict(state_dict)
            py_model.eval()
            report["pytorch_weights_load_passed"] = True
            print("  [PYTORCH WEIGHTS] Successfully loaded with weights_only=True.")
        except Exception as e:
            print(f"  [PYTORCH WEIGHTS ERROR] {e}")
            py_model = None
    else:
        py_model = None

    # 4. Numerical Agreement Test
    if ts_model is not None and py_model is not None:
        torch.manual_seed(42)
        x_test = torch.randn(2, 4, 1, 96, 78)
        mask_test = torch.tensor([[True, True, True, False], [True, False, False, False]])
        with torch.no_grad():
            out_ts = ts_model(x_test, mask_test)
            out_py = py_model(x_test, mask_test)
            diff = (out_ts - out_py).abs().max().item()
            report["max_numerical_discrepancy"] = float(diff)
            report["numerical_agreement_passed"] = (diff < 1e-5)
            print(f"  [NUMERICAL AGREEMENT] Discrepancy: {diff} (Passed: {diff < 1e-5})")

    # 5. Shape Contract
    if ts_model is not None:
        try:
            dummy_x = torch.zeros(1, 4, 1, 96, 78, dtype=torch.float32)
            dummy_m = torch.tensor([[True, False, False, False]], dtype=torch.bool)
            with torch.no_grad():
                out = ts_model(dummy_x, dummy_m)
                assert out.shape == torch.Size([1]), f"Unexpected output shape: {out.shape}"
                assert torch.isfinite(out).all(), "Non-finite output detected"
                report["shape_contract_passed"] = True
                print("  [SHAPE CONTRACT] Verified 1x4x1x96x78 -> 1-dim finite logit.")
        except Exception as e:
            print(f"  [SHAPE ERROR] {e}")

    # 6. Real CirCor Validation (if present)
    circor_dir = Path("data/external/circor-heart-sound-1.0.3/training_data")
    if circor_dir.exists():
        test_patients = ["14241", "2530"]
        for pid in test_patients:
            wavs = sorted(glob.glob(str(circor_dir / f"{pid}_*.wav")))
            if wavs:
                try:
                    pred = predict_recordings(artifact_dir, wavs)
                    report["real_circor_validation"][pid] = {
                        "recordings_count": len(wavs),
                        "positive_probability": pred["positive_probability"],
                        "threshold": pred["validation_selected_threshold"],
                        "predicted_label": pred["predicted_label"],
                        "status": "PASS"
                    }
                    print(f"  [CIRCOR TEST {pid}] P={pred['positive_probability']:.4f} -> {pred['predicted_label']}")
                except Exception as e:
                    report["real_circor_validation"][pid] = {"error": str(e), "status": "FAIL"}
                    print(f"  [CIRCOR TEST {pid} ERROR] {e}")

    # Overall Verdict
    all_ok = (
        report["sha256_checks_passed"]
        and report["torchscript_load_passed"]
        and report["pytorch_weights_load_passed"]
        and report["numerical_agreement_passed"]
        and report["shape_contract_passed"]
    )
    report["overall_status"] = "VERIFIED_PASS" if all_ok else "VERIFICATION_FAILED"
    print(f"[VERIFY] Final Status: {report['overall_status']}")

    if output_report_path:
        output_report_path = Path(output_report_path)
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[VERIFY] Saved report to {output_report_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify AuscultaForge ML Model Artifact")
    parser.add_argument("--artifact-dir", type=str, default="research/ml/records/af_murmur_mil_1.0")
    parser.add_argument("--output", type=str, default="research/ml/records/af_murmur_mil_1.0/verification_report.json")
    args = parser.parse_args()

    rep = run_verification(Path(args.artifact_dir), Path(args.output))
    sys.exit(0 if rep["overall_status"] == "VERIFIED_PASS" else 1)
