#!/usr/bin/env python3
"""
AuscultaForge — Portable Lab Delivery Package Builder (25 Nov 2026)

Packages the repository at HEAD (feature/rev04-evidence-integration) for
zero-configuration transfer to a Windows lab laptop:
1. All files tracked in Git at HEAD (including LAPTOP_PROMPT.md, START_HERE_2026-11-25.md).
2. Clean .git directory preserving commit 12c439e and branch tracking.
3. Reference PCG stimulus: data/raw/week6_real_pcg_20261026/circor/40058_AV.wav.
4. Strictly excludes .venv, node_modules, build directories, *.zip, and caches.
5. Computes and prints the final SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
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
    repo_root = Path(__file__).resolve().parent.parent
    output_zip = repo_root.parent / "AuscultaForge_Lab_Delivery_20261125.zip"

    print("============================================================")
    print("  AUSCULTAFORGE — LAB DELIVERY PACKAGING (25 Nov 2026)")
    print("============================================================")
    print(f"Repository Root : {repo_root}")
    print(f"Output ZIP Path : {output_zip}")

    # 1. Get git tracked files at HEAD
    res = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    print(f"Git Tracked Files: {len(tracked_files)} files found.")

    # 2. Check reference WAV
    ref_wav_rel = "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav"
    ref_wav_path = repo_root / ref_wav_rel
    if not ref_wav_path.is_file():
        raise FileNotFoundError(f"Missing reference WAV: {ref_wav_path}")
    ref_hash = sha256_file(ref_wav_path)
    expected_ref_hash = "108df8f77491a5706209aa5b467ed10ac43f2a0b847801fe666ba8146dcbf8e8"
    if ref_hash.lower() != expected_ref_hash.lower():
        raise ValueError(f"Reference WAV hash mismatch! Got {ref_hash}, expected {expected_ref_hash}")
    print(f"Reference PCG   : OK (SHA256: {ref_hash})")

    # 3. Create ZIP archive
    if output_zip.exists():
        output_zip.unlink()

    added_count = 0
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # Add tracked files
        for rel in tracked_files:
            file_path = repo_root / rel
            if file_path.is_file():
                arcname = f"ausculta-forge/{rel.replace(os.sep, '/')}"
                zf.write(file_path, arcname)
                added_count += 1

        # Add reference WAV (untracked in git)
        zf.write(ref_wav_path, f"ausculta-forge/{ref_wav_rel.replace(os.sep, '/')}")
        added_count += 1

        # Add clean .git directory
        git_dir = repo_root / ".git"
        if git_dir.is_dir():
            for root, _, files in os.walk(git_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(repo_root)
                    # Skip transient git logs, hooks, or locks
                    if any(part in rel_p.parts for part in ("logs", "hooks")) or f.endswith(".lock"):
                        continue
                    arcname = f"ausculta-forge/{str(rel_p).replace(os.sep, '/')}"
                    zf.write(full_p, arcname)
                    added_count += 1

    zip_size_mb = output_zip.stat().st_size / (1024 * 1024)
    zip_sha = sha256_file(output_zip)

    print(f"Total Packaged  : {added_count} files ({zip_size_mb:.2f} MB)")
    print(f"ZIP SHA-256     : {zip_sha}")
    print("============================================================")
    print("Packaging completed successfully!")


if __name__ == "__main__":
    main()
