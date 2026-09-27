"""Download and verify official PhysioNet CirCor DigiScope v1.0.3 dataset.

Uses official PhysioNet open S3 mirror:
https://physionet-open.s3.amazonaws.com/circor-heart-sound/1.0.3/

Validates dataset files against official SHA256SUMS.txt.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from pathlib import Path
import sys
import time
import urllib.request

PHYSIONET_S3_BASE = "https://physionet-open.s3.amazonaws.com/circor-heart-sound/1.0.3"


def verify_file_sha256(path: Path, expected_hash: str) -> bool:
    if not path.is_file():
        return False
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower() == expected_hash.lower()


def download_single_file(url: str, dest_path: Path, expected_sha: str | None = None) -> tuple[str, bool, str]:
    """Download one file with retry and optional checksum validation."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.is_file() and expected_sha:
        if verify_file_sha256(dest_path, expected_sha):
            return str(dest_path.name), True, "already_cached_valid"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AuscultaForge-CirCor-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as out_f:
                while chunk := resp.read(65536):
                    out_f.write(chunk)
            break
        except Exception as e:
            if attempt == 2:
                return str(dest_path.name), False, f"download_failed: {e}"
            time.sleep(1.0)

    if expected_sha:
        if not verify_file_sha256(dest_path, expected_sha):
            return str(dest_path.name), False, "checksum_mismatch"

    return str(dest_path.name), True, "downloaded_and_verified"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download CirCor DigiScope v1.0.3 from PhysioNet S3 mirror.")
    parser.add_argument("--dest", type=str, default="data/external/circor-heart-sound-1.0.3")
    parser.add_argument("--subjects", type=int, default=50, help="Number of deterministic subjects (default 50, 0 for all)")
    parser.add_argument("--workers", type=int, default=16, help="Concurrent download workers")
    args = parser.parse_args()

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== CirCor v1.0.3 Downloader & Integrity Verifier ===")
    print(f"Destination: {dest_dir.resolve()}")
    print(f"Source: {PHYSIONET_S3_BASE}")

    # 1. Fetch SHA256SUMS.txt
    sums_file = dest_dir / "SHA256SUMS.txt"
    sums_url = f"{PHYSIONET_S3_BASE}/SHA256SUMS.txt"
    print("Fetching official SHA256SUMS.txt...")
    _, ok, status = download_single_file(sums_url, sums_file)
    if not ok:
        print(f"ERROR: Failed to fetch SHA256SUMS.txt: {status}")
        sys.exit(1)

    with open(sums_file, "r", encoding="utf-8", errors="replace") as f:
        sums_text = f.read()

    # Parse checksums
    checksum_map: dict[str, str] = {}
    subject_map: dict[str, list[str]] = {}

    for line in sums_text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            sha = parts[0]
            rel_path = parts[1]
            checksum_map[rel_path] = sha

            if rel_path.startswith("training_data/"):
                fname = rel_path.split("/")[-1]
                stem = fname.rsplit(".", 1)[0]
                subj = stem.split("_")[0]
                if subj not in subject_map:
                    subject_map[subj] = []
                subject_map[subj].append(rel_path)

    all_subjects = sorted(subject_map.keys())
    print(f"Total available subjects in dataset index: {len(all_subjects)}")

    if args.subjects and args.subjects > 0:
        selected_subjects = all_subjects[:args.subjects]
        print(f"Selected first {len(selected_subjects)} deterministic subjects for pilot.")
    else:
        selected_subjects = all_subjects
        print(f"Selected all {len(selected_subjects)} subjects.")

    files_to_download: list[tuple[str, str]] = []
    # Companion root files
    for root_file in ["LICENSE.txt", "RECORDS", "training_data.csv"]:
        if root_file in checksum_map:
            files_to_download.append((root_file, checksum_map[root_file]))

    for s in selected_subjects:
        for rel_path in subject_map[s]:
            # Focus on .wav, .tsv, .hea
            if any(rel_path.endswith(ext) for ext in [".wav", ".tsv", ".hea", ".txt"]):
                files_to_download.append((rel_path, checksum_map[rel_path]))

    print(f"Total files to download and verify: {len(files_to_download)}")
    t0 = time.time()

    checked = 0
    passed = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for rel_path, expected_sha in files_to_download:
            target_p = dest_dir / rel_path
            url = f"{PHYSIONET_S3_BASE}/{rel_path}"
            fut = executor.submit(download_single_file, url, target_p, expected_sha)
            futures[fut] = rel_path

        for fut in as_completed(futures):
            rel_p = futures[fut]
            fname, success, msg = fut.result()
            checked += 1
            if success:
                passed += 1
            else:
                failed += 1
                print(f"FAIL: {rel_p} -> {msg}")

            if checked % 50 == 0 or checked == len(files_to_download):
                print(f"Progress: {checked}/{len(files_to_download)} files (Passed: {passed}, Failed: {failed})")

    elapsed = time.time() - t0
    print("\n=== Checksum and Download Verification Summary ===")
    print(f"checksum_files_checked: {checked}")
    print(f"checksum_passed: {passed}")
    print(f"checksum_failed: {failed}")
    print(f"Total time elapsed: {elapsed:.2f}s")

    if failed > 0:
        print("ERROR: One or more checksum verifications failed!")
        sys.exit(1)
    else:
        print("SUCCESS: 100% of downloaded files verified with official SHA256 checksums.")


if __name__ == "__main__":
    main()
