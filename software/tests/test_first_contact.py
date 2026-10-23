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
