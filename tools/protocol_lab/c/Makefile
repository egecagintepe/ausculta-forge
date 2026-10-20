# AuscultaForge Protocol Core C11 Makefile
# Toolchain: GCC / Clang C11

CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -O2 -Iinclude
LDFLAGS ?= -lm

SRC = src/waveform_gen.c src/ring_buffer.c src/packet_framing.c
TEST_SRC = tests/test_c_protocol_core.c $(SRC)
RUNNER_SRC = src/g1_sim_runner.c $(SRC)

TARGET_TEST = test_c_protocol_core.exe
TARGET_RUNNER = g1_sim_runner.exe

all: $(TARGET_TEST) $(TARGET_RUNNER)

$(TARGET_TEST): $(TEST_SRC)
	$(CC) $(CFLAGS) -o $@ $(TEST_SRC) $(LDFLAGS)

$(TARGET_RUNNER): $(RUNNER_SRC)
	$(CC) $(CFLAGS) -o $@ $(RUNNER_SRC) $(LDFLAGS)

test: $(TARGET_TEST)
	./$(TARGET_TEST)

clean:
	rm -f $(TARGET_TEST) $(TARGET_RUNNER) *.o

.PHONY: all test clean
