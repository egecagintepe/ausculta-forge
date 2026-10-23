"""Compile actual firmware core; verify using the unchanged production Python host.

Run from repository root: .venv/Scripts/python -m pytest firmware/tests -q
This is SOFTWARE VERIFIED evidence, never physical USB or ESP-IDF build evidence.
"""
import binascii
import ctypes
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

import numpy as np
import pytest

from pcg_app.canonical import codec as c
from pcg_app.canonical.session import HostProtocolSession, SessionState

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def lib(tmp_path_factory):
    gcc = shutil.which("gcc")
    assert gcc, "Install GCC to execute firmware host tests"
    directory = tmp_path_factory.mktemp("g1")
    binary = directory / ("g1.dll" if os.name == "nt" else "g1.so")
    subprocess.run([
        gcc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-shared",
        *([] if os.name == "nt" else ["-fPIC"]),
        str(ROOT / "firmware/tests/bridge.c"),
        str(ROOT / "firmware/components/g1/g1.c"),
        str(ROOT / "firmware/components/g1/acquisition.c"),
        str(ROOT / "tools/protocol_lab/c/src/packet_framing.c"),
        "-I" + str(ROOT / "firmware/components/g1/include"),
        "-I" + str(ROOT / "tools/protocol_lab/c/include"), "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    dll_dir = os.add_dll_directory(str(Path(gcc).parent)) if os.name == "nt" else None
    api = ctypes.CDLL(str(binary))
    api.test_init.argtypes = [ctypes.c_uint64]
    api.test_rx.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint64]
    api.test_tick.argtypes = [ctypes.c_uint64, ctypes.c_int]
    api.test_link.argtypes = [ctypes.c_int]
    api.test_read.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    api.test_read.restype = ctypes.c_size_t
    api.g1_sample.argtypes = [ctypes.c_uint64]
    api.g1_sample.restype = ctypes.c_int32
    api.acquisition_read.argtypes = [ctypes.c_uint8, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_uint16]
    yield api
    if dll_dir:
        dll_dir.close()


class Device:
    def __init__(self, lib):
        self.lib = lib
        lib.test_init(0x4155534300000000)

    def rx(self, data, now=1_000_000, fragment=7):
        for offset in range(0, len(data), fragment):
            chunk = bytes(data[offset:offset + fragment])
            self.lib.test_rx(chunk, len(chunk), now)

    def tick(self, now, drained=True):
        self.lib.test_tick(now, drained)

    def read(self, cap=1068):
        result = bytearray()
        buffer = ctypes.create_string_buffer(1068)
        while n := self.lib.test_read(buffer, cap):
            result.extend(buffer.raw[:n])
        return bytes(result)

    def packets(self):
        return c.StreamingProtocolDecoder().feed_bytes(self.read())


def start(device, target=480000):
    host = HostProtocolSession()
    device.rx(host.initiate_handshake(0x12345678))
    host.handle_incoming_bytes(device.read())
    assert host.state == SessionState.READY
    device.rx(host.request_start(target_samples=target, source_mode=1))
    host.handle_incoming_bytes(device.read())
    assert host.state == SessionState.STREAMING
    return host


def test_full_g1_against_real_host(lib):
    device = Device(lib)
    host = start(device)
    assert host.active_session_id != 0
    # No block may be emitted ahead of its complete-block deadline.
    device.tick(1_005_332)
    assert device.read() == b""
    audio = []
    statuses = 0
    for elapsed in range(0, 10_000_001, 1000):
        device.tick(1_000_000 + elapsed)
        wire = device.read()
        for offset in range(0, len(wire), 83):
            for packet in host.handle_incoming_bytes(wire[offset:offset+83]):
                assert packet.crc_ok
                if packet.msg_type == c.MSG_TYPE_AUDIO_DATA:
                    audio.append(packet)
                    assert packet.sample_count == 256
                    assert packet.flags & c.FRAME_FLAG_SIMULATED_SOURCE
                    assert packet.sequence_id == len(audio)-1
                    assert packet.sample_index_start == (len(audio)-1)*256
                    assert packet.timestamp_us == 1_000_000 + packet.sample_index_start*1_000_000//48000
                elif packet.msg_type == c.MSG_TYPE_HEARTBEAT_STATUS:
                    statuses += 1
    assert len(audio) == 1875 and statuses > 0
    assert host.host_samples_accepted == 480000
    indices = np.arange(480000, dtype=np.int64)
    expected = (indices*16807+7) % (1 << 24)
    expected = np.where(expected >= (1 << 23), expected-(1 << 24), expected)
    np.testing.assert_array_equal(np.concatenate([p.raw_samples for p in audio]), expected)
    device.tick(11_001_000)
    assert device.read() == b""  # No unsolicited STOP_ACK.
    device.rx(host.request_stop(), now=11_001_000)
    device.tick(11_001_000, drained=False)
    assert device.read() == b""
    device.tick(11_002_000)
    host.handle_incoming_bytes(device.read())
    assert host.state == SessionState.COMPLETE
    t = host.final_telemetry
    assert t.generated_samples == t.fully_queued_samples == 480000
    assert t.audio_frames_queued == 1875 and t.audio_bytes_queued == 1875*1068
    assert t.dropped_samples == t.error_code == t.usb_timeout_events == 0
    assert t.stop_reason == 0
    assert lib.test_state() == 7


def test_reject_invalid_state_mode_config_and_session(lib):
    device = Device(lib)
    request = c.StartReq(48000, 480000, 1, 1, 1, 2)
    device.rx(c.build_start_req_packet(request))
    assert device.packets()[0].control_payload.error_code == 1
    device.rx(c.build_hello_req_packet(0xffffffff))
    assert device.packets()[0].control_payload.nonce_echo == 0xffffffff
    for config in [c.StartReq(48000,480000,0,1,1,2), c.StartReq(48000,480000,2,1,1,2)]:
        device.rx(c.build_start_req_packet(config))
        assert device.packets()[0].control_payload.error_code == 2
    for config in [c.StartReq(44100,480000,1,1,1,2), c.StartReq(48000,0,1,1,1,2),
                   c.StartReq(48000,480001,1,1,1,2), c.StartReq(48000,480000,1,2,1,2),
                   c.StartReq(48000,480000,1,1,2,2), c.StartReq(48000,480000,1,1,1,1)]:
        device.rx(c.build_start_req_packet(config))
        assert device.packets()[0].control_payload.error_code == 4
    host = start(device)
    device.rx(c.build_stop_req_packet(host.active_session_id+1))
    assert device.packets()[0].control_payload.error_code == 3
    assert lib.test_state() in (4,5)


def test_crc_malformed_fragmentation_noise_and_timeout(lib):
    device = Device(lib)
    hello = c.build_hello_req_packet(123)
    bad = bytearray(hello)
    bad[-1] ^= 1
    device.rx(b"garbage" + bad + hello, fragment=1)
    assert device.packets()[0].control_payload.nonce_echo == 123
    assert lib.test_crc_errors() == 1
    for offset, value in [(4,2), (5,0x99), (32,1), (35,16), (36,2), (37,2)]:
        malformed = bytearray(hello)
        malformed[offset] = value
        malformed[-4:] = struct.pack("<I", binascii.crc32(malformed[:-4]))
        device.rx(malformed + hello, fragment=256)
        assert device.packets()[0].msg_type == c.MSG_TYPE_HELLO_ACK
    device.rx(hello[:20])
    device.tick(2_000_001)
    device.rx(hello, now=2_000_002)
    assert device.packets()[0].control_payload.nonce_echo == 123
    assert lib.test_malformed() >= 7


def test_stop_during_backpressure_and_partial_write(lib):
    device = Device(lib)
    host = start(device)
    for elapsed in range(0, 100001, 1000):
        device.tick(1_000_000+elapsed)
    device.rx(host.request_stop(), now=1_100_001)
    assert lib.test_state() == 6
    # Drain existing audio before STOP_ACK, using partial writes.
    host.handle_incoming_bytes(device.read(cap=31))
    device.tick(1_100_002, drained=False)
    assert device.read() == b""
    device.tick(1_100_003)
    host.handle_incoming_bytes(device.read())
    assert host.state == SessionState.COMPLETE
    t = host.final_telemetry
    assert t.dropped_samples > 0 and t.ring_overflow_events > 0
    assert t.generated_samples == t.fully_queued_samples+t.dropped_samples
    assert t.usb_partial_write_events > 0
    assert t.stop_reason == 1


def test_disconnect_fresh_session_timeout_and_control_overload(lib):
    device = Device(lib)
    host = start(device)
    previous = host.active_session_id
    lib.test_link(0)
    device.tick(9_000_000)
    assert device.read() == b""
    lib.test_link(1)
    device.rx(c.build_start_req_packet(c.StartReq(48000,256,1,1,1,2)))
    assert device.packets()[0].control_payload.error_code == 1
    host = start(device, target=256)
    assert host.active_session_id != previous
    device.tick(41_000_001)
    assert lib.test_state() == 1
    assert device.read() == b""
    device.rx(c.build_hello_req_packet(1)*9, fragment=256)
    assert lib.test_overflows() == 1
    assert device.read() == b""
    device.rx(c.build_hello_req_packet(2))
    assert device.packets()[0].control_payload.nonce_echo == 2


def test_wrong_nonce_is_rejected_by_real_host(lib):
    device = Device(lib)
    host = HostProtocolSession()
    host.initiate_handshake(1)
    device.rx(c.build_hello_req_packet(2))
    host.handle_incoming_bytes(device.read())
    assert host.state == SessionState.ERROR


def test_acquisition_boundary_and_session_counter_wrap(lib):
    buffer = (ctypes.c_int32*256)()
    assert lib.acquisition_read(0,0,buffer,256) == -2
    assert lib.acquisition_read(1,0,None,256) == -1
    assert lib.acquisition_read(1,0,buffer,0) == -2
    assert lib.acquisition_read(1,0,buffer,257) == -2
    assert lib.acquisition_read(1,500,buffer,1) == 0 and buffer[0] == -8373709
    device = Device(lib)
    lib.test_init(0xffffffffffffffff)
    host = start(device)
    assert host.active_session_id == 1


def test_partial_final_block_and_restart(lib):
    device = Device(lib)
    host = start(device, target=257)
    for now in [1_005_333, 1_005_354]:
        device.tick(now)
        host.handle_incoming_bytes(device.read())
    assert host.host_samples_accepted == 257
    device.rx(host.request_stop())
    device.tick(1_006_000)
    host.handle_incoming_bytes(device.read())
    assert host.state == SessionState.COMPLETE
    previous = host.active_session_id
    host = start(device)
    assert host.active_session_id != previous


def test_frozen_golden_vectors_and_corrupt_output(lib):
    vectors = json.loads((Path(__file__).parent / "golden_vectors.json").read_text())
    for vector in vectors.values():
        wire = bytes.fromhex(vector)
        packets = c.StreamingProtocolDecoder().feed_bytes(wire)
        assert len(packets) == 1 and packets[0].crc_ok
        corrupt = bytearray(wire)
        corrupt[40] ^= 0x80
        assert not any(p.crc_ok for p in c.StreamingProtocolDecoder().feed_bytes(corrupt))
    device = Device(lib)
    device.rx(bytes.fromhex(vectors["hello_req"]))
    assert device.read().hex() == vectors["hello_ack"]
    device.rx(bytes.fromhex(vectors["start_req"]))
    assert device.read().hex() == vectors["start_ack"]
    device.tick(1_005_333)
    assert device.read().hex() == vectors["audio"]
    device.rx(bytes.fromhex(vectors["stop_req"]))
    device.tick(1_006_000)
    assert device.read().hex() == vectors["stop_ack"]
    for index, value in [(0,7),(1,16814),(500,-8373709),(1000,29791),(479999,-2497696)]:
        assert lib.g1_sample(index) == value


def test_boundary_vectors_match_c_serializer_and_reject_truncation(lib):
    vectors=json.loads((Path(__file__).parent/"golden_vectors.json").read_text())
    build=lib.packet_build_profile_b
    build.argtypes=[ctypes.c_uint32,ctypes.c_uint64,ctypes.c_uint64,ctypes.POINTER(ctypes.c_int32),
        ctypes.c_uint16,ctypes.c_uint32,ctypes.c_uint8,ctypes.c_uint16,ctypes.c_uint8,
        ctypes.c_uint16,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    for name in ("signed_boundaries","sequence_wrap_before","sequence_wrap_after","partial_final"):
        expected=bytes.fromhex(vectors[name])
        decoded=c.StreamingProtocolDecoder().feed_bytes(expected)[0]
        samples=(ctypes.c_int32*decoded.sample_count)(*decoded.raw_samples)
        output=ctypes.create_string_buffer(1068); size=ctypes.c_size_t()
        assert build(decoded.sequence_id,0,0,samples,decoded.sample_count,48000,24,1,1,0,output,1068,ctypes.byref(size))==0
        assert output.raw[:size.value]==expected
        for cut in (1,39,40,len(expected)-1):
            assert c.StreamingProtocolDecoder().feed_bytes(expected[:cut])==[]


def test_corrupted_start_stop_do_not_change_session(lib):
    device = Device(lib)
    device.rx(c.build_hello_req_packet(9))
    device.read()
    request = bytearray(c.build_start_req_packet(c.StartReq(48000,480000,1,1,1,2)))
    request[-1] ^= 1
    device.rx(request)
    assert device.read() == b"" and lib.test_state() == 3
    host = start(device)
    request = bytearray(c.build_stop_req_packet(host.active_session_id))
    request[-1] ^= 1
    device.rx(request)
    assert device.read() == b"" and lib.test_state() == 4
    assert lib.test_crc_errors() == 2


def test_real_time_core_against_existing_acceptance_validator(lib, tmp_path):
    sys.path.insert(0, str(ROOT / "tools/protocol_lab/module_b_package"))
    from verify_g1_bringup import execute_physical_g1_protocol

    class FirmwareTransport:
        def __init__(self):
            self.device = Device(lib)
            self.origin = time.perf_counter_ns()

        def now(self):
            return (time.perf_counter_ns()-self.origin)//1000

        def write(self, wire):
            self.device.rx(wire, now=self.now())
            return len(wire)

        def read(self, max_bytes=1024):
            self.device.tick(self.now())
            # Preserve unread bytes, as a real CDC byte stream does.
            buffer = ctypes.create_string_buffer(max_bytes)
            n = lib.test_read(buffer, max_bytes)
            return buffer.raw[:n]

    passed, verdict, metrics = execute_physical_g1_protocol(
        FirmwareTransport(), duration_s=10, is_physical=False,
    )
    assert passed, metrics.get("failure_reasons")
    assert verdict == "SOFTWARE_SIMULATION_PASS"
    assert metrics["host_samples_accepted"] == 480000
    assert metrics["host_frames_accepted"] == 1875
    assert 10 <= metrics["elapsed_seconds"] < 15
    (tmp_path / "firmware_g1_software_evidence.json").write_text(json.dumps(metrics, indent=2))


def test_i2s_conversion_and_independent_live_adapter(lib):
    lib.pcm24_from_i2s.argtypes=[ctypes.c_uint32]
    lib.pcm24_from_i2s.restype=ctypes.c_int32
    for word, expected in [(0,0),(0x100,1),(0x7fffff00,8388607),
                            (0x80000000,-8388608),(0xffffff00,-1),(0xffffffab,-1)]:
        assert lib.pcm24_from_i2s(word)==expected
    device=Device(lib)
    lib.test_enable_live()
    host=HostProtocolSession()
    device.rx(host.initiate_handshake(3)); host.handle_incoming_bytes(device.read())
    device.rx(host.request_start(target_samples=256,source_mode=0))
    host.handle_incoming_bytes(device.read())
    device.tick(1006000)
    packets=host.handle_incoming_bytes(device.read())
    assert packets[0].raw_samples[0]==-8388608
    assert packets[0].flags & c.FRAME_FLAG_SIMULATED_SOURCE == 0
    device.rx(host.request_stop()); device.tick(1007000)
    host.handle_incoming_bytes(device.read())
    assert host.state==SessionState.COMPLETE
    assert host.final_telemetry.generated_samples==256
    assert host.final_telemetry.dropped_samples==0


def test_live_source_does_not_erase_usb_overflow_counters(lib):
    device=Device(lib)
    lib.test_enable_live()
    host=HostProtocolSession()
    device.rx(host.initiate_handshake(4)); host.handle_incoming_bytes(device.read())
    device.rx(host.request_start(target_samples=480000,source_mode=0))
    host.handle_incoming_bytes(device.read())
    for now in range(1006000,1026000,1000): device.tick(now)
    device.rx(host.request_stop()); host.handle_incoming_bytes(device.read())
    device.tick(1027000); host.handle_incoming_bytes(device.read())
    t=host.final_telemetry
    assert t.ring_overflow_events>0 and t.dropped_samples>0
    assert t.generated_samples==t.fully_queued_samples+t.dropped_samples


def test_acquisition_failure_is_not_a_usb_timeout(lib):
    device=Device(lib)
    lib.test_enable_live()
    host=HostProtocolSession()
    device.rx(host.initiate_handshake(5)); host.handle_incoming_bytes(device.read())
    device.rx(host.request_start(target_samples=256,source_mode=0))
    host.handle_incoming_bytes(device.read())
    lib.test_fail_live(); device.tick(1006000)
    assert device.packets()[0].control_payload.error_code==6
    device.rx(c.build_stop_req_packet(host.active_session_id)); device.tick(1007000)
    t=device.packets()[0].telemetry
    assert t.error_code==6 and t.usb_timeout_events==0


def test_supported_i2s_start_failure_is_acquisition_fault_and_g1_still_works(lib):
    device=Device(lib)
    lib.test_enable_live()
    host=HostProtocolSession()
    device.rx(host.initiate_handshake(6)); host.handle_incoming_bytes(device.read())
    lib.test_fail_live_start()
    device.rx(host.request_start(target_samples=256,source_mode=0))
    packet=device.packets()[0]
    assert packet.control_payload.error_code==6 and lib.test_state()==3
    host=start(device,target=256)
    device.tick(1006000)
    host.handle_incoming_bytes(device.read())
    assert host.host_samples_accepted==256 and host.host_sample_value_errors==0
