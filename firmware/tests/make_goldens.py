"""Independent struct/CRC oracle; regenerate only after reviewing the wire contract."""
import binascii
import json
from pathlib import Path
import struct


def frame(opcode, payload, flags=1, sequence=0, time=0, count=0):
    header = struct.pack("<IBBHIIQQHBBBBH", 0xAF534331, 1, opcode, flags,
                         sequence, 48000, time, 0, count, 24, 32, 1, 1, 0)
    assert len(header) == 40
    body = header+payload
    return (body+struct.pack("<I", binascii.crc32(body))).hex()


if __name__ == "__main__":
    sid = 0x4155534300000001
    samples = [(n*16807+7) % (1 << 24) for n in range(256)]
    samples = [u-(1 << 24) if u >= (1 << 23) else u for u in samples]
    telemetry = struct.pack("<QQQQIIIIIIQII", sid,256,256,0,1,0,0,0,0,0,1068,0,0)
    vectors = {
        "hello_req": frame(0x10, struct.pack("<I", 0x12345678)),
        "hello_ack": frame(0x11, struct.pack("<IBBBBI4BHHI", 0x12345678,1,0,2,1,
                                              48000,1,1,0,0,256,0,0x53433332)),
        "start_req": frame(3, struct.pack("<IQBBBB", 48000,256,1,1,1,2)),
        "start_ack": frame(4, struct.pack("<QQIQBBBB",sid,1000000,48000,256,1,1,1,2),
                           flags=0x81, time=1000000),
        "audio": frame(1, struct.pack("<256i", *samples), flags=0xa1, time=1000000,count=256),
        "status": frame(2, telemetry, flags=0x81,sequence=1,time=1006000),
        "stop_req": frame(5, struct.pack("<Q", sid)),
        "stop_ack": frame(6, telemetry, sequence=1),
        "error": frame(0x0f, struct.pack("<II",2,0)),
        "signed_boundaries": frame(1, struct.pack("<5i", -8388608,-1,0,1,8388607),count=5),
        "sequence_wrap_before": frame(1, struct.pack("<i",7),sequence=0xffffffff,count=1),
        "sequence_wrap_after": frame(1, struct.pack("<i",7),sequence=0,count=1),
        "partial_final": frame(1, struct.pack("<3i",7,16814,33621),count=3),
    }
    (Path(__file__).parent / "golden_vectors.json").write_text(json.dumps(vectors,indent=2)+"\n")
