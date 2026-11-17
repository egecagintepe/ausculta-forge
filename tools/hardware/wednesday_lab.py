"""AuscultaForge — Single-Command Autonomous Wednesday Lab Orchestrator CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software"))

try:
    from pcg_app.wednesday_orchestrator import (  # noqa: E402
        DEFAULT_G1_MANIFEST_REL,
        DEFAULT_G2_MANIFEST_REL,
        DEFAULT_STATE_REL,
        G2_CAPTURE_TARGET_SAMPLES,
        OPERATOR_CHECKLIST_TR,
        get_wednesday_status_snapshot,
        run_wednesday_orchestrator,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        f"MISSING: {exc.name}. Run .\\.venv\\Scripts\\python.exe tools/hardware/wednesday_lab.py after scripts\\handoff\\windows_setup.ps1."
    ) from None


def _print_banner(result: dict) -> None:
    state = result.get("state") or {}
    stages = state.get("stages") or {}
    zip_info = state.get("latest_return_zip") or {}
    print("\n==========================================================")
    print(f"  AUSCULTAFORGE — CARSAMBA LAB DURUMU: {result.get('status')}")
    print("==========================================================")
    for name, info in stages.items():
        print(f"  - {name:22s}: {info.get('status')}")
    if result.get("status") == "WAITING_OPERATOR":
        print("\n" + (result.get("reason") or ""))
        print("\n" + OPERATOR_CHECKLIST_TR)
    elif result.get("status") == "INCONCLUSIVE":
        print(f"\n[INCONCLUSIVE / BELİRSİZ UYARAN AYRIMI] {result.get('reason') or ''}")
        print("Mikrofon alt deligi acikligini, hoparlor/uyaran ses seviyesini ve mesafesini kontrol edip tekrar deneyin.")
    if result.get("error"):
        print(f"\n[HATA / DURMA NEDENI] {result['error']}")
    if zip_info.get("zip_path"):
        print("\n==========================================================")
        print("  EGE'YE GONDERILECEK TEK KANIT PAKETI (ZIP)")
        print("==========================================================")
        print(f"  DOSYA : {zip_info['zip_path']}")
        print(f"  BOYUT : {zip_info.get('zip_size_bytes')} byte ({zip_info.get('file_count')} dosya)")
        print(f"  SHA256: {zip_info.get('zip_sha256')}")
        print("  Bu ZIP dosyasini WhatsApp / Google Drive ile Ege'ye gonderin.")
    gh = state.get("github_evidence_drop") or {}
    if gh.get("status") not in (None, "NOT_REQUESTED"):
        print(f"\n  GitHub Kanit Yükleme Durumu: {gh.get('status')} ({gh.get('reason') or gh.get('files')})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=None, help="Explicit Espressif USB CDC COM port (auto-selects only if unique)")
    parser.add_argument("--state-file", type=Path, default=None, help=f"Persistent JSON state path (default: {DEFAULT_STATE_REL})")
    parser.add_argument("--g1-manifest", type=Path, default=None, help=f"G1 manifest (default: {DEFAULT_G1_MANIFEST_REL})")
    parser.add_argument("--g2-manifest", type=Path, default=None, help=f"G2 candidate manifest (default: {DEFAULT_G2_MANIFEST_REL})")
    parser.add_argument("--operator", default="Kaan_Ozan", help="Operator names")
    parser.add_argument("--notes", default="", help="Optional session notes")
    parser.add_argument("--force-g1", action="store_true", help="Re-run G1 even if already PASSED for this board")
    parser.add_argument("--skip-g2-captures", action="store_true", help="Stop after H0/G2 physical gate verification")
    parser.add_argument("--assume-g2-flashed", action="store_true", help="Confirm operator already flashed G2 firmware on this board")
    parser.add_argument("--g2-samples", type=int, default=G2_CAPTURE_TARGET_SAMPLES, help="G2 samples per capture (multiple of 256, default 480000=10s)")
    parser.add_argument("--return-zip", type=Path, default=None, help="Output path for return ZIP")
    parser.add_argument("--push-evidence", action="store_true", help="Optionally push summary JSON/MD into experiments/hardware/team_2026-11-18/")
    parser.add_argument("--status-only", action="store_true", help="Print passive Wednesday Lab status JSON without touching USB")
    parser.add_argument("--authorize-g2", action="store_true", help="Run interactive G2 physical attestation gate (never auto-confirms)")
    parser.add_argument("--bclk", type=int, default=4)
    parser.add_argument("--ws", type=int, default=5)
    parser.add_argument("--din", type=int, default=6)
    parser.add_argument("--slot", choices=("left", "right"), default="left")
    parser.add_argument("--vdd-volts", type=float, default=None)
    parser.add_argument("--multimeter", default=None)
    parser.add_argument("--non-interactive", action="store_true", help="Do not wait for Enter prompts on audio cues (never bypasses G2 attestation)")
    args = parser.parse_args(argv)

    if args.status_only:
        snap = get_wednesday_status_snapshot(ROOT, state_path=args.state_file)
        print(json.dumps(snap, indent=2, ensure_ascii=False))
        return 0

    auth_args = None
    if args.authorize_g2:
        if args.vdd_volts is None or not args.multimeter:
            parser.error("--authorize-g2 requires --vdd-volts and --multimeter")
        auth_args = {
            "bclk": args.bclk,
            "ws": args.ws,
            "din": args.din,
            "slot": args.slot,
            "vdd_volts": args.vdd_volts,
            "operator": args.operator,
            "multimeter": args.multimeter,
        }

    def _audio_cue(msg: str) -> None:
        print(f"\n[OPERATÖR YÖNLENDİRMESİ] {msg}")
        if not args.non_interactive:
            input("Hazir oldugunuzda Enter'a basin...")

    result = run_wednesday_orchestrator(
        root=ROOT,
        state_path=args.state_file,
        port=args.port,
        g1_manifest_path=args.g1_manifest,
        g2_manifest_path=args.g2_manifest,
        operator=args.operator,
        notes=args.notes,
        force_g1=args.force_g1,
        authorize_g2_args=auth_args,
        run_g2_captures=False if args.skip_g2_captures else None,
        assume_g2_flashed=args.assume_g2_flashed,
        g2_target_samples=args.g2_samples,
        return_zip_path=args.return_zip,
        push_evidence=args.push_evidence,
        confirm_operator_ready=_audio_cue,
    )
    _print_banner(result)
    status = result.get("status")
    if status == "FAILED":
        return 1
    if status == "INCONCLUSIVE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
