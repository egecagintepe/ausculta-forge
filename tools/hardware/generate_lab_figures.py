"""Generate EVIDENCE_MANIFEST.json and real-data SVG figures for 2026-11-25 lab milestone."""

from __future__ import annotations

from datetime import datetime, timezone
import glob
import json
from pathlib import Path
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

REPO_ROOT = Path(__file__).resolve().parents[2]
LAB_DIR = REPO_ROOT / "docs" / "lab" / "2026-11-25"
FIG_DIR = LAB_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def _polyline(xs: np.ndarray, ys: np.ndarray, x0: float, y0: float, w: float, h: float, ymin: float, ymax: float) -> str:
    pts = []
    n = len(xs)
    for i in range(n):
        px = x0 + (i / max(n - 1, 1)) * w
        norm_y = (ys[i] - ymin) / max(ymax - ymin, 1e-12)
        norm_y = max(0.0, min(1.0, norm_y))
        py = y0 + h - norm_y * h
        pts.append(f"{px:.1f},{py:.1f}")
    return " ".join(pts)


def generate_figures() -> None:
    # 1. Signal path architecture diagram (SVG)
    arch_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="220" viewBox="0 0 960 220">
  <rect width="960" height="220" fill="#faf8f5" rx="10"/>
  <text x="480" y="30" text-anchor="middle" font-family="Segoe UI, Arial" font-size="16" font-weight="bold" fill="#2b1d1f">AuscultaForge Physical Phantom Signal Path (25 Nov 2026)</text>
  <g font-family="Consolas, monospace" font-size="11" text-anchor="middle">
    <rect x="20" y="65" width="130" height="64" rx="8" fill="#fff" stroke="#7a3842" stroke-width="2"/>
    <text x="85" y="92" font-weight="bold" fill="#7a3842">PC Audio Out</text>
    <text x="85" y="110" fill="#555">40058_AV.wav</text>
    <text x="85" y="123" fill="#555">Realtek AUX 20%</text>

    <line x1="150" y1="97" x2="180" y2="97" stroke="#7a3842" stroke-width="2"/>
    <rect x="180" y="65" width="140" height="64" rx="8" fill="#fff" stroke="#7a3842" stroke-width="2"/>
    <text x="250" y="92" font-weight="bold" fill="#7a3842">PAM8403 BTL</text>
    <text x="250" y="110" fill="#555">Indep. 5V/2A DC</text>
    <text x="250" y="123" fill="#555">12 Ohm Exciter</text>

    <line x1="320" y1="97" x2="350" y2="97" stroke="#7a3842" stroke-width="2"/>
    <rect x="350" y="65" width="145" height="64" rx="8" fill="#fff" stroke="#8a6d3b" stroke-width="2"/>
    <text x="422" y="92" font-weight="bold" fill="#8a6d3b">Phantom Assembly</text>
    <text x="422" y="110" fill="#555">Cardboard Plate</text>
    <text x="422" y="123" fill="#555">+ RTV-2 Silicone</text>

    <line x1="495" y1="97" x2="525" y2="97" stroke="#8a6d3b" stroke-width="2"/>
    <rect x="525" y="65" width="135" height="64" rx="8" fill="#fff" stroke="#2d6a4f" stroke-width="2"/>
    <text x="592" y="92" font-weight="bold" fill="#2d6a4f">Stethoscope</text>
    <text x="592" y="110" fill="#555">Diaphragm +</text>
    <text x="592" y="123" fill="#555">Sealed Y-Tubing</text>

    <line x1="660" y1="97" x2="690" y2="97" stroke="#2d6a4f" stroke-width="2"/>
    <rect x="690" y="65" width="125" height="64" rx="8" fill="#fff" stroke="#2d6a4f" stroke-width="2"/>
    <text x="752" y="92" font-weight="bold" fill="#2d6a4f">INMP441 MEMS</text>
    <text x="752" y="110" fill="#555">GPIO 4/5/6</text>
    <text x="752" y="123" fill="#555">L/R=GND, 3.3V</text>

    <line x1="815" y1="97" x2="840" y2="97" stroke="#2d6a4f" stroke-width="2"/>
    <rect x="840" y="65" width="105" height="64" rx="8" fill="#fff" stroke="#1d3557" stroke-width="2"/>
    <text x="892" y="92" font-weight="bold" fill="#1d3557">ESP32-S3</text>
    <text x="892" y="110" fill="#555">G2 FW 1.1.0</text>
    <text x="892" y="123" fill="#555">COM10 48kHz</text>
  </g>
  <text x="480" y="180" text-anchor="middle" font-family="Segoe UI, Arial" font-size="12" fill="#444">Exploratory P01 (trial_20261125_095717_275ae8, 1-10s): 20-250 Hz Coherence = 0.8820 | Contextual SNR = +17.30 dB | 0 Drops / 0 CRC</text>
</svg>"""
    (FIG_DIR / "signal_path_architecture.svg").write_text(arch_svg, encoding="utf-8")

    # 2. RMS vs Windows volume curve from real trials
    pts = [
        ("Q01 (0%)", 0.001469, "#6c757d"),
        ("P01 #1 (~4%)", 0.001330, "#8a6d3b"),
        ("P01 #2 (10%)", 0.001524, "#8a6d3b"),
        ("P01 #3 (20%)", 0.010761, "#2d6a4f"),
    ]
    bars = []
    for idx, (lbl, val, col) in enumerate(pts):
        bx = 95 + idx * 145
        bh = (val / 0.012) * 150
        by = 200 - bh
        bars.append(f'<rect x="{bx}" y="{by:.1f}" width="70" height="{bh:.1f}" fill="{col}" rx="4"/>')
        bars.append(f'<text x="{bx+35}" y="{by-8:.1f}" text-anchor="middle" font-family="Consolas" font-size="11" font-weight="bold" fill="#222">{val:.6f}</text>')
        bars.append(f'<text x="{bx+35}" y="220" text-anchor="middle" font-family="Segoe UI" font-size="11" fill="#333">{lbl}</text>')
    vol_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="700" height="250" viewBox="0 0 700 250">
  <rect width="700" height="250" fill="#faf8f5" rx="10"/>
  <text x="350" y="28" text-anchor="middle" font-family="Segoe UI, Arial" font-size="15" font-weight="bold" fill="#2b1d1f">Stable 1-10s Bandpass (20-500 Hz) RMS vs. Windows Playback Volume</text>
  <line x1="60" y1="200" x2="660" y2="200" stroke="#999" stroke-width="1"/>
  {''.join(bars)}
</svg>"""
    (FIG_DIR / "rms_vs_volume_curve.svg").write_text(vol_svg, encoding="utf-8")

    # 3. Q01 startup transient (0-3s envelope from real Q01 raw.wav)
    q_wav = REPO_ROOT / "experiments/phantom/quiet_baselines/session_20261125_093843_959d7eb0/raw.wav"
    sr, q_arr = wavfile.read(q_wav)
    q_x = q_arr[: 3 * sr].astype(np.float64)
    # downsample to 600 bins (max abs per 5ms bin)
    bins = 600
    step = len(q_x) // bins
    q_env = np.array([np.max(np.abs(q_x[i * step : (i + 1) * step])) for i in range(bins)])
    poly_q = _polyline(np.arange(bins), q_env, 60, 45, 620, 150, 0.0, 1.05)
    q_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="240" viewBox="0 0 720 240">
  <rect width="720" height="240" fill="#faf8f5" rx="10"/>
  <text x="360" y="26" text-anchor="middle" font-family="Segoe UI, Arial" font-size="14" font-weight="bold" fill="#2b1d1f">Official Q01 (session_20261125_093843_959d7eb0) — First 3s Peak Envelope (5ms bins)</text>
  <rect x="60" y="45" width="206" height="150" fill="#fde2e4" opacity="0.5"/>
  <text x="163" y="62" text-anchor="middle" font-family="Consolas" font-size="10" fill="#9b2226">0-1s Startup Transient (254 clips)</text>
  <text x="460" y="62" text-anchor="middle" font-family="Consolas" font-size="10" fill="#2d6a4f">1-10s Settled Baseline (~0.00147 FS BP RMS)</text>
  <rect x="60" y="45" width="620" height="150" fill="none" stroke="#bbb"/>
  <polyline fill="none" stroke="#9b2226" stroke-width="1.5" points="{poly_q}"/>
  <text x="60" y="212" font-family="Consolas" font-size="10" fill="#555">0.0s</text>
  <text x="266" y="212" font-family="Consolas" font-size="10" fill="#555">1.0s</text>
  <text x="473" y="212" font-family="Consolas" font-size="10" fill="#555">2.0s</text>
  <text x="665" y="212" font-family="Consolas" font-size="10" fill="#555">3.0s</text>
</svg>"""
    (FIG_DIR / "q01_startup_transient.svg").write_text(q_svg, encoding="utf-8")

    # 4. P01 Retest 03 (1-10s) reference vs captured 20-500 Hz envelope
    t_dir = REPO_ROOT / "experiments/phantom/trial_20261125_095717_275ae8"
    sr_s, stim_i = wavfile.read(t_dir / "stimulus_pcg_48000hz.wav")
    stim = stim_i.astype(np.float64) / 32768.0
    sr_c, cap = wavfile.read(t_dir / "session_20261125_095718_2d385ca8/raw.wav")
    sos = butter(4, [20.0, 500.0], btype="bandpass", fs=sr_c, output="sos")
    stim_1_10 = sosfiltfilt(sos, stim)[sr_c:]
    cap_1_10 = sosfiltfilt(sos, cap.astype(np.float64))[sr_c:]
    bins_p = 450
    step_p = len(cap_1_10) // bins_p
    ref_env = np.array([np.max(np.abs(stim_1_10[i * step_p : (i + 1) * step_p])) for i in range(bins_p)])
    cap_env = np.array([np.max(np.abs(cap_1_10[i * step_p : (i + 1) * step_p])) for i in range(bins_p)])
    ref_env_n = ref_env / max(np.max(ref_env), 1e-12)
    cap_env_n = cap_env / max(np.max(cap_env), 1e-12)
    poly_ref = _polyline(np.arange(bins_p), ref_env_n, 60, 45, 620, 70, 0.0, 1.05)
    poly_cap = _polyline(np.arange(bins_p), cap_env_n, 60, 135, 620, 70, 0.0, 1.05)
    p01_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="245" viewBox="0 0 720 245">
  <rect width="720" height="245" fill="#faf8f5" rx="10"/>
  <text x="360" y="25" text-anchor="middle" font-family="Segoe UI, Arial" font-size="14" font-weight="bold" fill="#2b1d1f">P01 Exploratory Retest #3 (1-10s, 20-500 Hz Normalized Envelope)</text>
  <text x="65" y="58" font-family="Consolas" font-size="10" fill="#1d3557">Reference 40058_AV.wav (1-10s)</text>
  <rect x="60" y="45" width="620" height="70" fill="none" stroke="#ccc"/>
  <polyline fill="none" stroke="#1d3557" stroke-width="1.3" points="{poly_ref}"/>
  <text x="65" y="148" font-family="Consolas" font-size="10" fill="#2d6a4f">Captured INMP441 (1-10s) | Coh=0.8820 | SNR=+17.30 dB | S1/S2=10/16</text>
  <rect x="60" y="135" width="620" height="70" fill="none" stroke="#ccc"/>
  <polyline fill="none" stroke="#2d6a4f" stroke-width="1.3" points="{poly_cap}"/>
  <text x="60" y="222" font-family="Consolas" font-size="10" fill="#555">1.0s</text>
  <text x="360" y="222" font-family="Consolas" font-size="10" fill="#555">5.5s</text>
  <text x="660" y="222" font-family="Consolas" font-size="10" fill="#555">10.0s</text>
</svg>"""
    (FIG_DIR / "p01_retest03_waveform_and_alignment.svg").write_text(p01_svg, encoding="utf-8")


def generate_manifest() -> None:
    artifacts = []
    for sd in sorted((REPO_ROOT / "experiments/phantom/quiet_baselines").glob("session_20261125_*")):
        sess = json.loads((sd / "session.json").read_text(encoding="utf-8"))
        wav = sd / "raw.wav"
        artifacts.append({
            "kind": "mic_or_coupling_or_q01",
            "session_id": sess["session_id"],
            "role": sess.get("processing_profile", {}).get("capture_role"),
            "started_at_utc": sess.get("started_at_utc"),
            "total_samples": sess.get("total_samples"),
            "sample_rate_hz": sess.get("sample_rate_hz"),
            "raw_wav_relpath_local_only": str(wav.relative_to(REPO_ROOT)).replace("\\", "/"),
            "raw_wav_bytes": wav.stat().st_size if wav.is_file() else 0,
            "raw_wav_sha256": sess.get("raw_wav_sha256"),
            "session_json_relpath": str((sd / "session.json").relative_to(REPO_ROOT)).replace("\\", "/"),
            "stream_quality": sess.get("stream_quality"),
            "git_commit_sha": sess.get("git_commit_sha"),
        })

    for td in sorted((REPO_ROOT / "experiments/phantom").glob("trial_20261125_*")):
        rep_f = td / "phantom_pcg_experiment_report.json"
        rep = json.loads(rep_f.read_text(encoding="utf-8")) if rep_f.is_file() else {}
        wavs = list(td.glob("session_*/raw.wav"))
        wav = wavs[0] if wavs else None
        sess_f = wav.parent / "session.json" if wav else None
        sess = json.loads(sess_f.read_text(encoding="utf-8")) if sess_f and sess_f.is_file() else {}
        artifacts.append({
            "kind": "phantom_trial",
            "trial_id": td.name,
            "session_id": sess.get("session_id"),
            "notes": rep.get("notes", "FAILED_DIGITAL_SILENCE"),
            "timestamp_utc": rep.get("timestamp_utc") or sess.get("started_at_utc"),
            "gate_status": rep.get("gate_status", "FAILED_DIGITAL_SILENCE"),
            "raw_wav_relpath_local_only": str(wav.relative_to(REPO_ROOT)).replace("\\", "/") if wav else None,
            "raw_wav_bytes": wav.stat().st_size if wav else 0,
            "raw_wav_sha256": sess.get("raw_wav_sha256"),
            "report_json_relpath": str(rep_f.relative_to(REPO_ROOT)).replace("\\", "/") if rep_f.is_file() else None,
        })

    manifest = {
        "manifest_version": "1.0.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "milestone": "AuscultaForge — First Successful Physical PCG Phantom Proof of Concept | 25 November 2026",
        "classifications": {
            "PROTOTYPE_POC_ACCEPTED": "YES — internal engineering milestone",
            "PHYSICAL_PCG_TRANSMISSION_DEMONSTRATED": "YES — supported by exploratory trial_20261125_095717_275ae8 (1-10s)",
            "DIGITAL_CAPTURE_INTEGRITY": "PASS for successful sessions",
            "STETHOSCOPE_COUPLING_DIAGNOSTIC": "PASS (3/3 taps in session_20261125_083848_02ff521c & session_20261125_100542_a818e843)",
            "OFFICIAL_Q01": "FAIL — startup transient (session_20261125_093843_959d7eb0)",
            "OFFICIAL_P01": "NOT YET ACCEPTED",
            "DIRECT_SILICONE_SIDEQUEST": "INCONCLUSIVE — all-zero I2S captures",
            "CLINICAL_VALIDATION": "NOT CLAIMED",
        },
        "media_publication_policy": "Raw WAVs and CirCor 40058_AV.wav are excluded from public GitHub via .gitignore (privacy/licensing/binary size). Metadata JSONs, Markdown reports, SHA-256 hashes, and derived SVG figures are published.",
        "artifacts": artifacts,
    }
    (LAB_DIR / "EVIDENCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    generate_figures()
    generate_manifest()
    print("Generated SVG figures and EVIDENCE_MANIFEST.json successfully.")
