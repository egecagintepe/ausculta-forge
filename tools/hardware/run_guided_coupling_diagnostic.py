"""Terminal-based guided 10-second STETHOSCOPE_COUPLING_DIAGNOSTIC runner.

Synchronizes visual Turkish instructions (zero audible beeps) to the actual
hardware StartAck callback on COM10 (G2 firmware, source_mode=0, 48 kHz, 10s),
then analyzes local transient peaks and tap-window signal-to-baseline ratios.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "software"))

from pcg_app.wednesday_orchestrator import record_g2_session  # noqa: E402


GUIDED_CUES = [
    (0.0, "0-2s  : SESSİZ KAL (Diyaframa dokunmayın)"),
    (2.0, "2-3s  : DOKUNUŞ 1 (Stetoskop diyaframına 1 hafif dokunuş)"),
    (3.0, "3-4s  : SESSİZ KAL"),
    (4.0, "4-5s  : DOKUNUŞ 2 (Stetoskop diyaframına 1 hafif dokunuş)"),
    (5.0, "5-6s  : SESSİZ KAL"),
    (6.0, "6-7s  : DOKUNUŞ 3 (Stetoskop diyaframına 1 hafif dokunuş)"),
    (7.0, "7-10s : SESSİZ KAL (Kayıt bitene kadar bekleyin)"),
]


def analyze_coupling_wav(wav_path: Path) -> dict[str, Any]:
    """Analyze 20-500 Hz bandpass local transient peaks and 3 tap windows."""
    sr, arr = wavfile.read(str(wav_path))
    x = arr.astype(np.float64)
    if x.ndim > 1:
        x = x[:, 0]
    n = int(len(x))
    rms_fs = float(np.sqrt(np.mean(x ** 2))) if n > 0 else 0.0
    peak_fs = float(np.max(np.abs(x))) if n > 0 else 0.0
    clip_count = int(np.sum(np.abs(x) > 0.98)) if n > 0 else 0

    sos = butter(4, [20.0, min(500.0, sr * 0.45)], btype="bandpass", fs=sr, output="sos")
    y = sosfiltfilt(sos, x)
    bp_rms = float(np.sqrt(np.mean(y ** 2)))
    bp_peak = float(np.max(np.abs(y)))

    # 250ms window profile to surface waveform-derived tap candidates
    w = max(1, sr // 4)
    win_peaks = []
    for i in range(n // w):
        seg = y[i * w : (i + 1) * w]
        win_peaks.append({
            "t_start_s": round(i * 0.25, 2),
            "t_end_s": round((i + 1) * 0.25, 2),
            "bp_peak_fs": round(float(np.max(np.abs(seg))), 6),
            "bp_rms_fs": round(float(np.sqrt(np.mean(seg ** 2))), 6),
        })

    # Silence baseline across [0.5-2.0s, 3.0-4.0s, 5.0-6.0s, 7.0-10.0s] (excludes 0-0.5s I2S turn-on transient)
    silence_rms_vals = []
    silence_peaks = []
    for s0, s1 in [(0.5, 2.0), (3.0, 4.0), (5.0, 6.0), (7.0, 10.0)]:
        i0, i1 = min(n, int(s0 * sr)), min(n, int(s1 * sr))
        seg = y[i0:i1]
        if len(seg) > 0:
            silence_peaks.append(float(np.max(np.abs(seg))))
        for k in range(0, len(seg) - w + 1, w):
            silence_rms_vals.append(float(np.sqrt(np.mean(seg[k : k + w] ** 2))))
    silence_baseline_rms = float(np.median(silence_rms_vals)) if silence_rms_vals else 0.0
    silence_max_peak = float(np.max(silence_peaks)) if silence_peaks else 0.0

    # Tap window comparison
    tap_windows = []
    all_detected = True
    for label, t0, t1 in [("DOKUNUŞ 1", 2.0, 3.0), ("DOKUNUŞ 2", 4.0, 5.0), ("DOKUNUŞ 3", 6.0, 7.0)]:
        i0, i1 = min(n, int(t0 * sr)), min(n, int(t1 * sr))
        seg = y[i0:i1]
        l_peak = float(np.max(np.abs(seg))) if len(seg) > 0 else 0.0
        l_rms = float(np.sqrt(np.mean(seg ** 2))) if len(seg) > 0 else 0.0
        ratio = l_peak / max(silence_baseline_rms, 1e-9)
        vs_silence_peak = l_peak / max(silence_max_peak, 1e-9)
        detected = bool(ratio >= 4.0 and vs_silence_peak >= 2.0 and l_peak >= 0.02 and n >= int(t1 * sr))
        if not detected:
            all_detected = False
        tap_windows.append({
            "label": label,
            "start_s": t0,
            "end_s": t1,
            "local_peak_fs": round(l_peak, 6),
            "local_rms_fs": round(l_rms, 6),
            "peak_to_baseline_ratio": round(ratio, 2),
            "peak_to_silence_peak_ratio": round(vs_silence_peak, 2),
            "detected": detected,
        })

    # Top 5 waveform-derived transient candidates across 0.5-10s
    post_turnon = [wp for wp in win_peaks if wp["t_start_s"] >= 0.5]
    top_candidates = sorted(post_turnon, key=lambda d: d["bp_peak_fs"], reverse=True)[:5]

    return {
        "sample_rate_hz": int(sr),
        "total_samples": n,
        "rms_fs": round(rms_fs, 6),
        "peak_fs": round(peak_fs, 6),
        "clipping_count": clip_count,
        "band_20_500_rms_fs": round(bp_rms, 6),
        "band_20_500_peak_fs": round(bp_peak, 6),
        "silence_baseline_rms_fs": round(silence_baseline_rms, 6),
        "silence_max_peak_fs": round(silence_max_peak, 6),
        "tap_windows": tap_windows,
        "top_transient_candidates": top_candidates,
        "three_taps_detected": all_detected,
        "coupling_verified": bool(all_detected and silence_baseline_rms < 0.02 and n >= 480000),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Guided 10s STETHOSCOPE_COUPLING_DIAGNOSTIC runner")
    parser.add_argument("--port", default="COM10", help="ESP32-S3 USB CDC COM port (default: COM10)")
    args = parser.parse_args()

    out_dir = REPO_ROOT / "experiments" / "phantom" / "quiet_baselines"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================", flush=True)
    print("  STETHOSCOPE_COUPLING_DIAGNOSTIC (Resmî Q01/P01 DEĞİLDİR)", flush=True)
    print(f"  Port: {args.port} | source_mode=0 (INMP441) | 48 kHz | 10s", flush=True)
    print("  Sesli uyarı YOK — Yalnızca görsel terminal komutları", flush=True)
    print("============================================================", flush=True)
    print("[DURUM] Kayıt başlatılıyor / Donanım hazırlanıyor (HELLO + START)...", flush=True)

    ack_info: dict[str, Any] = {"ack_monotonic": None, "ack_utc": None, "cue_thread": None}
    stop_cues = threading.Event()

    def _run_cues(t0_mono: float) -> None:
        for offset_s, text in GUIDED_CUES:
            if stop_cues.is_set():
                return
            remaining = (t0_mono + offset_s) - time.monotonic()
            if remaining > 0:
                if stop_cues.wait(timeout=remaining):
                    return
            actual_dt = time.monotonic() - t0_mono
            print(f"  >>> [t={actual_dt:5.2f}s] {text}", flush=True)

    def _on_capture_started() -> None:
        t0 = time.monotonic()
        ack_info["ack_monotonic"] = t0
        ack_info["ack_utc"] = datetime.now(timezone.utc).isoformat()
        print(f"[ONAY] Donanım StartAck alındı ({ack_info['ack_utc']}). Zamanlama ~±100ms yaklaşıktır.", flush=True)
        th = threading.Thread(target=_run_cues, args=(t0,), daemon=True)
        ack_info["cue_thread"] = th
        th.start()

    try:
        result = record_g2_session(
            root=REPO_ROOT,
            port=args.port,
            role="STETHOSCOPE_COUPLING_DIAGNOSTIC",
            target_samples=480000,
            capture_timeout_s=25.0,
            sessions_dir=out_dir,
            on_capture_started=_on_capture_started,
        )
    finally:
        stop_cues.set()
        if ack_info["cue_thread"] is not None:
            ack_info["cue_thread"].join(timeout=1.0)

    print("\n[DURUM] Kayıt tamamlandı / Analiz başlatıldı...", flush=True)
    wav_path = Path(result["raw_wav_path"])
    analysis = analyze_coupling_wav(wav_path)

    report = {
        "experiment_type": "STETHOSCOPE_COUPLING_DIAGNOSTIC",
        "not_official_q01_or_p01": True,
        "session_id": result["session_id"],
        "wav_path": str(wav_path),
        "raw_wav_sha256": result["raw_wav_sha256"],
        "ack_timestamp_utc": ack_info["ack_utc"],
        "timing_uncertainty_note": "Cues synchronized to host receipt of hardware StartAck; USB/OS scheduling uncertainty ~±50-100ms.",
        "crc_failures": result["crc_failures"],
        "dropped_frames": result["dropped_frames"],
        "analysis": analysis,
    }
    report_path = wav_path.parent / "coupling_diagnostic_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n============================================================", flush=True)
    print("  STETHOSCOPE_COUPLING_DIAGNOSTIC — SONUÇ RAPORU", flush=True)
    print("============================================================", flush=True)
    print(f"  Session ID    : {result['session_id']}", flush=True)
    print(f"  WAV Dosyası   : {wav_path}", flush=True)
    print(f"  WAV SHA-256   : {result['raw_wav_sha256']}", flush=True)
    print(f"  Örnek Sayısı  : {analysis['total_samples']} @ {analysis['sample_rate_hz']} Hz", flush=True)
    print(f"  Ham RMS / Peak: {analysis['rms_fs']:.6f} FS / {analysis['peak_fs']:.6f} FS", flush=True)
    print(f"  20-500 Hz RMS : {analysis['band_20_500_rms_fs']:.6f} FS (Peak: {analysis['band_20_500_peak_fs']:.6f} FS)", flush=True)
    print(f"  Clipping      : {analysis['clipping_count']} örnek (>0.98 FS)", flush=True)
    print(f"  Kayıp Paket   : {result['dropped_frames']} | CRC Hatası: {result['crc_failures']}", flush=True)
    print(f"  Sessiz Taban  : {analysis['silence_baseline_rms_fs']:.6f} FS RMS (0.5-2s, 3-4s, 5-6s, 7-10s medyan)", flush=True)
    print("\n  Pencere Bazlı Dokunuş Analizi (20-500 Hz):", flush=True)
    for tw in analysis["tap_windows"]:
        status = "ALGILANDI" if tw["detected"] else "ALGILANAMADI"
        print(
            f"    - {tw['label']} ({tw['start_s']:.0f}-{tw['end_s']:.0f}s): "
            f"Peak={tw['local_peak_fs']:.5f} FS, RMS={tw['local_rms_fs']:.5f} FS, "
            f"Oran={tw['peak_to_baseline_ratio']:.1f}x -> {status}",
            flush=True,
        )
    print("\n  Waveform Türevli En Yüksek 5 Aday (0.5-10s, 250ms pencereler):", flush=True)
    for cand in analysis["top_transient_candidates"]:
        print(
            f"    - [{cand['t_start_s']:.2f}-{cand['t_end_s']:.2f}s] "
            f"Peak={cand['bp_peak_fs']:.5f} FS, RMS={cand['bp_rms_fs']:.5f} FS",
            flush=True,
        )
    verdict = "COUPLING_VERIFIED (3/3 ayırt edilebilir dokunuş algılandı)" if analysis["coupling_verified"] else "COUPLING_NOT_VERIFIED (3 ayırt edilebilir dokunuş doğrulanamadı)"
    print(f"\n  KARAR: {verdict}", flush=True)
    print("  NOT  : Bu kayıt STETHOSCOPE_COUPLING_DIAGNOSTIC olup resmî Q01/P01 değildir.", flush=True)
    print("============================================================", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
