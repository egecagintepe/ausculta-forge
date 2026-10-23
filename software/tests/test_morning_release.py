"""Release regressions exercise production paths; all devices here are software doubles."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from pcg_app.app import create_app
from pcg_app.canonical import codec
from pcg_app.canonical.engine import CanonicalSessionEngine
from pcg_app.canonical.session import HostProtocolSession, SessionState
from pcg_app.canonical.transport import UsbCdcAcmAdapter
from pcg_app.device_runtime import DeviceState, DeviceSamplePacket
from pcg_app.hardware_workflow import qualify_recording, ROOT
from pcg_app.state import ClientSession, StreamManager
from pcg_core.models import SampleBlock
from pcg_core.recording import SessionRecorder


def cli():
    spec=importlib.util.spec_from_file_location("morning_cli",ROOT/"tools/hardware/bringup.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manager_ready(tmp_path):
    manager=StreamManager(sessions_dir=tmp_path)
    manager.source_type="hardware"
    manager.sample_rate_hz=48000
    manager.is_streaming=True
    manager.device_runtime._state=DeviceState.STREAMING
    return manager


def test_known_answer_wire_to_product_recording_and_dsp_failure(tmp_path,monkeypatch):
    manager=manager_ready(tmp_path)
    sid=manager.start_recording()
    expected=np.array([-8388608,-1,0,1,8388607],dtype=np.int32)
    wire=codec.build_profile_b_packet(sequence_id=0,timestamp_us=0,sample_index_start=0,samples=expected)
    packet=codec.StreamingProtocolDecoder().feed_bytes(wire)[0]
    monkeypatch.setattr(manager.pipeline,"process_block",lambda block:(_ for _ in ()).throw(RuntimeError("DSP injected failure")))
    with pytest.raises(RuntimeError,match="DSP injected"):
        manager.ingest_device_packet_sync(DeviceSamplePacket(sequence=packet.sequence_id,timestamp_s=0,
            raw_samples=packet.raw_samples,crc_ok=packet.crc_ok,sample_rate_hz=packet.sample_rate_hz))
    metadata=manager.stop_recording(termination_reason="dsp_error")
    rate,saved=wavfile.read(tmp_path/sid/"raw.wav")
    assert rate==48000 and metadata.total_samples==5
    np.testing.assert_array_equal(np.rint(saved.astype(np.float64)*8388608).astype(np.int32),expected)


def test_worker_display_delivery_is_bounded_and_thread_safe():
    async def check():
        asyncio.get_running_loop().set_debug(True)
        received=[]
        async def send_json(frame): received.append(frame)
        client=ClientSession(SimpleNamespace(send_json=send_json))
        client.start()
        def producer():
            for i in range(1000): client.push_display_frame({"sample":i})
        worker=threading.Thread(target=producer)
        worker.start(); worker.join()
        assert client.dropped_display_frames==999
        assert client.queue.qsize()<=2
        for _ in range(10):
            await asyncio.sleep(.005)
            if received: break
        assert received==[{"sample":999}]
        client.stop()
    asyncio.run(check())


def test_normal_stop_finalizes_recording_and_repeated_session(tmp_path):
    app=create_app(sessions_dir=tmp_path/"sessions",assets_dir=tmp_path/"assets",analysis_dir=tmp_path/"analysis")
    ids=[]
    with TestClient(app) as client:
        assert client.post("/api/device/usb/connect",json={"port":"SIMULATED_ESP32_S3"}).status_code==200
        for _ in range(2):
            assert client.post("/api/device/usb/start",json={"target_samples":480000}).status_code==200
            rec=client.post("/api/recording/start",json={}).json()["session_id"]
            ids.append(rec)
            deadline=time.monotonic()+2
            while app.state.stream_manager.recorder.total_samples==0 and time.monotonic()<deadline: time.sleep(.01)
            assert client.post("/api/device/usb/stop").status_code==200
            assert not app.state.stream_manager.recorder.is_recording
            data=json.loads((tmp_path/"sessions"/rec/"session.json").read_text())
            assert data["acquisition_mode"]=="software_simulated" and data["device_info"] is None
            assert data["total_samples"]>0 and data["status"]=="finalized"
    assert ids[0]!=ids[1]
    assert not app.state.stream_manager.device_runtime.canonical_engine.is_running


def test_partial_serial_initialization_releases_handle(monkeypatch):
    import serial
    class BrokenSerial:
        closed=False
        def __init__(self,**kw): self.__dict__["dtr"]=False
        def __setattr__(self,name,value):
            if name=="dtr": raise OSError("control line failed")
            object.__setattr__(self,name,value)
        def close(self): self.closed=True
    handle=BrokenSerial()
    monkeypatch.setattr(serial,"Serial",lambda **kw:handle)
    with pytest.raises(ConnectionError,match="control line failed"):
        UsbCdcAcmAdapter().open("EXPLICIT_TEST_DOUBLE")
    assert handle.closed


def test_busy_selected_port_is_an_error_not_ready(tmp_path,monkeypatch):
    import serial
    monkeypatch.setattr(serial,"Serial",lambda **kw:(_ for _ in ()).throw(PermissionError("access denied: competing monitor")))
    app=create_app(sessions_dir=tmp_path/"sessions",assets_dir=tmp_path/"assets",analysis_dir=tmp_path/"analysis")
    with TestClient(app) as client:
        response=client.post("/api/device/usb/connect",json={"port":"EXPLICIT_TEST_DOUBLE"})
        assert response.status_code==400 and "access denied" in response.json()["detail"]
        assert client.get("/api/device/state").json()["state"]=="error"
        engine=app.state.stream_manager.device_runtime.canonical_engine
        assert engine.transport is None and not engine.is_running


def test_stop_storage_failure_cannot_leave_clean_acceptance(tmp_path,monkeypatch):
    app=create_app(sessions_dir=tmp_path/"sessions",assets_dir=tmp_path/"assets",analysis_dir=tmp_path/"analysis")
    with TestClient(app) as client:
        client.post("/api/device/usb/connect",json={"port":"SIMULATED_ESP32_S3"})
        client.post("/api/device/usb/start",json={"target_samples":480000})
        client.post("/api/recording/start",json={})
        manager=app.state.stream_manager
        monkeypatch.setattr(manager,"stop_recording",lambda:(_ for _ in ()).throw(OSError("disk full")))
        response=client.post("/api/device/usb/stop")
        assert response.status_code==500 and "disk full" in response.json()["detail"]
        engine=manager.device_runtime.canonical_engine
        assert engine.host_ingestion_errors==1
        assert engine.last_g1_evidence["verification_result"]=="FAIL"


def test_unexpected_callback_failure_releases_owner():
    engine=CanonicalSessionEngine(on_telemetry=lambda t:(_ for _ in ()).throw(RuntimeError("callback failed")))
    try:
        engine.connect("SIMULATED_ESP32_S3").result(timeout=3)
        engine.transport.device.status_interval_frames=1
        engine.start_acquisition().result(timeout=3)
        deadline=time.monotonic()+5
        while engine.is_running and time.monotonic()<deadline: time.sleep(.01)
        assert not engine.is_running and engine.transport is None
        assert any("callback failed" in e for e in engine.session.error_log)
        assert engine.last_g1_evidence["verification_result"]=="FAIL"
    finally:
        engine.disconnect().result(timeout=3)


def test_unsupported_firmware_never_ready():
    session=HostProtocolSession()
    session.initiate_handshake(123)
    ack=codec.HelloAck(nonce_echo=123,protocol_version_major=1,protocol_version_minor=0,
        supported_profiles_mask=2,supported_encodings_mask=1,hardware_sample_rate_hz=48000,
        firmware_version_major=99,firmware_version_minor=0,firmware_version_patch=0,
        max_frame_samples=256,device_uid_low=123,reserved=0,capability_flags=0)
    session.handle_incoming_bytes(codec.build_hello_ack_packet(ack))
    assert session.state==SessionState.ERROR
    assert "Unsupported firmware" in session.error_log[-1]


@pytest.mark.parametrize("signal",["zero","saturation","tone"])
def test_raw_microphone_screen_does_not_claim_physical_pass(tmp_path,signal):
    recorder=SessionRecorder(tmp_path)
    sid=recorder.start(acquisition_mode="software_simulated")
    x=np.zeros(48000,dtype=np.float32)
    if signal=="saturation": x[::2]=-1
    if signal=="tone": x=(.25*np.sin(2*np.pi*500*np.arange(48000)/48000)).astype(np.float32)
    recorder.record_block(SampleBlock(sequence=0,timestamp_s=0,sample_rate_hz=48000,samples=x))
    recorder.stop()
    report=qualify_recording(tmp_path/sid)
    assert report["constant_zero"]==(signal=="zero")
    assert report["saturation_fraction"]==(.5 if signal=="saturation" else 0)
    if signal=="tone":
        welch=report["welch"]
        assert abs(welch["frequencies_hz"][np.argmax(welch["power_fs2_per_hz"])]-500)<6
    assert report["physical_microphone"]=="NOT_VERIFIED_BY_THIS_ANALYSIS"
    (tmp_path/sid/"raw.wav").write_bytes(b"invalid")
    with pytest.raises(ValueError): qualify_recording(tmp_path/sid)


def test_existing_session_cannot_be_overwritten(tmp_path):
    recorder=SessionRecorder(tmp_path)
    existing=tmp_path/"preserve"; existing.mkdir()
    (existing/"session.json").write_text("original")
    with pytest.raises(FileExistsError): recorder.start(session_id="preserve")
    assert (existing/"session.json").read_text()=="original" and not recorder.is_recording


def test_recorder_concurrent_stop_cannot_create_inconsistent_wav(tmp_path):
    recorder=SessionRecorder(tmp_path)
    sid=recorder.start()
    block=SampleBlock(sequence=0,timestamp_s=0,sample_rate_hz=48000,samples=np.linspace(-.5,.5,256,dtype=np.float32))
    recorder.record_block(block)
    def produce():
        from pcg_core.recording import RecordingStateError
        for _ in range(100):
            try: recorder.record_block(block)
            except RecordingStateError: break
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(produce)
        meta=recorder.stop()
        future.result(timeout=2)
    rate,data=wavfile.read(tmp_path/sid/"raw.wav")
    assert rate==48000 and len(data)==meta.total_samples and len(data)%256==0


def test_boot_capture_cancel_does_not_open_port(monkeypatch,tmp_path):
    module=cli()
    monkeypatch.setattr(module,"confirm_port",lambda *args:None)
    import serial
    monkeypatch.setattr(serial,"Serial",lambda **kw:pytest.fail("cancelled capture opened port"))
    with pytest.raises(RuntimeError,match="cancelled"):
        module.capture_boot("COM_TEST",tmp_path/"boot.txt",prompt=lambda _:"no")


def test_passive_watch_observes_reenumeration_without_open(monkeypatch,capsys):
    module=cli()
    from pcg_app.diagnostics.usb_doctor import UsbDiscoveryDoctor
    snapshots=iter([[SimpleNamespace(to_dict=lambda:{"port_name":"COM1"})],[],[SimpleNamespace(to_dict=lambda:{"port_name":"COM2"})]])
    monkeypatch.setattr(UsbDiscoveryDoctor,"scan_ports",lambda self:next(snapshots))
    ticks=iter([0,0,1,2]); monkeypatch.setattr(module.time,"monotonic",lambda:next(ticks))
    monkeypatch.setattr(module.time,"sleep",lambda value:None)
    module.watch_ports(seconds=2)
    output=capsys.readouterr().out
    assert 'COM1' in output and 'COM2' in output and 'UNVERIFIED' in output


def test_missing_dependencies_preflight_has_actionable_output():
    result=subprocess.run([sys.executable,"-S",str(ROOT/"tools/hardware/preflight.py"),"--json"],capture_output=True,text=True,timeout=10)
    assert result.returncode==0
    report=json.loads(result.stdout)
    assert report["HARDWARE_TEST"]=="NOT_EXECUTED" and report["checks"]["numpy"]=="MISSING"


@pytest.mark.parametrize("setting",["CONFIG_SECURE_BOOT=y","CONFIG_SECURE_FLASH_ENC_ENABLED=y"])
def test_first_contact_rejects_security_configuration(setting):
    from pcg_app.hardware_workflow import check_build_config
    config=(ROOT/"firmware/sdkconfig.defaults").read_text()
    with pytest.raises(ValueError,match="Forbidden"):
        check_build_config(config+"\n"+setting)


def test_missing_inference_dependency_does_not_block_usb(tmp_path,monkeypatch):
    from pcg_app.ml.registry import ResearchModelRegistry
    monkeypatch.setattr(ResearchModelRegistry,"_torch_available",lambda self:False)
    app=create_app(sessions_dir=tmp_path/"sessions",assets_dir=tmp_path/"assets",analysis_dir=tmp_path/"analysis")
    with TestClient(app) as client:
        assert client.get("/api/health").status_code==200
        models=client.get("/api/research/ml/models").json()
        assert next(m for m in models if m["model_id"]=="af_murmur_mil_1.0")["status"]=="DEPENDENCY_MISSING"
        assert client.post("/api/research/ml/predict",json={"file_paths":["not_used.wav"],"model_id":"af_murmur_mil_1.0"}).status_code==503
        assert client.post("/api/device/usb/connect",json={"port":"SIMULATED_ESP32_S3"}).status_code==200


@pytest.mark.parametrize("arguments",[["--help"],["boot-log","--help"],["qualify","--help"],["watch","--seconds","0"],["g1"]])
def test_cli_argument_contract(arguments):
    result=subprocess.run([sys.executable,str(ROOT/"tools/hardware/bringup.py"),*arguments],capture_output=True,text=True,timeout=10)
    assert result.returncode==(0 if "--help" in arguments else 2)
    assert "Traceback" not in result.stderr
