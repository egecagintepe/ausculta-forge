"""Software regression only: no serial port is opened by these tests."""
from copy import copy, deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import pytest

from pcg_app.canonical.engine import CanonicalSessionEngine
from pcg_app.canonical.acceptance import assess_g1
from pcg_app.canonical.simulator import SimulatedEsp32Device
from pcg_app.canonical.transport import DuplexLoopbackAdapter
from pcg_app import hardware_workflow as workflow


@pytest.fixture(scope="module")
def completed():
    engine=CanonicalSessionEngine()
    device=SimulatedEsp32Device()
    device.connect()
    engine.is_simulated=True
    engine.port_name="SIMULATED_ESP32_S3"
    engine.transport=DuplexLoopbackAdapter(device)
    def receive(wire):
        for packet in engine.session.handle_incoming_bytes(wire):
            engine.g1_observation.observe(packet)
    receive(device.process_incoming_bytes(engine.session.initiate_handshake(123)))
    receive(device.process_incoming_bytes(engine.session.request_start()))
    for _ in range(1875):
        receive(device.produce_next_audio_frame())
    receive(device.process_incoming_bytes(engine.session.request_stop()))
    assert engine.session.host_samples_accepted == 480000
    assert assess_g1(engine)["verification_result"] == "PASS"
    return engine


@pytest.fixture
def evidence_engine(completed):
    result=copy(completed)
    result.session=deepcopy(completed.session)
    result.g1_observation=copy(completed.g1_observation)
    return result


@pytest.mark.parametrize("field",["generated_samples","fully_queued_samples","audio_frames_queued",
    "audio_bytes_queued","session_id","dropped_samples","dma_overflow_events","ring_overflow_events",
    "usb_timeout_events","usb_disconnect_events","error_code"])
def test_falsified_or_faulted_telemetry_fails(evidence_engine,field):
    t=evidence_engine.session.final_telemetry
    setattr(t,field,getattr(t,field)+1)
    assert assess_g1(evidence_engine)["verification_result"]=="FAIL"


@pytest.mark.parametrize("counter",["total_frames_corrupted","total_sequence_gaps","total_duplicate_frames",
    "total_reordered_frames","total_timestamp_regressions","malformed_headers"])
def test_crc_sequence_and_parser_faults_fail(evidence_engine,counter):
    setattr(evidence_engine.session.decoder,counter,1)
    assert assess_g1(evidence_engine)["verification_result"]=="FAIL"


@pytest.mark.parametrize("defect",["missing_stop","partial","extra","mismatch","timestamp","format","ingestion","firmware"])
def test_missing_mandatory_evidence_fails(evidence_engine,defect):
    e=evidence_engine
    if defect=="missing_stop": e.session.final_telemetry=None
    if defect=="partial": e.session.host_samples_accepted=479744
    if defect=="extra": e.session.host_samples_accepted=480256
    if defect=="mismatch": e.g1_observation.mismatches=1
    if defect=="timestamp": e.g1_observation.timestamp_errors=1
    if defect=="format": e.g1_observation.format_errors=1
    if defect=="ingestion": e.host_ingestion_errors=1
    if defect=="firmware": e.session.device_capabilities.firmware_version_major=99
    assert assess_g1(e)["verification_result"]=="FAIL"


def test_simulation_and_unknown_transports_never_physical(evidence_engine,tmp_path):
    e=evidence_engine
    e.last_g1_evidence=assess_g1(e)
    assert e.last_g1_evidence["conclusion"]=="SOFTWARE_SIMULATION_PASS"
    directory=workflow.export_evidence(e,tmp_path)
    hashes=json.loads((directory/"sha256_manifest.json").read_text())
    assert all(workflow.sha256(directory/name)==digest for name,digest in hashes.items())
    assert "SOFTWARE SIMULATION" in (directory/"acceptance_report.md").read_text()
    e.is_simulated=False
    assert assess_g1(e)["conclusion"] in ("G1_FAILED","G1_INCOMPLETE")
    with pytest.raises(ValueError,match="rejects"):
        workflow.physical_g1("SIMULATED_ESP32_S3",tmp_path)


def test_preflight_never_opens_or_writes_ports(monkeypatch):
    monkeypatch.setattr(workflow.UsbDiscoveryDoctor,"scan_ports",lambda self: [])
    monkeypatch.setattr(workflow.shutil,"which",lambda name: None)
    report=workflow.preflight()
    assert report["BOARD_ATTACHED"]=="NOT_DETECTED"
    assert report["ESP_IDF"]=="NOT_READY"
    assert report["HARDWARE_TEST"]=="NOT_EXECUTED"
    assert "NOT_PROBED" in report["port_access"]


def test_windows_idf_launcher_is_not_read_as_python():
    assert workflow.idf_command("C:/idf.py.exe","build")==["C:/idf.py.exe","build"]


def test_canonical_maximum_count_matches_c_and_wire_spec():
    import numpy as np
    from pcg_app.canonical.codec import StreamingProtocolDecoder, build_profile_b_packet
    decoder=StreamingProtocolDecoder()
    wire=build_profile_b_packet(sequence_id=0,timestamp_us=0,sample_index_start=0,
                                samples=np.zeros(1025,dtype=np.int32))
    assert decoder.feed_bytes(wire)==[] and decoder.malformed_headers>0


def test_observer_handles_untrusted_uint64_index_without_crashing(completed):
    from pcg_app.canonical.acceptance import G1Observation
    packet=copy(completed.session.received_audio_frames[0])
    packet.sample_index_start=0xffffffffffffffff
    observer=G1Observation()
    observer.observe(packet)
    assert observer.timestamp_errors and observer.sequence_errors
    assert observer.first_mismatch is not None


def test_flash_manifest_rejects_tampered_binary(tmp_path):
    path=tmp_path/"app.bin"
    path.write_bytes(b"firmware")
    manifest={"status":"COMPILED_BUT_NOT_FLASHED","target":"esp32s3","idf_version":"5.5.1",
              "build_directory":str(tmp_path),"binary_sha256":{"app.bin":workflow.sha256(path)}}
    config=tmp_path/"sdkconfig"
    config.write_bytes((workflow.ROOT/"firmware/sdkconfig.defaults").read_bytes())
    manifest["sdkconfig_sha256"]=workflow.sha256(config)
    target=tmp_path/"manifest.json"
    workflow.write_json(target,manifest)
    workflow.validate_release(target)
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError,match="changed"):
        workflow.validate_release(target)


def test_flash_requires_explicit_confirmation_after_identity(monkeypatch,tmp_path):
    spec=importlib.util.spec_from_file_location("bringup",Path(__file__).parents[2]/"tools/hardware/bringup.py")
    cli=importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    monkeypatch.setattr(cli,"preflight",lambda:{"ports":[{"port_name":"COM_KNOWN"}]})
    monkeypatch.setattr(cli,"identify",lambda port:{"status":"TEST_DOUBLE_ROM_IDENTITY"})
    monkeypatch.setattr(cli,"validate_release",lambda path:{"build_directory":str(tmp_path),"commit":"test",
        "firmware_version":"1.1.0","flash_files":{"0x0":"b.bin","0x8000":"p.bin","0x10000":"a.bin"},
        "binary_sha256":{"b.bin":"b","p.bin":"p","a.bin":"a"}})
    monkeypatch.setattr(cli.subprocess,"run",lambda *a,**k:pytest.fail("No write without permission"))
    answers=iter(["COM_KNOWN","NO"])
    with pytest.raises(RuntimeError,match="not authorized"):
        cli.flash("COM_KNOWN",tmp_path/"manifest.json",prompt=lambda _:next(answers))


def test_doctor_enumeration_never_means_firmware_verified(monkeypatch):
    from pcg_app.diagnostics.usb_doctor import UsbDiscoveryDoctor, DiscoveryDiagnosticState
    journal=SimpleNamespace(record=lambda **kwargs:None)
    port=SimpleNamespace(device="COM_CANDIDATE",vid=0x303a,pid=0x4001,description="Espressif")
    doctor=UsbDiscoveryDoctor(flight_recorder=journal,custom_comports_fn=lambda:[port])
    monkeypatch.setattr(doctor,"check_port_accessibility",lambda *a:pytest.fail("Passive scan must not open"))
    state,_=doctor.diagnose_environment()
    assert state==DiscoveryDiagnosticState.PORTS_ENUMERATED_NO_VERIFIED_DEVICE


def test_engine_restart_and_live_mode_do_not_use_g1_validator():
    import time
    engine=CanonicalSessionEngine()
    try:
        engine.connect("SIMULATED_ESP32_S3").result(timeout=3)
        first=engine.start_acquisition(target_samples=256,source_mode=0).result(timeout=3)
        assert engine.session.sample_validator is None
        deadline=time.monotonic()+2
        while engine.session.host_samples_accepted<256 and time.monotonic()<deadline: time.sleep(0.01)
        engine.stop_acquisition().result(timeout=3)
        second=engine.start_acquisition(target_samples=256,source_mode=1).result(timeout=3)
        assert second.session_id!=first.session_id
        assert engine.session.sample_validator is not None
        engine.stop_acquisition().result(timeout=3)
        engine.disconnect().result(timeout=3)
        engine.connect("SIMULATED_ESP32_S3").result(timeout=3)
        assert engine.state.value=="READY" and engine.last_g1_evidence is None
    finally:
        engine.disconnect().result(timeout=3)


def test_selected_build_version_mismatch_prevents_start(monkeypatch,tmp_path,completed):
    import concurrent.futures
    from pcg_app.canonical.transport import UsbCdcAcmAdapter
    engine=CanonicalSessionEngine()
    engine.transport=UsbCdcAcmAdapter()
    engine.session.device_capabilities=deepcopy(completed.session.device_capabilities)
    ready=concurrent.futures.Future(); ready.set_result(engine.session.device_capabilities)
    monkeypatch.setattr(engine,"connect",lambda *a,**k:ready)
    monkeypatch.setattr(engine,"start_acquisition",lambda **k:pytest.fail("Wrong firmware must not START"))
    monkeypatch.setattr(workflow,"CanonicalSessionEngine",lambda **k:engine)
    monkeypatch.setattr(workflow.UsbDiscoveryDoctor,"scan_ports",lambda self:[])
    evidence,directory=workflow.physical_g1("COM_TEST_DOUBLE",tmp_path,
        firmware_manifest={"firmware_version":"99.0.0"})
    assert evidence["verification_result"]=="FAIL"
    assert any("differs from selected build" in reason for reason in evidence["failure_reasons"])
    assert (directory/"acceptance_report.md").exists()


@pytest.mark.parametrize("missing_stop",[False,True])
def test_production_engine_saves_failed_evidence_for_stop_timeout_and_ingestion(monkeypatch,missing_stop):
    import time
    from pcg_app.canonical import engine as module
    device=SimulatedEsp32Device()
    device.missing_stop_ack=missing_stop
    monkeypatch.setattr(module,"SimulatedEsp32Device",lambda:device)
    engine=CanonicalSessionEngine(on_audio_packet=lambda packet:False)
    try:
        engine.connect("SIMULATED_ESP32_S3").result(timeout=3)
        engine.start_acquisition(target_samples=256).result(timeout=3)
        deadline=time.monotonic()+2
        while engine.session.host_samples_accepted<256 and time.monotonic()<deadline: time.sleep(0.01)
        if missing_stop:
            with pytest.raises(TimeoutError): engine.stop_acquisition(timeout_s=0.05).result(timeout=2)
        else:
            engine.stop_acquisition().result(timeout=3)
        assert engine.last_g1_evidence["verification_result"]=="FAIL"
        assert engine.host_ingestion_errors>0
        if missing_stop:
            assert engine.last_g1_evidence["gates"]["stop_ack"]=="FAIL"
    finally:
        engine.disconnect().result(timeout=3)


def test_portable_validate_release_on_g1_rollback_backup():
    manifest_path = workflow.ROOT / "firmware/g1_rollback_backup/firmware_build_manifest.json"
    manifest = workflow.validate_release(manifest_path)
    assert manifest["firmware_version"] == "1.1.0"
    assert Path(manifest["build_directory"]).resolve() == manifest_path.parent.resolve()


def test_validate_release_rejects_g2_compile_check_and_unauthorized_g2(tmp_path):
    cc_dir = tmp_path / "g2_compile_check"
    cc_dir.mkdir()
    cc_manifest = cc_dir / "firmware_build_manifest.json"
    cc_manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden for flashing"):
        workflow.validate_release(cc_manifest)

    staged = tmp_path / "g2_candidate"
    staged.mkdir()
    unauth = staged / "firmware_build_manifest.json"
    unauth.write_text(json.dumps({
        "status": "PREPARED_NOT_AUTHORIZED_FOR_FLASH",
        "target": "esp32s3",
        "idf_version": "5.5.1",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="PREPARED_NOT_AUTHORIZED_FOR_FLASH"):
        workflow.validate_release(unauth)


def test_authorize_g2_candidate_gates_and_promotion(tmp_path):
    base = tmp_path / "g2_candidate_test"
    (base / "bootloader").mkdir(parents=True)
    (base / "partition_table").mkdir(parents=True)
    files = {
        "bootloader/bootloader.bin": b"boot",
        "partition_table/partition-table.bin": b"part",
        "auscultaforge_g1.bin": b"appg2",
    }
    hashes = {}
    for rel, content in files.items():
        p = base / rel
        p.write_bytes(content)
        hashes[rel] = workflow.sha256(p)

    defaults = (workflow.ROOT / "firmware/sdkconfig.defaults").read_text(encoding="utf-8")
    g2_cfg_text = (
        defaults
        + "\nCONFIG_AF_I2S_CONFIRMED_PROFILE=y\n"
        + "CONFIG_AF_I2S_BCLK=4\n"
        + "CONFIG_AF_I2S_WS=5\n"
        + "CONFIG_AF_I2S_DIN=6\n"
        + "# CONFIG_AF_I2S_RIGHT_SLOT is not set\n"
    )
    cfg_path = base / "sdkconfig"
    cfg_path.write_text(g2_cfg_text, encoding="utf-8")

    manifest_path = base / "firmware_build_manifest.json"
    manifest = {
        "status": "PREPARED_NOT_AUTHORIZED_FOR_FLASH",
        "target": "esp32s3",
        "idf_version": "5.5.1",
        "firmware_version": "1.1.0",
        "build_directory": str(base),
        "sdkconfig_sha256": workflow.sha256(cfg_path),
        "binary_sha256": hashes,
    }
    workflow.write_json(manifest_path, manifest)

    # 5V must be rejected
    with pytest.raises(ValueError, match="3.3V"):
        workflow.authorize_g2_candidate(
            manifest_path, 4, 5, 6, "left", 5.0, "Kaan", "Fluke-1", prompt=lambda _: "AUTHORIZE G2 BCLK4 WS5 DIN6 LEFT 3V3"
        )

    # Pin mismatch with staged sdkconfig must be rejected
    with pytest.raises(ValueError, match="Confirmed physical pins differ"):
        workflow.authorize_g2_candidate(
            manifest_path, 7, 5, 6, "left", 3.31, "Kaan", "Fluke-1", prompt=lambda _: "AUTHORIZE G2 BCLK7 WS5 DIN6 LEFT 3V3"
        )

    # Wrong confirmation phrase aborts
    with pytest.raises(RuntimeError, match="aborted"):
        workflow.authorize_g2_candidate(
            manifest_path, 4, 5, 6, "left", 3.31, "Kaan", "Fluke-1", prompt=lambda _: "NO"
        )

    # Valid confirmation promotes manifest and passes validate_release
    promoted = workflow.authorize_g2_candidate(
        manifest_path, 4, 5, 6, "left", 3.31, "Kaan", "Fluke-1",
        prompt=lambda _: "AUTHORIZE G2 BCLK4 WS5 DIN6 LEFT 3V3",
    )
    assert promoted["status"] == "COMPILED_BUT_NOT_FLASHED"
    assert (base / "g2_physical_attestation.json").is_file()
    validated = workflow.validate_release(manifest_path)
    assert validated["physical_attestation"]["measured_vdd_volts"] == 3.31


def test_download_zip_fallback_without_git_or_local_build(monkeypatch, tmp_path):
    staged = tmp_path / "firmware/releases/g1_release_20261117/firmware_build_manifest.json"
    staged.parent.mkdir(parents=True)
    staged.write_text(json.dumps({"commit": "abc1234zip"}), encoding="utf-8")
    selected = workflow.default_release_manifest_path(tmp_path)
    assert selected == staged

    monkeypatch.setattr(workflow.shutil, "which", lambda name: None)
    info = workflow.git_info(tmp_path)
    assert info["commit"] == "abc1234zip"
    assert info["state"] == "DOWNLOAD_ZIP_NO_GIT"


def test_pack_lab_return_creates_verified_zip_without_mutating_sources(tmp_path):
    import zipfile
    spec = importlib.util.spec_from_file_location("pack_lab_return", workflow.ROOT / "tools/hardware/pack_lab_return.py")
    packer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packer)

    bundle = tmp_path / "experiments/hardware/20261118T090000Z_deadbeef"
    bundle.mkdir(parents=True)
    (bundle / "acceptance_report.md").write_text("# PASS\n", encoding="utf-8")
    (tmp_path / "experiments/hardware/g2-quiet.json").write_text('{"kind": "RAW_RECORDING_SCREEN_ONLY", "constant_zero": false}\n', encoding="utf-8")

    sess = tmp_path / "experiments/sessions/session_20261118_090500_0001"
    sess.mkdir(parents=True)
    (sess / "raw.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    (sess / "session.json").write_text(json.dumps({
        "session_id": sess.name,
        "source": "physical_i2s_mic",
        "total_samples": 480000,
        "duration_s": 10.0,
        "raw_wav_sha256": "deadbeef",
    }), encoding="utf-8")

    att = tmp_path / "firmware/releases/g2_candidate_20261117/g2_physical_attestation.json"
    att.parent.mkdir(parents=True)
    att.write_text('{"measured_vdd_volts": 3.31}\n', encoding="utf-8")
    (att.parent / "firmware_build_manifest.json").write_text('{"commit": "mainsha"}\n', encoding="utf-8")

    out_zip = tmp_path / "return_bundle.zip"
    mock_appdata = tmp_path / "mock_appdata_logs"
    mock_appdata.mkdir()
    (mock_appdata / "flight_recorder.jsonl").write_text('{"event":"TEST"}\n', encoding="utf-8")
    summary = packer.create_lab_return_zip(
        root=tmp_path,
        output_path=out_zip,
        operator="Kaan_Ozan",
        notes="Wed run",
        appdata_logs_dir=mock_appdata,
    )
    assert out_zip.is_file()
    assert summary["file_count"] == 7
    assert summary["gate_evidence_summary"]["h0_g2_attestation_present"] is True
    assert len(summary["gate_evidence_summary"]["recorded_sessions"]) == 1

    with zipfile.ZipFile(out_zip, "r") as zf:
        names = set(zf.namelist())
        assert "RETURN_PACKAGE_MANIFEST.json" in names
        assert "SHA256SUMS.txt" in names
        assert "experiments/sessions/session_20261118_090500_0001/raw.wav" in names
        manifest = json.loads(zf.read("RETURN_PACKAGE_MANIFEST.json").decode("utf-8"))
        assert manifest["operator"] == "Kaan_Ozan"
        assert manifest["gate_evidence_summary"]["g2_qualification_jsons"] == ["experiments/hardware/g2-quiet.json"]
