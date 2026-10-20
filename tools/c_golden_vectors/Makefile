# Makefile for AuscultaForge Portable C Golden-Vector Tools
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -pedantic -O2
LDFLAGS ?= -lm

TARGET = golden_generator.exe
SRCS = golden_generator.c
HEADERS = golden_common.h

.PHONY: all clean run-audit generate

all: $(TARGET)

$(TARGET): $(SRCS) $(HEADERS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET) $(LDFLAGS)

run-audit: $(TARGET)
	./$(TARGET) --verify-types

generate: $(TARGET)
	mkdir -p fixtures
	./$(TARGET) --generate-all fixtures

clean:
	rm -f $(TARGET) *.o
	rm -rf fixtures
