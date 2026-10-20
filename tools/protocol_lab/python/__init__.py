"""AuscultaForge Protocol Laboratory & C/Python Interoperability Core.

Course: EEE495 / EEE496 Senior Design Project — AuscultaForge
Module: C (Computer Application / Software Integration)
Author: Ege Çağın Tepe (Module C)
Reviewer: Ozan (Module B)
"""

from .protocol_codec import (
    StreamingProtocolDecoder,
    build_profile_a_packet,
    build_profile_b_packet,
    crc16_ccitt,
    crc32_ieee,
    DecodedPacket,
    PROFILE_A_MAGIC,
    PROFILE_B_MAGIC,
    NOMINAL_SAMPLE_RATE_HZ,
    PROFILE_B_SAMPLES_PER_FRAME,
)
from .protocol_validator import ProtocolValidator

__all__ = [
    "StreamingProtocolDecoder",
    "build_profile_a_packet",
    "build_profile_b_packet",
    "crc16_ccitt",
    "crc32_ieee",
    "DecodedPacket",
    "ProtocolValidator",
    "PROFILE_A_MAGIC",
    "PROFILE_B_MAGIC",
    "NOMINAL_SAMPLE_RATE_HZ",
    "PROFILE_B_SAMPLES_PER_FRAME",
]
