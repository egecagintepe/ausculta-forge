"""Hardware-free fault-injection and resilience tests for Autonomous Wednesday Lab Orchestrator."""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import zipfile

from fastapi.testclient import TestClient
import numpy as np
import pytest

from pcg_app.app import create_app
from pcg_app.canonical.codec import DecodedPacket, HelloAck, StartAck, StatusTelemetry, MSG_TYPE_AUDIO_DATA
from pcg_app.canonical.session import SessionState
from pcg_app.diagnostics.usb_doctor import UsbPortDescriptor
from pcg_app.hardware_workflow import ROOT, git_info, authorize_g2_candidate
from pcg_app.wednesday_orchestrator import (
    DEFAULT_G1_MANIFEST_REL,
    DEFAULT_G2_MANIFEST_REL,
    DEFAULT_ROLLBACK_MANIFEST_REL,
    G2CaptureValidationError,
    get_wednesday_status_snapshot,
    run_wednesday_orchestrator,
)


def _stage_minimal_repo(tmp_root: Path) -> Path:
    """Copy minimal manifests, binaries, and pack_lab_return.py into an isolated temp folder (no .git)."""
    for rel in (
        DEFAULT_ROLLBACK_MANIFEST_REL,
        "firmware/g1_rollback_backup/auscultaforge_g1.bin",
        "firmware/g1_rollback_backup/bootloader/bootloader.bin",
        "firmware/g1_rollback_backup/partition_table/partition-table.bin",
        "firmware/g1_rollback_backup/sdkconfig",
        "firmware/g1_rollback_backup/README.md",
        DEFAULT_G1_MANIFEST_REL,
        "firmware/releases/g1_release_20261117/auscultaforge_g1.bin",
        "firmware/releases/g1_release_20261117/bootloader/bootloader.bin",
        "firmware/releases/g1_release_20261117/partition_table/partition-table.bin",
        "firmware/releases/g1_release_20261117/sdkconfig",
        "firmware/releases/g1_release_20261117/README.md",
        DEFAULT_G2_MANIFEST_REL,
        "firmware/releases/g2_candidate_20261117/auscultaforge_g1.bin",
        "firmware/releases/g2_candidate_20261117/bootloader/bootloader.bin",
        "firmware/releases/g2_candidate_20261117/partition_table/partition-table.bin",
        "firmware/releases/g2_candidate_20261117/sdkconfig",
        "firmware/releases/g2_candidate_20261117/README.md",
        "firmware/CMakeLists.txt",
        "firmware/main/idf_component.yml",
        "firmware/dependencies.lock",
        "firmware/sdkconfig.defaults",
        "software/pcg_app/canonical/engine.py",
        "software/pcg_app/app.py",
        "tools/hardware/pack_lab_return.py",
    ):
        src = ROOT / rel
        dst = tmp_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return tmp_root


def _authorize_temp_g2(tmp_root: Path) -> Path:
    manifest_p = tmp_root / DEFAULT_G2_MANIFEST_REL
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["build_directory"] = str(manifest_p.parent)
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    authorize_g2_candidate(
        manifest_p,
        bclk_gpio=4,
        ws_gpio=5,
        din_gpio=6,
        slot="left",
        vdd_volts=3.31,
        operator="Kaan & Ozan",
        multimeter_id="Fluke-115",
        prompt=lambda _: "AUTHORIZE G2 BCLK4 WS5 DIN6 LEFT 3V3",
    )
    return manifest_p


class _FakeScanner:
    def __init__(self, ports: list[UsbPortDescriptor]) -> None:
        self._ports = ports

    def scan_ports(self) -> list[UsbPortDescriptor]:
        return list(self._ports)


class _FakeG2Engine:
    """In-memory physical-transport stand-in emitting controllable source_mode=0 PCM packets."""

    def __init__(
        self,
        waveform_mode_by_call: list[str],
        disconnect_after_packets: int | None = None,
        corrupt_crc_after: int | None = None,
        reject_g2: bool = False,
        **kwargs,
    ) -> None:
        self.waveform_mode_by_call = waveform_mode_by_call
        self.disconnect_after_packets = disconnect_after_packets
        self.corrupt_crc_after = corrupt_crc_after
        self.reject_g2 = reject_g2
        self.on_audio_packet = kwargs.get("on_audio_packet")
        self.on_disconnect = kwargs.get("on_disconnect")
        self.is_simulated = False
        self.state = SessionState.DISCONNECTED
        self._caps = HelloAck(
            nonce_echo=1,
            protocol_version_major=1,
            protocol_version_minor=0,
            supported_profiles_mask=2,
            supported_encodings_mask=1,
            hardware_sample_rate_hz=48000,
            firmware_version_major=1,
            firmware_version_minor=1,
            firmware_version_patch=0,
            reserved=0,
            max_frame_samples=256,
            capability_flags=0,
            device_uid_low=0xB1AA7CC4,
        )
        self.session = SimpleNamespace(
            error_log=[],
            decoder=SimpleNamespace(total_frames_corrupted=0, total_sequence_gaps=0),
            host_samples_accepted=0,
        )
        self._target_samples = 0

    def connect(self, port: str, timeout_s: float = 4.0):
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self.state = SessionState.READY
        fut.set_result(self._caps)
        return fut

    def start_acquisition(
        self,
        target_samples: int = 480000,
        source_mode: int = 0,
        sample_rate_hz: int = 48000,
        encoding: int = 1,
        channels: int = 1,
        timeout_s: float = 4.0,
    ):
        fut: concurrent.futures.Future = concurrent.futures.Future()
        if source_mode == 0 and self.reject_g2:
            fut.set_exception(RuntimeError("Unsupported source: live mode needs a reviewed I2S firmware profile. (firmware code 0x0002)"))
            return fut
        self.state = SessionState.STREAMING
        self._target_samples = target_samples
        fut.set_result(
            StartAck(
                session_id=7,
                session_reference_time_us=1000,
                accepted_sample_rate_hz=sample_rate_hz,
                accepted_target_samples=target_samples,
                accepted_source_mode=source_mode,
                encoding=encoding,
                channels=channels,
                profile_id=2,
            )
        )
        mode = self.waveform_mode_by_call.pop(0) if self.waveform_mode_by_call else "quiet"
        n_frames = max(1, target_samples // 256)
        for seq in range(n_frames):
            if self.disconnect_after_packets is not None and seq >= self.disconnect_after_packets:
                self.state = SessionState.ERROR
                if self.on_disconnect:
                    self.on_disconnect("Simulated USB cable pull mid-capture")
                break
            t = (np.arange(256, dtype=np.float64) + seq * 256) / float(sample_rate_hz)
            if mode == "zero":
                pcm = np.zeros(256, dtype=np.int32)
            elif mode == "quiet":
                rng = np.random.default_rng(100 + seq)
                pcm = (rng.normal(0.0, 0.002, size=256) * float(1 << 23)).astype(np.int32)
            else:  # stimulus
                sig = 0.25 * np.sin(2.0 * np.pi * 120.0 * t) + 0.10 * np.sin(2.0 * np.pi * 240.0 * t)
                pcm = (sig * float(1 << 23)).astype(np.int32)
            crc_ok = self.corrupt_crc_after is None or seq < self.corrupt_crc_after
            pkt = DecodedPacket(
                sequence_id=seq,
                timestamp_us=int(1000 + (seq * 256 * 1_000_000) // sample_rate_hz),
                sample_index_start=seq * 256,
                sample_count=256,
                sample_rate_hz=sample_rate_hz,
                meaningful_bits=24,
                flags=0x01,
                encoding=1,
                mcu_buffer_drops=0,
                is_profile_b=True,
                crc_ok=crc_ok,
                raw_samples=pcm,
                normalized_samples=(pcm.astype(np.float32) / float(1 << 23)),
                msg_type=MSG_TYPE_AUDIO_DATA,
            )
            if self.on_audio_packet:
                self.on_audio_packet(pkt)
        return fut

    def stop_acquisition(self, timeout_s: float = 4.0):
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self.state = SessionState.COMPLETE
        fut.set_result(
            StatusTelemetry(
                session_id=7,
                generated_samples=self._target_samples,
                fully_queued_samples=self._target_samples,
                dropped_samples=0,
                audio_frames_queued=max(1, self._target_samples // 256),
                dma_overflow_events=0,
                ring_overflow_events=0,
                usb_partial_write_events=0,
                usb_timeout_events=0,
                usb_disconnect_events=0,
                audio_bytes_queued=self._target_samples * 4,
                stop_reason=0,
                error_code=0,
            )
        )
        return fut

    def disconnect(self, timeout_s: float = 2.0):
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self.state = SessionState.DISCONNECTED
        fut.set_result(None)
        return fut


def _espressif_port(name: str = "COM10") -> UsbPortDescriptor:
    return UsbPortDescriptor(
        port_name=name,
        description="USB Serial Device",
        hwid="USB\\VID_303A&PID_4001&MI_00\\0",
        vid=0x303A,
        pid=0x4001,
        serial_number="B1AA7CC4",
        manufacturer="Espressif",
        product="ESP32-S3",
        interface="CDC",
        is_espressif_candidate=True,
        candidate_reason="Espressif native USB CDC",
    )


def _intel_port(name: str = "COM3") -> UsbPortDescriptor:
    return UsbPortDescriptor(
        port_name=name,
        description="Intel Active Management Technology",
        hwid="PCI\\VEN_8086",
        vid=0x8086,
        pid=0x1234,
        serial_number=None,
        manufacturer="Intel",
        product=None,
        interface=None,
        is_espressif_candidate=False,
        candidate_reason="Non-Espressif device",
    )


def test_windows_setup_missing_python_and_node_fault_injection():
    """Verify SkipAutoInstall exits with clear non-zero codes when Python or Node are absent."""
    ps_script = ROOT / "scripts/handoff/windows_setup.ps1"
    missing_py = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps_script),
            "-NonInteractive",
            "-SkipAutoInstall",
            "-SkipFrontend",
            "-PythonExeOverride",
            "C:\\auscultaforge_missing\\python.exe",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    assert missing_py.returncode == 2
    assert "MISSING_PYTHON" in (missing_py.stdout + missing_py.stderr)

    missing_node = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps_script),
            "-NonInteractive",
            "-SkipAutoInstall",
            "-NodeExeOverride",
            "C:\\auscultaforge_missing\\node.exe",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )
    assert missing_node.returncode == 3
    assert "MISSING_NODE" in (missing_node.stdout + missing_node.stderr)


def test_turkish_path_and_github_zip_without_git_supported(tmp_path):
    """Turkish/space directory extracted as GitHub Download ZIP without .git works end-to-end."""
    zip_folder = _stage_minimal_repo(tmp_path / "Ege Çağın_Archive Extract")
    gi = git_info(zip_folder)
    assert gi["state"] == "DOWNLOAD_ZIP_NO_GIT"
    assert gi["commit"] is not None

    state_file = zip_folder / "experiments/hardware/wednesday_20261118_state.json"
    out_zip = zip_folder / "return.zip"
    res = run_wednesday_orchestrator(
        root=zip_folder,
        state_path=state_file,
        scanner_factory=lambda: _FakeScanner([]),
        return_zip_path=out_zip,
    )
    assert res["status"] == "WAITING_OPERATOR"
    assert res["state"]["stages"]["preflight_and_hashes"]["status"] == "PASSED"
    assert res["state"]["stages"]["usb_discovery"]["status"] == "WAITING_OPERATOR"
    assert out_zip.is_file()
    with zipfile.ZipFile(out_zip) as zf:
        assert "RETURN_PACKAGE_MANIFEST.json" in zf.namelist()
        assert "experiments/hardware/wednesday_20261118_state.json" in zf.namelist()


def test_wrong_non_espressif_com_port_refused_and_archives_zip(tmp_path):
    """Selecting Intel COM3 fails usb_discovery safely without touching serial, while still producing ZIP."""
    repo = _stage_minimal_repo(tmp_path / "zip_repo")
    out_zip = tmp_path / "wrong_com.zip"
    res = run_wednesday_orchestrator(
        root=repo,
        port="COM3",
        scanner_factory=lambda: _FakeScanner([_intel_port("COM3"), _espressif_port("COM12")]),
        return_zip_path=out_zip,
    )
    assert res["status"] == "FAILED"
    assert "REFUSED_NON_ESPRESSIF_PORT" in res["error"]
    assert res["state"]["stages"]["usb_discovery"]["status"] == "FAILED"
    assert res["state"]["stages"]["hello_handshake"]["status"] == "PENDING"
    assert out_zip.is_file()


def test_forbidden_g2_compile_check_manifest_rejected(tmp_path):
    """Passing g2_compile_check manifest is blocked at preflight before any hardware operation."""
    repo = _stage_minimal_repo(tmp_path / "zip_repo")
    bad_dir = repo / "firmware/build/g2_compile_check"
    bad_dir.mkdir(parents=True)
    bad_manifest = bad_dir / "firmware_build_manifest.json"
    bad_manifest.write_text("{}", encoding="utf-8")

    out_zip = tmp_path / "bad_manifest.zip"
    res = run_wednesday_orchestrator(
        root=repo,
        g2_manifest_path=bad_manifest,
        scanner_factory=lambda: _FakeScanner([_espressif_port("COM12")]),
        return_zip_path=out_zip,
    )
    assert res["status"] == "FAILED"
    assert "g2_compile_check" in res["error"]
    assert res["state"]["stages"]["preflight_and_hashes"]["status"] == "FAILED"
    assert out_zip.is_file()


def test_g2_digital_silence_never_claims_pass(tmp_path):
    """All-zero I2S data (constant_zero=True) MUST fail G2 capture and never mark PASS."""
    repo = _stage_minimal_repo(tmp_path / "zip_repo")
    _authorize_temp_g2(repo)
    modes = ["zero"]

    res = run_wednesday_orchestrator(
        root=repo,
        port="COM12",
        assume_g2_flashed=True,
        g2_target_samples=1024,
        scanner_factory=lambda: _FakeScanner([_espressif_port("COM12")]),
        engine_factory=lambda **kw: _FakeG2Engine(modes, **kw),
        physical_g1_runner=lambda port, out, bi, mf: (
            {
                "conclusion": "PHYSICAL_G1_PASSED",
                "verification_result": "PASS",
                "host_samples_accepted": 480000,
                "host_sample_value_errors": 0,
                "firmware_samples_dropped": 0,
                "sha256_hash": "abc",
                "failure_reasons": [],
            },
            out / "dummy_g1",
        ),
        return_zip_path=tmp_path / "silence.zip",
    )
    assert res["status"] == "FAILED"
    assert "DIGITAL_SILENCE_OR_CONSTANT_SIGNAL" in res["error"]
    assert res["state"]["stages"]["g2_quiet_capture"]["status"] == "FAILED"
    assert res["state"]["stages"]["g2_quiet_capture"]["detail"]["constant_zero"] is True
    assert (tmp_path / "silence.zip").is_file()


def test_g2_disconnect_mid_stream_preserves_logs_and_zip(tmp_path):
    """Mid-stream USB disconnect fails cleanly, logs partial count, and writes return ZIP."""
    repo = _stage_minimal_repo(tmp_path / "zip_repo")
    _authorize_temp_g2(repo)
    modes = ["quiet"]

    res = run_wednesday_orchestrator(
        root=repo,
        port="COM12",
        assume_g2_flashed=True,
        g2_target_samples=1024,
        scanner_factory=lambda: _FakeScanner([_espressif_port("COM12")]),
        engine_factory=lambda **kw: _FakeG2Engine(modes, disconnect_after_packets=1, **kw),
        physical_g1_runner=lambda port, out, bi, mf: (
            {
                "conclusion": "PHYSICAL_G1_PASSED",
                "verification_result": "PASS",
                "host_samples_accepted": 480000,
                "host_sample_value_errors": 0,
                "firmware_samples_dropped": 0,
                "sha256_hash": "abc",
                "failure_reasons": [],
            },
            out / "dummy_g1",
        ),
        return_zip_path=tmp_path / "disc.zip",
    )
    assert res["status"] == "FAILED"
    assert "disconnected" in res["error"].lower()
    assert res["state"]["stages"]["g2_quiet_capture"]["status"] == "FAILED"
    assert res["state"]["stages"]["g2_quiet_capture"]["detail"]["samples_received"] == 256
    assert (tmp_path / "disc.zip").is_file()


def test_full_resumable_orchestration_g1_g2_and_github_fallback(tmp_path):
    """Run G1 + H0 + quiet/stimulus G2, verify resume skips redundant G1, and tolerate GitHub push failure."""
    repo = _stage_minimal_repo(tmp_path / "zip_repo")
    # Simulate presence of .git without real remote so push failure path runs deterministically.
    (repo / ".git").mkdir()
    _authorize_temp_g2(repo)

    g1_calls = {"count": 0}

    def _fake_g1(port, out, bi, mf):
        g1_calls["count"] += 1
        return (
            {
                "conclusion": "PHYSICAL_G1_PASSED",
                "verification_result": "PASS",
                "host_samples_accepted": 480000,
                "host_sample_value_errors": 0,
                "firmware_samples_dropped": 0,
                "sha256_hash": "g1sha",
                "failure_reasons": [],
            },
            out / "g1_bundle",
        )

    def _failing_git(cmd, **kwargs):
        if "diff" in cmd:
            return subprocess.CompletedProcess(cmd, 1, "", "")
        if "push" in cmd:
            return subprocess.CompletedProcess(cmd, 128, "", "fatal: could not read Username (simulated offline/no-auth)")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    modes = ["quiet", "stimulus"]
    out_zip = tmp_path / "full_pass.zip"
    res1 = run_wednesday_orchestrator(
        root=repo,
        assume_g2_flashed=True,
        g2_target_samples=2048,
        scanner_factory=lambda: _FakeScanner([_espressif_port("COM14")]),
        engine_factory=lambda **kw: _FakeG2Engine(modes, **kw),
        physical_g1_runner=_fake_g1,
        return_zip_path=out_zip,
        push_evidence=True,
        git_runner=_failing_git,
    )
    assert res1["status"] == "PASSED"
    assert g1_calls["count"] == 1
    assert res1["state"]["stages"]["g1_regression"]["status"] == "PASSED"
    assert res1["state"]["stages"]["g2_quiet_capture"]["detail"]["source_mode"] == 0
    assert res1["state"]["stages"]["g2_stimulus_capture"]["detail"]["acquisition_origin"] == "physical_i2s_inmp441"
    comp = json.loads((repo / "experiments/hardware/wednesday_g2_comparison.json").read_text(encoding="utf-8"))
    assert comp["provenance_separation"]["g1_source_mode"] == 1
    assert comp["provenance_separation"]["g2_source_mode"] == 0
    assert comp["stimulus_vs_quiet_snr_20_500hz_db"] > 20.0
    # GitHub failure must fall back cleanly to local ZIP without failing run
    assert res1["state"]["github_evidence_drop"]["status"] == "FALLBACK_LOCAL_ZIP"
    assert out_zip.is_file()

    # Second run resumes cleanly without repeating G1 or G2 captures
    res2 = run_wednesday_orchestrator(
        root=repo,
        assume_g2_flashed=True,
        g2_target_samples=2048,
        scanner_factory=lambda: _FakeScanner([_espressif_port("COM14")]),
        engine_factory=lambda **kw: _FakeG2Engine([], **kw),
        physical_g1_runner=_fake_g1,
        return_zip_path=tmp_path / "full_resumed.zip",
    )
    assert res2["status"] == "PASSED"
    assert g1_calls["count"] == 1  # Not called again!
    assert res2["state"]["stages"]["g1_regression"]["status"] == "RESUMED_PASSED"
    assert res2["state"]["stages"]["g2_quiet_capture"]["status"] == "RESUMED_PASSED"
    assert res2["state"]["stages"]["g2_stimulus_capture"]["status"] == "RESUMED_PASSED"


def test_lab_mode_fastapi_endpoints():
    """Verify Lab Mode status endpoint and read-only return ZIP REST endpoint."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/lab/wednesday-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "stages" in data
    assert "preflight_and_hashes" in data["stages"]
    assert "ports" in data

    # Also test POST /api/lab/pack-return and clean up generated repo-root ZIP afterward
    pack_resp = client.post("/api/lab/pack-return")
    assert pack_resp.status_code == 200
    pack_data = pack_resp.json()
    assert pack_data["status"] == "PACKAGED"
    zip_p = Path(pack_data["zip_path"])
    try:
        assert zip_p.is_file()
        assert pack_data["file_count"] > 0
    finally:
        zip_p.unlink(missing_ok=True)
