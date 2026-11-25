"""AuscultaForge — Autonomous Wednesday Lab Orchestrator (2026-11-18).

Coordinates safe, resumable, low-intervention physical bring-up for non-software
operators (Kaan & Ozan):
  1. Preflight + SHA-256 verification of staged/rollback manifests
  2. Espressif USB CDC port discovery (rejects Intel/Bluetooth/unrelated COMs)
  3. Canonical HELLO verification
  4. Resumable deterministic G1 regression (source_mode=1, 480k samples, 0 drops)
  5. Human-gated H0 physical inspection + G2 authorization check (never auto-flash)
  6. Automated 10s quiet + 10s controlled-stimulus G2 captures (source_mode=0)
  7. Read-only single return ZIP creation (+ optional safe GitHub evidence drop)
"""

from __future__ import annotations

from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Optional

import numpy as np
from scipy.io import wavfile

from pcg_core.metrology.models import MeasurementStatus, SensorConfiguration
from pcg_core.metrology.workflows import compute_active_quiescent_snr
from pcg_core.recording import SessionRecorder, verify_session_integrity
from pcg_core.scientific.signal_quality import assess_signal_quality

from .canonical.acceptance import assess_g1
from .canonical.codec import DecodedPacket, MSG_TYPE_AUDIO_DATA
from .canonical.engine import CanonicalSessionEngine
from .device_runtime import AcquisitionProfile, DeviceSamplePacket, packet_to_sample_block
from .diagnostics.flight_recorder import get_flight_recorder
from .diagnostics.usb_doctor import UsbDiscoveryDoctor
from .hardware_workflow import (
    ROOT,
    _resolve_and_verify_manifest_artifacts,
    authorize_g2_candidate,
    export_evidence,
    git_info,
    physical_g1,
    preflight,
    qualify_recording,
    sha256,
    utc_now,
    validate_release,
    write_json,
)

SCHEMA_VERSION = "1.0.0"
G2_CAPTURE_TARGET_SAMPLES = 480000
MIN_STIMULUS_VS_QUIET_SNR_20_500HZ_DB = 6.0
MIN_STIMULUS_TO_QUIET_RMS_RATIO = 1.8
MIN_STIMULUS_TO_QUIET_PEAK_RATIO = 1.5
MAX_STIMULUS_SATURATION_FRACTION = 0.01
DEFAULT_STATE_REL = Path("experiments/hardware/wednesday_20261118_state.json")
DEFAULT_ROLLBACK_MANIFEST_REL = Path("firmware/g1_rollback_backup/firmware_build_manifest.json")
DEFAULT_G1_MANIFEST_REL = Path("firmware/releases/g1_release_20261117/firmware_build_manifest.json")
DEFAULT_G2_MANIFEST_REL = Path("firmware/releases/g2_candidate_20261117/firmware_build_manifest.json")
TEAM_EVIDENCE_DIR_REL = Path("experiments/hardware/team_2026-11-18")

STAGE_ORDER = (
    "preflight_and_hashes",
    "usb_discovery",
    "hello_handshake",
    "g1_regression",
    "g2_physical_gate",
    "g2_quiet_capture",
    "g2_stimulus_capture",
    "return_package",
)

OPERATOR_CHECKLIST_TR = """=== CARSAMBA 18 KASIM — TEK SEFERDE FIZIKSEL KONTROL (H0) ===
Devam etmeden once Kaan & Ozan asagidaki 3 kaniti hazirlamalidir:
1. FOTOGRAFLAR (on + arka yuz):
   - ESP32-S3 (YD-ESP32-23 / N16R8) karti + pin yazilari net gorunur.
   - INMP441 karti + 6 lehim bacagi (VDD, GND, SCK, WS, SD, L/R) + ALT AKUSTIK DELIK tamamen acik.
2. MULTIMETRE OLCUMU (Mikrofon TAKILI DEGILKEN, tek USB kablosu ile):
   - ESP32 3V3 - GND arasi gerilim: _____ V (Guvenli aralik: 3.15 - 3.45 V, ASLA 5V degil)
   - Multimetre modeli / no: _____
3. GUC KESIKKEN (USB CIKARILMIS) KISA DEVRE & SUREKLILIK:
   - INMP441 VDD - GND kisa devre YOK (Open / >MOhm).
   - Sureklilik: VDD->3V3, GND->GND, SCK->GPIO4, WS->GPIO5, SD->GPIO6, L/R->GND (LEFT slot).

Hazir olunca yetkilendirme komutu (asla otomatik verilmez):
  .\\.venv\\Scripts\\python.exe tools/hardware/bringup.py authorize-g2 --bclk 4 --ws 5 --din 6 --slot left --vdd-volts <OLCULEN_V> --operator "Kaan & Ozan" --multimeter "<OLCU_ALETI>"
Ardindan ROM Bootloader modunda tek insan onayli flash:
  .\\.venv\\Scripts\\python.exe tools/hardware/bringup.py flash --port <COM_ROM> --manifest firmware/releases/g2_candidate_20261117/firmware_build_manifest.json"""


class G2CaptureValidationError(RuntimeError):
    """Raised when a G2 recording fails physical silence/drop/CRC acceptance rules."""

    def __init__(self, reason_code: str, message: str, summary: dict[str, Any]) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.summary = summary


def _load_pack_return_module(root: Path):
    mod_path = (root / "tools/hardware/pack_lab_return.py").resolve()
    spec = importlib.util.spec_from_file_location("pack_lab_return", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load pack_lab_return module at {mod_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_stages() -> dict[str, dict[str, Any]]:
    return {
        name: {"status": "PENDING", "updated_utc": None, "detail": None}
        for name in STAGE_ORDER
    }


def load_or_init_state(state_path: Path, root: Path) -> dict[str, Any]:
    """Load persistent Wednesday session state if present, else initialize a clean skeleton."""
    root = Path(root).resolve()
    if state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                stages = _default_stages()
                for k, v in (loaded.get("stages") or {}).items():
                    if k in stages and isinstance(v, dict):
                        stages[k] = v
                loaded["stages"] = stages
                loaded["updated_utc"] = utc_now()
                loaded["repo_root"] = str(root)
                loaded["git_info"] = git_info(root)
                return loaded
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "repo_root": str(root),
        "git_info": git_info(root),
        "selected_port": None,
        "device_identity": None,
        "stages": _default_stages(),
        "operator_prompt_checklist": OPERATOR_CHECKLIST_TR,
        "latest_return_zip": None,
        "github_evidence_drop": {"status": "NOT_REQUESTED", "uploaded": False},
    }


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state["updated_utc"] = utc_now()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(state_path, state)


def _set_stage(
    state_path: Path,
    state: dict[str, Any],
    stage: str,
    status: str,
    detail: Any,
) -> None:
    state["stages"][stage] = {
        "status": status,
        "updated_utc": utc_now(),
        "detail": detail,
    }
    save_state(state_path, state)


def verify_manifests(
    root: Path,
    g1_manifest_path: Optional[Path] = None,
    g2_manifest_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Verify SHA-256 integrity of rollback, staged G1, and G2 candidate manifests."""
    rollback_p = (root / DEFAULT_ROLLBACK_MANIFEST_REL).resolve()
    g1_p = (g1_manifest_path or (root / DEFAULT_G1_MANIFEST_REL)).resolve()
    g2_p = (g2_manifest_path or (root / DEFAULT_G2_MANIFEST_REL)).resolve()

    if "g2_compile_check" in g1_p.parts or "g2_compile_check" in g2_p.parts:
        raise ValueError("FORBIDDEN_MANIFEST: g2_compile_check is never allowed as a hardware candidate or flash target.")

    rb_data = validate_release(rollback_p)
    g1_data = validate_release(g1_p)

    if not g2_p.is_file():
        raise FileNotFoundError(f"G2 candidate manifest missing: {g2_p}")
    g2_raw = json.loads(g2_p.read_text(encoding="utf-8"))
    if g2_raw.get("target") != "esp32s3" or g2_raw.get("idf_version") != g1_data.get("idf_version"):
        raise ValueError("G2 manifest target or ESP-IDF version mismatch.")
    base, _ = _resolve_and_verify_manifest_artifacts(g2_p, dict(g2_raw))

    return {
        "g1_rollback_backup": {
            "path": str(rollback_p),
            "status": rb_data["status"],
            "firmware_version": rb_data["firmware_version"],
            "hashes_verified": True,
        },
        "g1_manifest": {
            "path": str(g1_p),
            "status": g1_data["status"],
            "firmware_version": g1_data["firmware_version"],
            "hashes_verified": True,
        },
        "g2_manifest": {
            "path": str(g2_p),
            "build_directory": str(base),
            "status": g2_raw.get("status"),
            "firmware_version": g2_raw.get("firmware_version"),
            "hashes_verified": True,
            "authorized_for_flash": bool(
                g2_raw.get("status") == "COMPILED_BUT_NOT_FLASHED" and g2_raw.get("physical_attestation")
            ),
            "physical_attestation": g2_raw.get("physical_attestation"),
        },
    }


def select_espressif_port(doctor: UsbDiscoveryDoctor, requested_port: Optional[str] = None) -> dict[str, Any]:
    """Discover USB CDC port safely; refuse simulated or non-Espressif ports."""
    scanned = [p.to_dict() for p in doctor.scan_ports()]
    espressif = [p for p in scanned if p.get("is_espressif_candidate")]

    if requested_port:
        norm = requested_port.strip()
        if norm.upper() in ("SIMULATED", "SIMULATED_ESP32_S3", "LOOPBACK"):
            raise ValueError("WEDNESDAY_PHYSICAL_ONLY: Simulated ports are not allowed in physical orchestration.")
        match = next((p for p in scanned if p["port_name"].casefold() == norm.casefold()), None)
        if match is None:
            return {
                "selected": None,
                "reason": f"Requested port '{norm}' not found among active Windows ports.",
                "scanned_ports": scanned,
            }
        if not match.get("is_espressif_candidate"):
            raise ValueError(
                f"REFUSED_NON_ESPRESSIF_PORT: '{match['port_name']}' ({match.get('description')}) is not an Espressif USB device."
            )
        return {"selected": match, "scanned_ports": scanned, "reason": "Explicitly selected Espressif port"}

    if len(espressif) == 1:
        return {"selected": espressif[0], "scanned_ports": scanned, "reason": "Unique Espressif USB candidate detected"}
    if len(espressif) == 0:
        return {
            "selected": None,
            "reason": "NO_ESPRESSIF_PORT: Hiç Espressif USB CDC portu bulunamadi. Tek veri kablosunu USB portuna takip tekrar calistirin.",
            "scanned_ports": scanned,
        }
    return {
        "selected": None,
        "reason": "AMBIGUOUS_PORTS: Birden fazla Espressif portu gorundu; --port COMx ile dogru portu secin.",
        "scanned_ports": scanned,
    }


def run_hello_handshake(
    port: str,
    engine_factory: Callable[..., Any] = CanonicalSessionEngine,
    timeout_s: float = 4.0,
) -> dict[str, Any]:
    """Perform non-destructive HELLO handshake and inspect capabilities."""
    engine = engine_factory(diagnostic_journal=get_flight_recorder())
    try:
        caps = engine.connect(port, timeout_s=timeout_s).result(timeout=timeout_s + 2.0)
        if getattr(engine, "is_simulated", False):
            raise RuntimeError("REFUSED_SIMULATED_ENGINE: Physical transport expected.")
        return {
            "port": port,
            "protocol_version": f"{caps.protocol_version_major}.{caps.protocol_version_minor}",
            "firmware_version": f"{caps.firmware_version_major}.{caps.firmware_version_minor}.{caps.firmware_version_patch}",
            "device_uid_low": f"0x{caps.device_uid_low:08x}",
            "hardware_sample_rate_hz": int(caps.hardware_sample_rate_hz),
            "max_frame_samples": int(caps.max_frame_samples),
            "supported_profiles_mask": int(caps.supported_profiles_mask),
            "supported_encodings_mask": int(caps.supported_encodings_mask),
        }
    finally:
        try:
            engine.disconnect(timeout_s=2.0).result(timeout=3.0)
        except Exception:
            pass


def _run_g1_via_custom_engine(
    engine_factory: Callable[..., Any],
    port: str,
    output_root: Path,
    board_identity: Optional[dict[str, Any]],
    firmware_manifest: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    """Run G1 regression using an injected engine factory (used in hardware-free fault tests)."""
    engine = engine_factory(diagnostic_journal=get_flight_recorder())
    error: Optional[str] = None
    try:
        caps = engine.connect(port, timeout_s=4.0).result(timeout=6.0)
        reported = f"{caps.firmware_version_major}.{caps.firmware_version_minor}.{caps.firmware_version_patch}"
        if firmware_manifest and reported != firmware_manifest["firmware_version"]:
            raise RuntimeError(
                f"Connected firmware {reported} differs from G1 manifest {firmware_manifest['firmware_version']}"
            )
        engine.start_acquisition(target_samples=480000, source_mode=1).result(timeout=5.0)
        deadline = time.monotonic() + 15.0
        while engine.session.host_samples_accepted < 480000:
            if engine.state.value != "STREAMING":
                raise RuntimeError(f"G1 acquisition interrupted: {engine.state.value}")
            if time.monotonic() >= deadline:
                raise TimeoutError("G1 480000 samples not received before deadline")
            time.sleep(0.005)
        engine.stop_acquisition().result(timeout=5.0)
    except Exception as exc:
        error = str(exc)
        engine.session.error_log.append(error)
    try:
        engine.last_g1_evidence = assess_g1(engine)
        if error:
            engine.last_g1_evidence["failure_reasons"].append(error)
        bundle_dir = export_evidence(engine, output_root, board_identity, firmware_manifest)
        return engine.last_g1_evidence, bundle_dir
    finally:
        try:
            engine.disconnect(timeout_s=2.0).result(timeout=3.0)
        except Exception:
            pass


def _summarize_capture_session(
    session_dir: Path,
    role: str,
    crc_failures: int,
    dropped_frames: int,
    telemetry_dict: dict[str, Any],
) -> dict[str, Any]:
    qual = qualify_recording(session_dir)
    meta = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
    rate, samples = wavfile.read(session_dir / meta["raw_wav_relpath"])
    sig_quality = assess_signal_quality(samples, rate).to_dict()

    freqs = np.asarray(qual["welch"]["frequencies_hz"], dtype=np.float64)
    power = np.asarray(qual["welch"]["power_fs2_per_hz"], dtype=np.float64)
    in_band = (freqs >= 20.0) & (freqs <= 500.0)
    peak_hz = float(freqs[in_band][int(np.argmax(power[in_band]))]) if np.any(in_band) and len(power[in_band]) else 0.0
    trapz_fn = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    band_power = float(trapz_fn(power[in_band], freqs[in_band])) if np.sum(in_band) >= 2 else 0.0

    return {
        "role": role,
        "session_id": meta["session_id"],
        "session_dir": str(session_dir),
        "raw_wav_path": str((session_dir / meta["raw_wav_relpath"]).resolve()),
        "raw_wav_sha256": qual["raw_sha256"],
        "source_mode": 0,
        "acquisition_origin": "physical_i2s_inmp441",
        "sample_rate_hz": int(qual["nominal_sample_rate_hz"]),
        "samples": int(qual["samples"]),
        "duration_s": float(qual["duration_from_count_s"]),
        "constant_zero": bool(qual["constant_zero"]),
        "constant_signal": bool(qual["constant_signal"]),
        "rms_fs": float(qual["rms_fs"]),
        "peak_fs": float(qual["peak_fs"]),
        "dc_fs": float(qual["dc_fs"]),
        "saturation_fraction": float(qual["saturation_fraction"]),
        "clipping_detected": bool(sig_quality["clipping"]["clipping_detected"]),
        "mains_hum_prominent": bool(sig_quality["spectral_contamination"]["mains_hum_prominent"]),
        "welch_peak_freq_hz_20_500": round(peak_hz, 3),
        "welch_band_power_20_500": band_power,
        "crc_failures": int(crc_failures),
        "dropped_frames": int(dropped_frames),
        "firmware_telemetry": telemetry_dict,
    }


def record_g2_session(
    root: Path,
    port: str,
    role: str,
    target_samples: int = G2_CAPTURE_TARGET_SAMPLES,
    capture_timeout_s: float = 25.0,
    sessions_dir: Optional[Path] = None,
    engine_factory: Callable[..., Any] = CanonicalSessionEngine,
    on_capture_started: Optional[Callable[[], None]] = None,
) -> dict[str, Any]:
    """Record a bounded physical source_mode=0 (INMP441) WAV session with strict silence/loss validation."""
    if target_samples <= 0 or (target_samples % 256) != 0:
        raise ValueError(f"G2 target_samples must be positive and a multiple of 256, got {target_samples}")

    out_sessions = (sessions_dir or (root / "experiments/sessions")).resolve()
    out_sessions.mkdir(parents=True, exist_ok=True)
    recorder = SessionRecorder(output_dir=out_sessions, wav_format="float32")
    profile = AcquisitionProfile()

    disconnect_event = threading.Event()
    disconnect_reason: list[str] = []
    ingest_stats = {"crc_failures": 0, "packets": 0, "samples": 0}
    last_seq: Optional[int] = None
    expected_gaps = 0

    def _on_audio(pkt: DecodedPacket) -> bool:
        nonlocal last_seq, expected_gaps
        if pkt.msg_type != MSG_TYPE_AUDIO_DATA:
            return True
        if not pkt.crc_ok:
            ingest_stats["crc_failures"] += 1
            return False
        if last_seq is not None and pkt.sequence_id != ((last_seq + 1) & 0xFFFFFFFF):
            expected_gaps += 1
        last_seq = pkt.sequence_id
        dsp = DeviceSamplePacket(
            sequence=pkt.sequence_id,
            timestamp_s=float(pkt.timestamp_us) / 1_000_000.0,
            raw_samples=pkt.raw_samples,
            flags=pkt.flags,
            crc_ok=pkt.crc_ok,
            meaningful_bits=24,
            sample_rate_hz=pkt.sample_rate_hz or 48000,
        )
        block = packet_to_sample_block(dsp, sample_rate_hz=dsp.sample_rate_hz, profile=profile)
        if recorder.is_recording:
            recorder.record_block(block)
        ingest_stats["packets"] += 1
        ingest_stats["samples"] += len(block.samples)
        return True

    def _on_disc(reason: str) -> None:
        disconnect_reason.append(reason)
        disconnect_event.set()

    engine = engine_factory(
        diagnostic_journal=get_flight_recorder(),
        on_audio_packet=_on_audio,
        on_disconnect=_on_disc,
    )
    session_id: Optional[str] = None
    term_reason = "completed"
    telem_dict: dict[str, Any] = {}
    stream_err: Optional[str] = None

    try:
        caps = engine.connect(port, timeout_s=4.0).result(timeout=6.0)
        if getattr(engine, "is_simulated", False):
            raise RuntimeError("REFUSED_SIMULATED_ENGINE: G2 live capture requires physical hardware or explicit mock.")
        fw_ver = f"{caps.firmware_version_major}.{caps.firmware_version_minor}.{caps.firmware_version_patch}"
        dev_uid = f"0x{caps.device_uid_low:08x}"

        session_id = recorder.start(
            source=f"Physical USB INMP441 G2 ({role}) on {port}",
            acquisition_mode="hardware",
            device_info={
                "port": port,
                "device_id": f"ESP32-S3 (UID: {dev_uid})",
                "firmware_version": fw_ver,
                "source_mode": 0,
            },
            wire_format="signed_pcm_24bit_in_32bit_slot",
            processing_profile={
                "filter_preset": "none_raw",
                "acquisition_origin": "physical_i2s_unqualified",
                "source_mode": 0,
                "capture_role": role,
            },
        )

        try:
            engine.start_acquisition(
                target_samples=target_samples,
                source_mode=0,
                sample_rate_hz=48000,
                encoding=1,
                channels=1,
                timeout_s=4.0,
            ).result(timeout=6.0)
            if on_capture_started is not None:
                try:
                    on_capture_started()
                except Exception as _cb_err:
                    get_flight_recorder().record(
                        severity="ERROR",
                        subsystem="G2_ACQUISITION",
                        event_type="ON_CAPTURE_STARTED_CALLBACK_ERROR",
                        message=f"on_capture_started callback raised: {_cb_err}",
                    )
                    raise RuntimeError(f"ON_CAPTURE_STARTED_CALLBACK_FAILED: {_cb_err}") from _cb_err
        except Exception as exc:
            msg = str(exc)
            if "Unsupported source" in msg or "0x0002" in msg:
                raise RuntimeError(
                    "G2_MODE_NOT_SUPPORTED_ON_BOARD: Connected firmware rejected source_mode=0 (live I2S). Flash authorized G2 firmware first."
                ) from exc
            raise

        deadline = time.monotonic() + capture_timeout_s
        while ingest_stats["samples"] < target_samples:
            if disconnect_event.is_set():
                term_reason = "device_disconnected"
                stream_err = f"USB disconnected mid-G2 capture: {'; '.join(disconnect_reason) or 'unknown'}"
                break
            if engine.state.value not in ("STREAMING", "COMPLETE"):
                term_reason = "stream_aborted"
                stream_err = f"Stream entered unexpected state {engine.state.value}: {engine.session.error_log}"
                break
            if time.monotonic() >= deadline:
                term_reason = "timeout"
                stream_err = f"Timed out waiting for {target_samples} G2 samples (got {ingest_stats['samples']})"
                break
            time.sleep(0.01)

        try:
            telem = engine.stop_acquisition(timeout_s=4.0).result(timeout=6.0)
            telem_dict = {
                "generated_samples": int(telem.generated_samples),
                "dropped_samples": int(telem.dropped_samples),
                "dma_overflows": int(telem.dma_overflow_events),
                "ring_overflows": int(telem.ring_overflow_events),
                "stop_reason": int(telem.stop_reason),
            }
        except Exception as exc:
            if stream_err is None:
                stream_err = f"STOP handshake failed: {exc}"
    finally:
        if recorder.is_recording:
            if recorder.total_samples > 0:
                recorder.stop(termination_reason=term_reason)
            else:
                # Leave session marker incomplete when zero samples arrived so it is auditably marked aborted.
                recorder._active = False
        try:
            engine.disconnect(timeout_s=2.0).result(timeout=3.0)
        except Exception:
            pass

    if session_id is None:
        raise RuntimeError(stream_err or "G2 capture failed before creating session")

    session_dir = out_sessions / session_id
    integrity = verify_session_integrity(session_id, out_sessions)
    if stream_err or not integrity.get("is_valid"):
        err_summary = {
            "role": role,
            "session_id": session_id,
            "session_dir": str(session_dir),
            "samples_received": ingest_stats["samples"],
            "crc_failures": ingest_stats["crc_failures"] + engine.session.decoder.total_frames_corrupted,
            "sequence_gaps": engine.session.decoder.total_sequence_gaps + expected_gaps,
            "integrity": integrity,
            "error": stream_err or f"Session integrity failed: {integrity}",
        }
        raise G2CaptureValidationError(
            "G2_STREAM_INTERRUPTED_OR_INCOMPLETE",
            err_summary["error"],
            err_summary,
        )

    total_crc = ingest_stats["crc_failures"] + int(engine.session.decoder.total_frames_corrupted)
    dropped_frames = int(engine.session.decoder.total_sequence_gaps) + expected_gaps
    summary = _summarize_capture_session(session_dir, role, total_crc, dropped_frames, telem_dict)

    # Distinguish proven post-target DMA drain from in-stream data loss:
    # Firmware generates 256 samples beyond target (e.g. 480256) due to ring/DMA chunk boundaries.
    # Exactly 256 dropped samples with complete, consistent telemetry (0 CRC errors, 0 frame sequence gaps,
    # 0 buffer overflows, and generated_samples >= target_samples + 256) constitutes proven post-target drain.
    required_telem_keys = ("dropped_samples", "generated_samples", "dma_overflows", "ring_overflows")
    if any(telem_dict.get(k) is None for k in required_telem_keys):
        raise G2CaptureValidationError(
            "G2_MISSING_FIRMWARE_TELEMETRY",
            f"G2 {role} capture missing required firmware telemetry fields: {telem_dict}",
            summary,
        )

    fw_dropped = int(telem_dict["dropped_samples"])
    fw_generated = int(telem_dict["generated_samples"])
    dma_overflows = int(telem_dict["dma_overflows"])
    ring_overflows = int(telem_dict["ring_overflows"])

    is_proven_post_drain = (
        summary["samples"] >= target_samples
        and dropped_frames == 0
        and total_crc == 0
        and dma_overflows == 0
        and ring_overflows == 0
        and fw_dropped == 256
        and fw_generated >= target_samples + 256
    )

    if is_proven_post_drain:
        in_stream_dropped = 0
        post_drain = 256
    else:
        in_stream_dropped = fw_dropped
        post_drain = 0

    summary["in_stream_dropped_samples"] = in_stream_dropped
    summary["post_target_drained_samples"] = post_drain

    if summary["constant_zero"] or summary["constant_signal"]:
        raise G2CaptureValidationError(
            "DIGITAL_SILENCE_OR_CONSTANT_SIGNAL",
            f"DIGITAL_SILENCE_OR_CONSTANT_SIGNAL: G2 {role} capture produced constant_zero={summary['constant_zero']}, constant_signal={summary['constant_signal']}. Never claiming PASS on silent/constant I2S data; check INMP441 VDD (3.3V), GND, L/R slot, SCK/WS/SD, and solder joints.",
            summary,
        )
    if summary["samples"] < target_samples or in_stream_dropped > 0 or total_crc > 0 or dropped_frames > 0:
        raise G2CaptureValidationError(
            "G2_CAPTURE_INTEGRITY_FAILED",
            f"G2 {role} capture integrity failed: samples={summary['samples']}/{target_samples}, in_stream_dropped={in_stream_dropped}, post_drain={post_drain}, crc_errors={total_crc}, dropped_frames={dropped_frames}.",
            summary,
        )

    return summary


def evaluate_g2_stimulus_separation(
    quiet_summary: Optional[dict[str, Any]],
    stimulus_summary: Optional[dict[str, Any]],
    snr_20_500_db: Optional[float],
) -> dict[str, Any]:
    """Verify controlled G2 stimulus is meaningfully separable from quiet room noise.

    Returns verdict='PASSED' only when all acoustic separation criteria pass;
    otherwise returns verdict='INCONCLUSIVE' with explicit unmet thresholds.
    """
    thresholds = {
        "min_snr_20_500hz_db": MIN_STIMULUS_VS_QUIET_SNR_20_500HZ_DB,
        "min_fullband_rms_ratio": MIN_STIMULUS_TO_QUIET_RMS_RATIO,
        "min_peak_ratio": MIN_STIMULUS_TO_QUIET_PEAK_RATIO,
        "max_stimulus_saturation_fraction": MAX_STIMULUS_SATURATION_FRACTION,
    }
    if not quiet_summary or not stimulus_summary:
        return {
            "verdict": "INCONCLUSIVE",
            "thresholds": thresholds,
            "observed": {},
            "criteria": {},
            "reasons": ["Missing quiet or stimulus G2 capture summary."],
        }

    q_rms = float(quiet_summary.get("rms_fs") or 0.0)
    s_rms = float(stimulus_summary.get("rms_fs") or 0.0)
    q_peak = float(quiet_summary.get("peak_fs") or 0.0)
    s_peak = float(stimulus_summary.get("peak_fs") or 0.0)
    sat = float(stimulus_summary.get("saturation_fraction") or 0.0)

    rms_ratio = (s_rms / q_rms) if q_rms > 1e-12 else (float("inf") if s_rms > 1e-12 else 0.0)
    peak_ratio = (s_peak / q_peak) if q_peak > 1e-12 else (float("inf") if s_peak > 1e-12 else 0.0)

    criteria = {
        "distinct_wav_sha256": stimulus_summary.get("raw_wav_sha256") != quiet_summary.get("raw_wav_sha256"),
        "snr_20_500hz_db_min_6db": (snr_20_500_db is not None) and (float(snr_20_500_db) >= MIN_STIMULUS_VS_QUIET_SNR_20_500HZ_DB),
        "fullband_rms_ratio_min_1_8x": rms_ratio >= MIN_STIMULUS_TO_QUIET_RMS_RATIO,
        "peak_ratio_min_1_5x": peak_ratio >= MIN_STIMULUS_TO_QUIET_PEAK_RATIO,
        "no_excessive_saturation": sat <= MAX_STIMULUS_SATURATION_FRACTION,
    }

    reasons: list[str] = []
    if not criteria["distinct_wav_sha256"]:
        reasons.append("Quiet and stimulus WAV SHA-256 digests are identical.")
    if not criteria["snr_20_500hz_db_min_6db"]:
        reasons.append(
            f"20-500 Hz stimulus-to-quiet SNR {snr_20_500_db} dB < {MIN_STIMULUS_VS_QUIET_SNR_20_500HZ_DB:.1f} dB minimum."
        )
    if not criteria["fullband_rms_ratio_min_1_8x"]:
        reasons.append(
            f"Wideband RMS ratio {rms_ratio:.3f}x < {MIN_STIMULUS_TO_QUIET_RMS_RATIO:.1f}x minimum."
        )
    if not criteria["peak_ratio_min_1_5x"]:
        reasons.append(
            f"Peak amplitude ratio {peak_ratio:.3f}x < {MIN_STIMULUS_TO_QUIET_PEAK_RATIO:.1f}x minimum."
        )
    if not criteria["no_excessive_saturation"]:
        reasons.append(
            f"Stimulus digital saturation fraction {sat:.4f} exceeds {MAX_STIMULUS_SATURATION_FRACTION:.4f} limit."
        )

    verdict = "PASSED" if all(criteria.values()) else "INCONCLUSIVE"
    return {
        "verdict": verdict,
        "thresholds": thresholds,
        "observed": {
            "snr_20_500hz_db": snr_20_500_db,
            "quiet_rms_fs": round(q_rms, 6),
            "stimulus_rms_fs": round(s_rms, 6),
            "fullband_rms_ratio": round(rms_ratio, 4) if np.isfinite(rms_ratio) else None,
            "quiet_peak_fs": round(q_peak, 6),
            "stimulus_peak_fs": round(s_peak, 6),
            "peak_ratio": round(peak_ratio, 4) if np.isfinite(peak_ratio) else None,
            "stimulus_saturation_fraction": round(sat, 6),
        },
        "criteria": criteria,
        "reasons": reasons,
    }


def write_g2_comparison(
    hw_dir: Path,
    g1_detail: Optional[dict[str, Any]],
    quiet_summary: Optional[dict[str, Any]],
    stimulus_summary: Optional[dict[str, Any]],
) -> tuple[Path, Path, dict[str, Any]]:
    """Compare G2 quiet vs controlled stimulus against G1 determinism provenance."""
    hw_dir.mkdir(parents=True, exist_ok=True)
    snr_20_500_db: Optional[float] = None
    snr_detail: Optional[dict[str, Any]] = None

    if quiet_summary and stimulus_summary:
        q_rate, q_wav = wavfile.read(quiet_summary["raw_wav_path"])
        s_rate, s_wav = wavfile.read(stimulus_summary["raw_wav_path"])
        if q_rate == s_rate and len(q_wav) > 0 and len(s_wav) > 0:
            res = compute_active_quiescent_snr(
                active_signal=s_wav,
                quiescent_signal=q_wav,
                sample_rate_hz=float(q_rate),
                sensor_config=SensorConfiguration("INMP441", "I2S_DIGITAL", "-26 dBFS @ 94 dB SPL"),
                room_acoustic_condition="Wednesday bench quiet capture",
                exciter_drive_level="Controlled bench acoustic stimulus",
                status=MeasurementStatus.BENCH_MEASURED,
            )
            snr_20_500_db = float(res.active_to_quiescent_ratio_db)
            snr_detail = asdict(res)

    acceptance_eval = evaluate_g2_stimulus_separation(quiet_summary, stimulus_summary, snr_20_500_db)

    comp = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": utc_now(),
        "provenance_separation": {
            "g1_source_mode": 1,
            "g1_origin": "physical_deterministic_g1",
            "g2_source_mode": 0,
            "g2_origin": "physical_i2s_inmp441",
        },
        "g1_reference": g1_detail,
        "g2_quiet_capture": quiet_summary,
        "g2_stimulus_capture": stimulus_summary,
        "stimulus_vs_quiet_snr_20_500hz_db": snr_20_500_db,
        "snr_measurement_detail": snr_detail,
        "acceptance_evaluation": acceptance_eval,
    }
    json_path = hw_dir / "wednesday_g2_comparison.json"
    md_path = hw_dir / "wednesday_g2_comparison.md"
    write_json(json_path, comp)

    lines = [
        "# Wednesday 2026-11-18 — G1 / G2 Quiet / G2 Stimulus Summary",
        "",
        f"- **Generated UTC:** `{comp['created_utc']}`",
        f"- **20–500 Hz Stimulus-to-Quiet SNR (dB):** `{snr_20_500_db}`",
        f"- **Stimulus Separation Verdict:** **`{acceptance_eval['verdict']}`**",
        "",
        "| Capture Role | `source_mode` | Provenance | Samples | Duration (s) | RMS (FS) | Peak (FS) | Clipping | Drops / CRC | SHA-256 (Raw WAV) |",
        "| --- | :---: | --- | ---: | ---: | ---: | ---: | :---: | :---: | --- |",
    ]
    for cap in (quiet_summary, stimulus_summary):
        if cap:
            fw_drop = (cap.get("firmware_telemetry") or {}).get("dropped_samples", 0)
            lines.append(
                f"| `{cap['role']}` | `0` | `{cap['acquisition_origin']}` | {cap['samples']} | {cap['duration_s']:.3f} | "
                f"{cap['rms_fs']:.6f} | {cap['peak_fs']:.6f} | `{cap['clipping_detected']}` | "
                f"{fw_drop} / {cap['crc_failures']} | `{cap['raw_wav_sha256'][:16]}...` |"
            )
    if acceptance_eval.get("reasons"):
        lines.append("")
        lines.append("## Unmet Acceptance Criteria")
        for r in acceptance_eval["reasons"]:
            lines.append(f"- {r}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, acceptance_eval


def upload_team_evidence_to_github(
    root: Path,
    files_to_publish: list[Path],
    git_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Safely publish JSON/MD summary evidence ONLY under experiments/hardware/team_2026-11-18/.

    Never prompts for passwords or tokens (GIT_TERMINAL_PROMPT=0), never writes .wav/.zip,
    and falls back cleanly to local ZIP delivery if Git is absent or push fails.
    """
    if not (root / ".git").exists() or not shutil.which("git"):
        return {
            "status": "FALLBACK_LOCAL_ZIP",
            "uploaded": False,
            "reason": "Git checkout or git binary unavailable (GitHub Download ZIP mode); deliver local ZIP instead.",
        }

    dest_dir = (root / TEAM_EVIDENCE_DIR_REL).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for src in files_to_publish:
        if src is not None and Path(src).is_file() and Path(src).suffix.lower() in (".json", ".md"):
            target = dest_dir / Path(src).name
            if Path(src).resolve() != target:
                shutil.copy2(src, target)
            copied.append(target.relative_to(root).as_posix())

    if not copied:
        return {"status": "SKIPPED_NO_SUMMARY_FILES", "uploaded": False, "copied": []}

    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"

    def _run_git(args: list[str]):
        return git_runner(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=25,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

    try:
        add_res = _run_git(["add", "--", *copied])
        if add_res.returncode != 0:
            return {"status": "FALLBACK_LOCAL_ZIP", "uploaded": False, "reason": add_res.stderr or add_res.stdout}

        diff_res = _run_git(["diff", "--cached", "--quiet", "--", *copied])
        if diff_res.returncode != 0:
            commit_res = _run_git(["commit", "-m", "data(wednesday-lab): add 2026-11-18 team hardware summary evidence", "--", *copied])
            if commit_res.returncode != 0:
                return {"status": "FALLBACK_LOCAL_ZIP", "uploaded": False, "reason": commit_res.stderr or commit_res.stdout}

        push_res = _run_git(["push", "origin", "HEAD"])
        if push_res.returncode != 0:
            return {
                "status": "FALLBACK_LOCAL_ZIP",
                "uploaded": False,
                "reason": (push_res.stderr or push_res.stdout or f"git push exited {push_res.returncode}").strip(),
                "staged_local_evidence": copied,
            }
        return {"status": "PUSHED_TEAM_EVIDENCE", "uploaded": True, "files": copied}
    except Exception as exc:
        return {"status": "FALLBACK_LOCAL_ZIP", "uploaded": False, "reason": str(exc), "copied": copied}


def run_wednesday_orchestrator(
    root: Path = ROOT,
    state_path: Optional[Path] = None,
    port: Optional[str] = None,
    g1_manifest_path: Optional[Path] = None,
    g2_manifest_path: Optional[Path] = None,
    operator: str = "Kaan_Ozan",
    notes: str = "",
    force_g1: bool = False,
    authorize_g2_args: Optional[dict[str, Any]] = None,
    run_g2_captures: Optional[bool] = None,
    assume_g2_flashed: bool = False,
    g2_target_samples: int = G2_CAPTURE_TARGET_SAMPLES,
    g2_capture_timeout_s: float = 25.0,
    return_zip_path: Optional[Path] = None,
    push_evidence: bool = False,
    scanner_factory: Callable[[], UsbDiscoveryDoctor] = UsbDiscoveryDoctor,
    engine_factory: Callable[..., Any] = CanonicalSessionEngine,
    physical_g1_runner: Optional[Callable[..., Any]] = None,
    git_runner: Callable[..., Any] = subprocess.run,
    prompt_fn: Callable[[str], str] = input,
    confirm_operator_ready: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    """Execute resumable Wednesday lab bring-up, G1 check, G2 gates/captures, and return ZIP packaging."""
    root = Path(root).resolve()
    resolved_state = (state_path or (root / DEFAULT_STATE_REL)).resolve()
    hw_dir = (root / "experiments/hardware").resolve()
    sessions_dir = (root / "experiments/sessions").resolve()
    hw_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    state = load_or_init_state(resolved_state, root)
    if g1_manifest_path:
        g1_manifest_p = Path(g1_manifest_path).resolve()
    else:
        g1_manifest_p = (root / DEFAULT_G1_MANIFEST_REL).resolve()
    if g2_manifest_path:
        g2_manifest_p = Path(g2_manifest_path).resolve()
    else:
        g2_manifest_p = (root / DEFAULT_G2_MANIFEST_REL).resolve()

    overall_status = "UNKNOWN"
    comparison_json: Optional[Path] = None
    comparison_md: Optional[Path] = None

    try:
        # 1. Preflight & Manifest Hashes
        try:
            pf = preflight(root)
            manifests = verify_manifests(root, g1_manifest_p, g2_manifest_p)
            _set_stage(
                resolved_state,
                state,
                "preflight_and_hashes",
                "PASSED",
                {
                    "git": pf["git"],
                    "checks": pf["checks"],
                    "manifests": manifests,
                },
            )
        except Exception as exc:
            _set_stage(resolved_state, state, "preflight_and_hashes", "FAILED", {"error": str(exc)})
            overall_status = "FAILED"
            return {"status": overall_status, "error": str(exc), "state": state}

        # 2. USB Port Discovery (Strictly rejects non-Espressif / simulated ports)
        try:
            usb_res = select_espressif_port(scanner_factory(), requested_port=port)
            if usb_res["selected"] is None:
                _set_stage(resolved_state, state, "usb_discovery", "WAITING_OPERATOR", usb_res)
                overall_status = "WAITING_OPERATOR"
                return {"status": overall_status, "reason": usb_res["reason"], "state": state}
            selected_port = usb_res["selected"]["port_name"]
            state["selected_port"] = usb_res["selected"]
            _set_stage(resolved_state, state, "usb_discovery", "PASSED", usb_res["selected"])
        except Exception as exc:
            _set_stage(resolved_state, state, "usb_discovery", "FAILED", {"error": str(exc)})
            overall_status = "FAILED"
            return {"status": overall_status, "error": str(exc), "state": state}

        # 3. HELLO Handshake
        try:
            caps = run_hello_handshake(selected_port, engine_factory=engine_factory)
            state["device_identity"] = caps
            _set_stage(resolved_state, state, "hello_handshake", "PASSED", caps)
        except Exception as exc:
            _set_stage(resolved_state, state, "hello_handshake", "FAILED", {"port": selected_port, "error": str(exc)})
            overall_status = "FAILED"
            return {"status": overall_status, "error": str(exc), "state": state}

        # 4. Deterministic G1 Regression (NEVER reuses pre-G2-flash G1 state once G2 flash is active)
        prior_g1 = state["stages"]["g1_regression"]
        prior_detail = prior_g1.get("detail") if isinstance(prior_g1.get("detail"), dict) else {}
        first_flash_file = g2_manifest_p.parent / "first-flash.txt"
        flash_evidence_sha256 = sha256(first_flash_file) if first_flash_file.is_file() else None
        g2_flash_active = bool(assume_g2_flashed or first_flash_file.is_file())
        g2_raw = json.loads(g2_manifest_p.read_text(encoding="utf-8"))
        g2_is_authorized = (
            g2_raw.get("status") == "COMPILED_BUT_NOT_FLASHED"
            and bool(g2_raw.get("physical_attestation") or (g2_manifest_p.parent / "g2_physical_attestation.json").is_file())
        )
        active_manifest_p = g2_manifest_p if (g2_flash_active and g2_is_authorized) else g1_manifest_p
        active_g1_manifest = validate_release(active_manifest_p)
        manifest_role = "g2_post_flash" if active_manifest_p == g2_manifest_p else "g1_baseline"
        post_g2_flash_verified = (manifest_role == "g2_post_flash")

        # Never allow an un-authorized manifest to masquerade as post-flash verified G1
        if g2_flash_active and not g2_is_authorized and prior_g1.get("status") in ("PASSED", "RESUMED_PASSED"):
            state["pre_g2_flash_g1_regression"] = dict(prior_detail)

        same_board = (
            prior_g1.get("status") in ("PASSED", "RESUMED_PASSED")
            and prior_detail.get("device_uid_low") == caps["device_uid_low"]
            and prior_detail.get("firmware_version") == caps["firmware_version"]
            and prior_detail.get("post_g2_flash_verified") is True and post_g2_flash_verified is True
            and prior_detail.get("manifest_sdkconfig_sha256") == active_g1_manifest.get("sdkconfig_sha256")
            and prior_detail.get("flash_evidence_sha256") == flash_evidence_sha256
        )
        # Allow baseline pre-flash G1 resume ONLY when NOT post-G2-flash and matching baseline sdkconfig
        if not post_g2_flash_verified and not g2_flash_active:
            same_board = (
                prior_g1.get("status") in ("PASSED", "RESUMED_PASSED")
                and prior_detail.get("device_uid_low") == caps["device_uid_low"]
                and prior_detail.get("firmware_version") == caps["firmware_version"]
                and prior_detail.get("post_g2_flash_verified") is False
                and prior_detail.get("manifest_sdkconfig_sha256") == active_g1_manifest.get("sdkconfig_sha256")
            )

        if same_board and not force_g1:
            g1_detail = dict(prior_detail)
            _set_stage(resolved_state, state, "g1_regression", "RESUMED_PASSED", g1_detail)
        else:
            if post_g2_flash_verified and prior_g1.get("status") in ("PASSED", "RESUMED_PASSED") and not prior_detail.get("post_g2_flash_verified"):
                state["pre_g2_flash_g1_regression"] = dict(prior_detail)
            try:
                if physical_g1_runner is not None:
                    g1_ev, g1_dir = physical_g1_runner(selected_port, hw_dir, None, active_g1_manifest)
                elif engine_factory is not CanonicalSessionEngine:
                    g1_ev, g1_dir = _run_g1_via_custom_engine(engine_factory, selected_port, hw_dir, None, active_g1_manifest)
                else:
                    g1_ev, g1_dir = physical_g1(selected_port, hw_dir, None, active_g1_manifest)

                g1_detail = {
                    "conclusion": g1_ev.get("conclusion"),
                    "verification_result": g1_ev.get("verification_result"),
                    "host_samples_accepted": g1_ev.get("host_samples_accepted"),
                    "host_sample_value_errors": g1_ev.get("host_sample_value_errors"),
                    "firmware_samples_dropped": g1_ev.get("firmware_samples_dropped"),
                    "sha256_hash": g1_ev.get("sha256_hash"),
                    "source_mode": 1,
                    "bundle_dir": str(g1_dir),
                    "device_uid_low": caps["device_uid_low"],
                    "firmware_version": caps["firmware_version"],
                    "manifest_role": manifest_role,
                    "manifest_path": str(active_manifest_p),
                    "manifest_sdkconfig_sha256": active_g1_manifest.get("sdkconfig_sha256"),
                    "flash_evidence_sha256": flash_evidence_sha256,
                    "post_g2_flash_verified": post_g2_flash_verified,
                    "failure_reasons": g1_ev.get("failure_reasons", []),
                }
                if g1_ev.get("conclusion") != "PHYSICAL_G1_PASSED":
                    _set_stage(resolved_state, state, "g1_regression", "FAILED", g1_detail)
                    overall_status = "FAILED"
                    return {"status": overall_status, "error": "G1 failed; H0/G2 halted.", "state": state}
                _set_stage(resolved_state, state, "g1_regression", "PASSED", g1_detail)
            except Exception as exc:
                _set_stage(resolved_state, state, "g1_regression", "FAILED", {"port": selected_port, "manifest_role": manifest_role, "error": str(exc)})
                overall_status = "FAILED"
                return {"status": overall_status, "error": str(exc), "state": state}

        # 5. G2 Physical Gate Check (+ optional explicit interactive operator authorization)
        try:
            if authorize_g2_args is not None:
                authorize_g2_candidate(
                    g2_manifest_p,
                    authorize_g2_args["bclk"],
                    authorize_g2_args["ws"],
                    authorize_g2_args["din"],
                    authorize_g2_args["slot"],
                    authorize_g2_args["vdd_volts"],
                    authorize_g2_args.get("operator", operator),
                    authorize_g2_args["multimeter"],
                    prompt=prompt_fn,
                )
            g2_validated = validate_release(g2_manifest_p)
            attestation_file = g2_manifest_p.parent / "g2_physical_attestation.json"
            if not attestation_file.is_file() and not g2_validated.get("physical_attestation"):
                raise ValueError("Missing physical_attestation record (g2_physical_attestation.json).")
            gate_detail = {
                "g2_manifest": str(g2_manifest_p),
                "status": g2_validated["status"],
                "physical_attestation": g2_validated.get("physical_attestation"),
                "flash_confirmed": assume_g2_flashed or (g2_manifest_p.parent / "first-flash.txt").is_file(),
            }
            if not gate_detail["flash_confirmed"] and run_g2_captures is not True:
                gate_detail["next_step"] = (
                    f"Put ESP32-S3 in ROM Bootloader mode (BOOT+RESET) and run: "
                    f".\\.venv\\Scripts\\python.exe tools/hardware/bringup.py flash --port <COM_ROM> --manifest {g2_manifest_p}"
                )
                _set_stage(resolved_state, state, "g2_physical_gate", "WAITING_OPERATOR", gate_detail)
                overall_status = "WAITING_OPERATOR"
                return {"status": overall_status, "reason": "Authorized G2 manifest ready; waiting operator ROM flash confirmation.", "state": state}
            _set_stage(resolved_state, state, "g2_physical_gate", "PASSED", gate_detail)
        except Exception as exc:
            msg = str(exc)
            waiting = "PREPARED_NOT_AUTHORIZED_FOR_FLASH" in msg or "Missing physical_attestation" in msg
            _set_stage(
                resolved_state,
                state,
                "g2_physical_gate",
                "WAITING_OPERATOR" if waiting else "FAILED",
                {"error": msg, "checklist": OPERATOR_CHECKLIST_TR if waiting else None},
            )
            overall_status = "WAITING_OPERATOR" if waiting else "FAILED"
            return {"status": overall_status, "reason": msg, "state": state}

        if run_g2_captures is False:
            overall_status = "PASSED"
            return {"status": overall_status, "state": state}

        # 6A. Automated G2 10-second Quiet Room Capture (source_mode=0)
        quiet_summary: Optional[dict[str, Any]] = None
        prior_q = state["stages"]["g2_quiet_capture"]
        if prior_q.get("status") in ("PASSED", "RESUMED_PASSED") and isinstance(prior_q.get("detail"), dict):
            quiet_summary = dict(prior_q["detail"])
            _set_stage(resolved_state, state, "g2_quiet_capture", "RESUMED_PASSED", quiet_summary)
        else:
            if confirm_operator_ready is not None:
                confirm_operator_ready("QUIET: INMP441 takili iken 10 saniyelik SESSIZ ORTAM kaydi baslayacak.")
            try:
                quiet_summary = record_g2_session(
                    root=root,
                    port=selected_port,
                    role="quiet",
                    target_samples=g2_target_samples,
                    capture_timeout_s=g2_capture_timeout_s,
                    sessions_dir=sessions_dir,
                    engine_factory=engine_factory,
                )
                _set_stage(resolved_state, state, "g2_quiet_capture", "PASSED", quiet_summary)
            except G2CaptureValidationError as exc:
                _set_stage(resolved_state, state, "g2_quiet_capture", "FAILED", {"reason_code": exc.reason_code, **exc.summary})
                overall_status = "FAILED"
                return {"status": overall_status, "error": str(exc), "state": state}
            except Exception as exc:
                _set_stage(resolved_state, state, "g2_quiet_capture", "FAILED", {"error": str(exc)})
                overall_status = "FAILED"
                return {"status": overall_status, "error": str(exc), "state": state}

        # 6B. Automated G2 10-second Controlled Stimulus Capture (source_mode=0)
        stimulus_summary: Optional[dict[str, Any]] = None
        prior_s = state["stages"]["g2_stimulus_capture"]
        if prior_s.get("status") in ("PASSED", "RESUMED_PASSED") and isinstance(prior_s.get("detail"), dict):
            stimulus_summary = dict(prior_s["detail"])
            _set_stage(resolved_state, state, "g2_stimulus_capture", "RESUMED_PASSED", stimulus_summary)
        else:
            if confirm_operator_ready is not None:
                confirm_operator_ready("STIMULUS: Simdi INMP441 alt akustik deligine 10-15 cm mesafeden test sesi/alkis uygulayin.")
            try:
                stimulus_summary = record_g2_session(
                    root=root,
                    port=selected_port,
                    role="stimulus",
                    target_samples=g2_target_samples,
                    capture_timeout_s=g2_capture_timeout_s,
                    sessions_dir=sessions_dir,
                    engine_factory=engine_factory,
                )
                _set_stage(resolved_state, state, "g2_stimulus_capture", "PASSED", stimulus_summary)
            except G2CaptureValidationError as exc:
                _set_stage(resolved_state, state, "g2_stimulus_capture", "FAILED", {"reason_code": exc.reason_code, **exc.summary})
                overall_status = "FAILED"
                return {"status": overall_status, "error": str(exc), "state": state}
            except Exception as exc:
                _set_stage(resolved_state, state, "g2_stimulus_capture", "FAILED", {"error": str(exc)})
                overall_status = "FAILED"
                return {"status": overall_status, "error": str(exc), "state": state}

        comparison_json, comparison_md, acceptance_eval = write_g2_comparison(
            hw_dir, state["stages"]["g1_regression"]["detail"], quiet_summary, stimulus_summary
        )
        state["g2_comparison_paths"] = {"json": str(comparison_json), "markdown": str(comparison_md)}
        state["g2_acceptance_evaluation"] = acceptance_eval
        if acceptance_eval["verdict"] != "PASSED":
            stim_detail = dict(stimulus_summary)
            stim_detail["acceptance_evaluation"] = acceptance_eval
            _set_stage(resolved_state, state, "g2_stimulus_capture", "INCONCLUSIVE", stim_detail)
            save_state(resolved_state, state)
            overall_status = "INCONCLUSIVE"
            reason = "; ".join(acceptance_eval.get("reasons") or ["Stimulus recording did not separate meaningfully from quiet capture."])
            return {"status": overall_status, "reason": reason, "state": state}

        save_state(resolved_state, state)
        overall_status = "PASSED"
        return {"status": overall_status, "state": state}

    finally:
        # 7. ALWAYS save state & generate local Return ZIP (even on pause/failure), then optionally try GitHub evidence drop.
        save_state(resolved_state, state)
        extra_files = [resolved_state]
        if comparison_json is not None:
            extra_files.extend([comparison_json, comparison_md])
        try:
            pack_mod = _load_pack_return_module(root)
            zip_summary = pack_mod.create_lab_return_zip(
                root=root,
                output_path=return_zip_path,
                operator=operator,
                notes=notes or f"Wednesday Lab Orchestrator status={overall_status}",
                extra_files=extra_files,
            )
            state["latest_return_zip"] = zip_summary
            _set_stage(resolved_state, state, "return_package", "PASSED", zip_summary)
        except Exception as exc:
            _set_stage(resolved_state, state, "return_package", "FAILED", {"error": str(exc)})

        if push_evidence:
            pub_files = [resolved_state]
            if comparison_json and comparison_md:
                pub_files.extend([comparison_json, comparison_md])
            state["github_evidence_drop"] = upload_team_evidence_to_github(root, pub_files, git_runner=git_runner)
            save_state(resolved_state, state)


def get_wednesday_status_snapshot(root: Path = ROOT, state_path: Optional[Path] = None) -> dict[str, Any]:
    """Read-only status view for Device Center Lab Mode UI (does not probe serial or touch hardware)."""
    root = Path(root).resolve()
    resolved_state = (state_path or (root / DEFAULT_STATE_REL)).resolve()
    has_state_file = resolved_state.is_file()
    state = load_or_init_state(resolved_state, root) if has_state_file else {
        "schema_version": SCHEMA_VERSION,
        "updated_utc": None,
        "repo_root": str(root),
        "git_info": git_info(root),
        "selected_port": None,
        "device_identity": None,
        "stages": _default_stages(),
        "operator_prompt_checklist": OPERATOR_CHECKLIST_TR,
        "latest_return_zip": None,
        "github_evidence_drop": {"status": "NOT_REQUESTED", "uploaded": False},
    }
    try:
        ports = [p.to_dict() for p in UsbDiscoveryDoctor().scan_ports()]
    except Exception:
        ports = []
    return {
        "state_file_exists": has_state_file,
        "state_file_path": str(resolved_state),
        "ports": ports,
        "espressif_ports": [p for p in ports if p.get("is_espressif_candidate")],
        **state,
    }
