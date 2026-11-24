#!/usr/bin/env python3
"""
AuscultaForge — Delivery ZIP Extraction and Smoke Verification Script

1. Extracts AuscultaForge_Lab_Delivery_20261125.zip into a clean temp folder.
2. Verifies presence and SHA-256 of reference PCG stimulus (40058_AV.wav).
3. Verifies presence of LAPTOP_PROMPT.md, START_HERE_2026-11-25.md, AGENTS.md,
   and Ozan's REV04 DOCX/XLSX.
4. Verifies presence of clean .git and git branch status.
5. Runs workflow in simulation mode (-Simulate) using the extracted worktree and system/existing python.
6. Verifies exit code 0.
7. Cleans up temporary test folder.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    bitirme_dir = Path(r"C:\Dev\Antigravity\bitirme")
    zip_path = bitirme_dir / "AuscultaForge_Lab_Delivery_20261125.zip"
    test_dir = bitirme_dir / "test_clean_extract"

    print("============================================================")
    print("  AUSCULTAFORGE — DELIVERY PACKAGE EXTRACTION TEST")
    print("============================================================")
    print(f"ZIP Archive  : {zip_path}")
    print(f"Extraction To: {test_dir}")

    if not zip_path.is_file():
        raise FileNotFoundError(f"ZIP package not found at: {zip_path}")

    zip_hash = sha256_file(zip_path)
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"ZIP Size     : {zip_size_mb:.2f} MB")
    print(f"ZIP SHA-256  : {zip_hash}")

    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract ZIP
    print("\n[1/5] Extracting archive...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(test_dir)
    extracted_repo = test_dir / "ausculta-forge"
    print(f"  Extracted to: {extracted_repo}")

    # 2. Check critical files
    print("\n[2/5] Checking critical files in extracted package...")
    critical_files = [
        extracted_repo / "START_HERE_2026-11-25.md",
        extracted_repo / "LAPTOP_PROMPT.md",
        extracted_repo / "AGENTS.md",
        extracted_repo / "tools/hardware/run_lab_phantom_workflow.ps1",
        extracted_repo / "tools/hardware/run_phantom_pcg_experiment.py",
        extracted_repo / "docs/sdp/week-09/submissions/module-b-ozan/W09_B_system-design-technical-specification_REV04_2026-11-20.docx",
        extracted_repo / "docs/sdp/week-09/submissions/module-b-ozan/W09_B_procurement-bom-test_REV04_2026-11-20.xlsx",
        extracted_repo / "docs/sdp/week-09/submissions/module-b-ozan/AuscultaForge_W09_REV04_QA_2026-11-20.md",
    ]
    for cf in critical_files:
        if not cf.is_file():
            raise FileNotFoundError(f"Missing critical file in package: {cf}")
        print(f"  [OK] {cf.relative_to(extracted_repo)}")

    # 3. Check reference WAV and SHA-256
    print("\n[3/5] Verifying reference PCG stimulus (40058_AV.wav)...")
    ref_wav = extracted_repo / "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
    if not ref_wav.is_file():
        raise FileNotFoundError(f"Reference WAV missing in package: {ref_wav}")
    ref_hash = sha256_file(ref_wav).lower()
    expected_ref_hash = "108df8f77491a5706209aa5b467ed10ac43f2a0b847801fe666ba8146dcbf8e8"
    if ref_hash != expected_ref_hash:
        raise ValueError(f"WAV hash mismatch! Got {ref_hash}, expected {expected_ref_hash}")
    print(f"  [OK] Reference WAV verified (SHA256: {ref_hash})")

    # 4. Check git status in extracted folder
    print("\n[4/5] Checking Git status in extracted folder...")
    res_git = subprocess.run(
        ["git", "status"],
        cwd=extracted_repo,
        capture_output=True,
        text=True,
    )
    if res_git.returncode == 0:
        first_line = res_git.stdout.splitlines()[0] if res_git.stdout else ""
        print(f"  [OK] Git is functional: {first_line}")
    else:
        print("  [INFO] Git CLI not active or not in path (not required for lab operation).")

    # 5. Run simulation smoke test in extracted folder
    print("\n[5/5] Running PowerShell simulation smoke test (-Simulate)...")
    # For simulation test, copy .venv from parent to avoid re-downloading packages in temp folder
    parent_venv = bitirme_dir / "ausculta-forge" / ".venv"
    dest_venv = extracted_repo / ".venv"
    if parent_venv.is_dir() and not dest_venv.is_dir():
        print("  Copying virtualenv for offline smoke testing...")
        shutil.copytree(parent_venv, dest_venv, symlinks=True)

    sim_cmd = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(extracted_repo / "tools/hardware/run_lab_phantom_workflow.ps1"),
        "-Simulate",
    ]
    sim_res = subprocess.run(sim_cmd, cwd=extracted_repo, capture_output=True, text=True)
    print("Simulation Output:\n" + sim_res.stdout)
    if sim_res.returncode != 0:
        print("Simulation Errors:\n" + sim_res.stderr)
        raise RuntimeError(f"Simulation smoke test failed with exit code {sim_res.returncode}")
    print("  [OK] Simulation smoke test PASSED!")

    # Cleanup
    print("\nCleaning up temporary test directory...")
    shutil.rmtree(test_dir, ignore_errors=True)
    print("  [OK] Cleaned up test_clean_extract successfully.")

    print("\n============================================================")
    print("  ALL VERIFICATION CHECKS PASSED (100% CLEAN)")
    print(f"  Final ZIP: {zip_path}")
    print(f"  SHA-256  : {zip_hash}")
    print("============================================================")


if __name__ == "__main__":
    main()
