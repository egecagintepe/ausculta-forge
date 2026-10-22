# Compile the canonical serializer in place: no copied wire implementation.
idf_component_register(SRCS "g1.c" "acquisition.c" "../../../tools/protocol_lab/c/src/packet_framing.c"
    INCLUDE_DIRS "include" "../../../tools/protocol_lab/c/include")
