"""AuscultaForge — Read-Only Wednesday Lab Return ZIP Packager.

Collects physical hardware evidence, recorded WAV sessions, G2 attestations,
qualify JSON reports, updated academic progress docs, and recent diagnostic logs
into one verified SHA-256 ZIP archive so teammates do not need Git or GitHub push
access to deliver their measurements back to Ege.

Pure Python standard library only; strictly read-only on all source files.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any, Optional
import zipfile


DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _detect_baseline_commit(root: Path) -> Optional[str]:
    for rel in (
        "docs/handoff/HANDOFF_VERSION.json",
        "firmware/releases/g1_release_20261117/firmware_build_manifest.json",
    ):
        p = root / rel
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("commit"):
                    return str(data["commit"])
            except (OSError, json.JSONDecodeError):
                pass
    return None


def collect_return_entries(root: Path, appdata_logs_dir: Optional[Path] = None, extra_dirs: Optional[list[Path]] = None) -> list[tuple[Path, str]]:
    """Discover existing evidence files cleanly without modifying or inventing artifacts."""
    root = root.resolve()
    collected: dict[str, Path] = {}

    def add_file(src: Path, arcname: str) -> None:
        if not src.is_file():
            return
        if src.name in (".gitkeep", "Thumbs.db", ".DS_Store"):
            return
        norm = arcname.replace("\\", "/")
        if norm not in collected:
            collected[norm] = src

    # 1. experiments/hardware/** (includes physical_g1 bundles, g2 qualify JSONs, preflight JSONs, photos)
    hw_dir = root / "experiments/hardware"
    if hw_dir.is_dir():
        for p in sorted(hw_dir.rglob("*")):
            if p.is_file():
                add_file(p, p.relative_to(root).as_posix())

    # 2. experiments/sessions/session_*/** (includes raw.wav, session.json, manifest.json)
    sess_dir = root / "experiments/sessions"
    if sess_dir.is_dir():
        for child in sorted(sess_dir.iterdir()):
            if child.is_dir() and child.name.startswith("session_"):
                for p in sorted(child.rglob("*")):
                    if p.is_file():
                        add_file(p, p.relative_to(root).as_posix())

    # 3. Release attestations & local flash logs (never alters source or rollback files)
    for rel in (
        "firmware/releases/g2_candidate_20261117/g2_physical_attestation.json",
        "firmware/releases/g2_candidate_20261117/firmware_build_manifest.json",
        "firmware/build/release/firmware_build_manifest.json",
        "firmware/build/release/first-flash.txt",
        "firmware/build/release/board_identity.json",
    ):
        p = root / rel
        if p.is_file():
            add_file(p, rel)

    # 4. SDP weekly reports and Week 1-9 submissions
    sdp_dir = root / "docs/sdp"
    if sdp_dir.is_dir():
        for fixed in ("SDP4_WEEK01_06_DRAFT_PROGRESS_REPORT.md", "PROGRESS_ASOF_2026-11-17.md", "README.md"):
            fp = sdp_dir / fixed
            if fp.is_file():
                add_file(fp, fp.relative_to(root).as_posix())
        for wk in range(1, 10):
            wk_dir = sdp_dir / f"week-{wk:02d}"
            if wk_dir.is_dir():
                for p in sorted(wk_dir.rglob("*")):
                    if p.is_file():
                        add_file(p, p.relative_to(root).as_posix())

    # 5. Optional Flight Recorder logs from %APPDATA%/AuscultaForge/logs
    logs_dir = appdata_logs_dir
    if logs_dir is None:
        appdata = os.environ.get("APPDATA")
        if appdata:
            logs_dir = Path(appdata) / "AuscultaForge" / "logs"
    if logs_dir is not None and logs_dir.is_dir():
        log_files = sorted(
            [p for p in logs_dir.iterdir() if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:10]
        for p in log_files:
            add_file(p, f"appdata_logs/{p.name}")

    # 6. Optional extra directories (e.g., lab photos folder outside repo)
    if extra_dirs:
        for idx, ext in enumerate(extra_dirs):
            ext_resolved = ext.resolve()
            if ext_resolved.is_dir():
                for p in sorted(ext_resolved.rglob("*")):
                    if p.is_file():
                        add_file(p, f"extra_evidence_{idx+1}/{p.relative_to(ext_resolved).as_posix()}")

    return [(src, arc) for arc, src in sorted(collected.items())]


def _build_gate_evidence_summary(root: Path, entries: list[tuple[Path, str]]) -> dict[str, Any]:
    g1_bundles: list[str] = []
    g2_qualify_files: list[str] = []
    recorded_sessions: list[dict[str, Any]] = []
    attestation_present = False
    boot_logs: list[str] = []

    for src, arc in entries:
        if arc.endswith("/acceptance_report.md") and arc.startswith("experiments/hardware/"):
            g1_bundles.append(str(Path(arc).parent.as_posix()))
        elif arc.startswith("experiments/hardware/") and arc.endswith(".json"):
            if "qualify" in src.name.lower():
                g2_qualify_files.append(arc)
            else:
                try:
                    data = json.loads(src.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and data.get("kind") == "RAW_RECORDING_SCREEN_ONLY":
                        g2_qualify_files.append(arc)
                except (OSError, json.JSONDecodeError):
                    pass
        elif arc == "firmware/releases/g2_candidate_20261117/g2_physical_attestation.json":
            attestation_present = True
        elif arc.startswith("experiments/hardware/") and "boot" in src.name.lower():
            boot_logs.append(arc)
        elif arc.startswith("experiments/sessions/") and src.name == "session.json":
            try:
                meta = json.loads(src.read_text(encoding="utf-8"))
                recorded_sessions.append({
                    "session_id": meta.get("session_id"),
                    "source": meta.get("source"),
                    "acquisition_mode": meta.get("acquisition_mode"),
                    "acquisition_origin": (meta.get("processing_profile") or {}).get("acquisition_origin"),
                    "sample_rate_hz": meta.get("sample_rate_hz"),
                    "total_samples": meta.get("total_samples"),
                    "duration_s": meta.get("duration_s"),
                    "raw_wav_sha256": meta.get("raw_wav_sha256"),
                })
            except (OSError, json.JSONDecodeError):
                pass

    return {
        "h0_g2_attestation_present": attestation_present,
        "g1_acceptance_bundles": sorted(g1_bundles),
        "g2_qualification_jsons": sorted(g2_qualify_files),
        "recorded_sessions": recorded_sessions,
        "boot_logs": sorted(boot_logs),
    }


def create_lab_return_zip(
    root: Path = DEFAULT_ROOT,
    output_path: Optional[Path] = None,
    operator: str = "Kaan_Ozan",
    notes: str = "",
    appdata_logs_dir: Optional[Path] = None,
    extra_dirs: Optional[list[Path]] = None,
) -> dict[str, Any]:
    """Build a verified SHA-256 return ZIP archive from real lab measurements."""
    root = Path(root).resolve()
    now_utc = datetime.now(timezone.utc)
    safe_op = re.sub(r"[^A-Za-z0-9_-]+", "_", str(operator).strip()) or "team"

    if output_path is None:
        stamp = now_utc.strftime("%Y%m%d_%H%M%SZ")
        out_zip = root / f"AuscultaForge_Lab_Return_{safe_op}_{stamp}.zip"
    else:
        out_zip = Path(output_path).resolve()

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    entries = collect_return_entries(root, appdata_logs_dir=appdata_logs_dir, extra_dirs=extra_dirs)

    file_records: list[dict[str, Any]] = []
    sha_lines: list[str] = []

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, arc in entries:
            digest = _sha256_file(src)
            size = src.stat().st_size
            zf.write(src, arcname=arc)
            file_records.append({"arcname": arc, "size_bytes": size, "sha256": digest})
            sha_lines.append(f"{digest}  {arc}")

        manifest = {
            "schema_version": "1.0.0",
            "created_utc": now_utc.isoformat(),
            "operator": str(operator),
            "notes": str(notes),
            "baseline_commit": _detect_baseline_commit(root),
            "host_platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "file_count": len(file_records),
            "gate_evidence_summary": _build_gate_evidence_summary(root, entries),
            "files": file_records,
            "integrity_note": "Strictly read-only snapshot of actual local lab files; no synthetic values added.",
        }
        zf.writestr("RETURN_PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        zf.writestr("SHA256SUMS.txt", "\n".join(sha_lines) + ("\n" if sha_lines else ""))

    return {
        "status": "PACKAGED",
        "zip_path": str(out_zip),
        "zip_size_bytes": out_zip.stat().st_size,
        "zip_sha256": _sha256_file(out_zip),
        "file_count": len(file_records),
        "gate_evidence_summary": manifest["gate_evidence_summary"],
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Project folder root")
    parser.add_argument("--output", type=Path, default=None, help="Target ZIP archive path")
    parser.add_argument("--operator", default="Kaan_Ozan", help="Operator names")
    parser.add_argument("--notes", default="", help="Optional summary notes from the session")
    parser.add_argument("--extra-dir", type=Path, action="append", default=None, help="Optional extra folder (e.g., lab photos)")
    args = parser.parse_args(argv)

    summary = create_lab_return_zip(
        root=args.root,
        output_path=args.output,
        operator=args.operator,
        notes=args.notes,
        extra_dirs=args.extra_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
