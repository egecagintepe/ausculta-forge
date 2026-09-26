# AuscultaForge — Hardware Directory

This directory hosts hardware designs, mechanical specifications, PCB schematics, and acoustic modeling.

## Responsibilities & Ownership
- **Digital Hardware, Schematics & PCB Layout:** Ozan
  - Component selection (ESP32-S3-WROOM dev board, LDO, connectors)
  - Altium schematic capture and ERC verification
  - Native USB hardware routing and termination
  - I2S microphone routing with configurable ~6-pin header (supporting INMP441, ICS-43434/43432 swapping)
  - Custom PCB layout and design rule verification (tape-out after dev-board phantom milestone)
- **Power Management & Acoustic Phantom System:** Kaan
  - MCP73831 + PFET + Schottky power-path reference design & integration support
  - Physical acoustic phantom test chamber, speaker/exciter setup
  - Acoustic and mechanical coupling between exciter and candidate microphones
  - Reference PCG playback system and repeatable phantom test protocols
