"""AuscultaForge Research ML Model Installer.

Unpacks and verifies the versioned AuscultaForge_MurmurMIL_v1.0.zip artifact into
the local ignored artifact directory (research/ml/artifacts/circor_mil_v1/).
Prevents checking binary weights into Git history while enabling instant desktop use.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

EXPECTED_ZIP_SHA256 = "997947a00d0d525c1fde344f925edfd78206c69f8f316e48b82bacdef98a62b2"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def install_model(archive_path: Path, dest_dir: Path | None = None) -> bool:
    repo_root = Path(__file__).parent.parent
    if dest_dir is None:
        dest_dir = repo_root / "research" / "ml" / "artifacts" / "circor_mil_v1"

    archive_path = Path(archive_path)
    if not archive_path.is_file():
        print(f"[ERROR] Model artifact archive not found: {archive_path}")
        return False

    print(f"[INSTALL] Verifying archive integrity: {archive_path.name}...")
    actual_sha = compute_sha256(archive_path)
    print(f"  Archive SHA-256: {actual_sha}")

    if actual_sha != EXPECTED_ZIP_SHA256:
        print(f"[ERROR] SHA-256 mismatch! Archive integrity verification failed.")
        print(f"  Expected: {EXPECTED_ZIP_SHA256}")
        print(f"  Observed: {actual_sha}")
        print("[ABORT] Installation cancelled (fail-closed, no bypass permitted).")
        return False

    print("  [INTEGRITY OK] SHA-256 verified against official release specification.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INSTALL] Extracting to {dest_dir}...")

    with zipfile.ZipFile(archive_path, "r") as z:
        # Zip-slip guard
        for name in z.namelist():
            resolved = (dest_dir / name).resolve()
            if not str(resolved).startswith(str(dest_dir.resolve())):
                raise RuntimeError(f"Unsafe zip entry path detected (zip-slip attempt): {name}")
        z.extractall(dest_dir)

    print(f"[INSTALL] Unpacked files to {dest_dir}. Verifying required artifact files and hashes...")

    # Post-extraction artifact integrity check
    required_checksums = {
        "murmur_mil_cpu.pt": "60ee906eb204c5c5bc94d0285e0f6b25f7d2c9532b6394939d902813a86a49e0",
        "weights.pt": "63728ddc49dc24399fc4c523ced67d3cf7aeb8046bca8a742a68f64609256280",
        "manifest.json": "efb961e529cba6df4825860d8e375ac3d0c49569cdc699e1f246c4aee602e1ea",
        "metrics.json": "7c788a5fef982eead586e3de44c16c2216481b45eb94100becccfadf8c245a30",
        "training_config.yaml": "a764ed5583c240c92cdf0c4e23d1bbe03c66f9ae438312ba5c462189373fb78d",
    }
    for filename, expected_hash in required_checksums.items():
        extracted_file = dest_dir / filename
        if not extracted_file.is_file():
            print(f"[ERROR] Required artifact file missing after extraction: {filename}")
            return False
        file_sha = compute_sha256(extracted_file)
        if file_sha != expected_hash:
            print(f"[ERROR] Checksum mismatch for extracted file {filename}!")
            print(f"  Expected: {expected_hash}")
            print(f"  Observed: {file_sha}")
            return False

    print("[INSTALL] All artifact files and SHA-256 hashes successfully verified.")

    # Verify installation with verification script if available
    verify_script = repo_root / "tools" / "verify_ml_model.py"
    if verify_script.exists():
        print("[INSTALL] Running offline verification suite...")
        import subprocess
        res = subprocess.run([
            sys.executable,
            str(verify_script),
            "--artifact-dir", str(dest_dir),
        ])
        return res.returncode == 0

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install AuscultaForge MurmurMIL Model Artifact")
    parser.add_argument(
        "--archive",
        type=str,
        default="c:\\Dev\\Antigravity\\bitirme\\AuscultaForge_MurmurMIL_v1.0.zip",
        help="Path to AuscultaForge_MurmurMIL_v1.0.zip",
    )
    parser.add_argument(
        "--dest",
        type=str,
        default=None,
        help="Target installation directory",
    )
    args = parser.parse_args()

    success = install_model(Path(args.archive), Path(args.dest) if args.dest else None)
    sys.exit(0 if success else 1)
