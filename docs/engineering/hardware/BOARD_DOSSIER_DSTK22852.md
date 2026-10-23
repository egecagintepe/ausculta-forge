# DSTK22852 board identity dossier

Research date: 2026-10-23. This identifies the purchased product family, not the
physical unit. G0 requires the actual PCB photographs, markings and ROM queries.

## Sources and evidence boundaries

The [Direnc.net product page](https://www.direnc.net/esp32-s3-n16r8-wifi-bluetooth-board)
identifies SKU DSTK22852, N16R8, 16 MB flash and 8 MB PSRAM. Its marketing language
does not establish USB speed or connector wiring. Manufacturer/PCB revision is
not identified by a matching schematic on that page.

The seller's [first photograph](https://www.direnc.net/esp32-s3-n16r8-wifi-bluetooth-board-esp-board-direncnet-67898-22-K.jpg)
was inspected: two USB connector positions, two buttons, parallel headers and a
shielded antenna module are visible. Its 250-pixel image does not allow reliable
reading of the bridge IC, module suffix or every header. The
[second listing photograph](https://www.direnc.net/esp32-s3-n16r8-wifi-bluetooth-board-esp-board-direncnet-67899-22-K.jpg)
is a comparison reference, not evidence of the delivered unit.

Primary silicon/module authority:
[ESP32-S3-WROOM-1 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf).
Equivalent-board reference only:
[official DevKitC-1 v1.1 guide](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html).

| Fact | Classification | What still has to be checked |
| --- | --- | --- |
| Seller Direnc.net, SKU DSTK22852 | CONFIRMED seller record | Compare invoice/product bag |
| N16R8 / WROOM-1 target; 16 MB flash, 8 MB PSRAM | CONFIRMED intended variant | Read actual shield marking; query flash; inspect boot PSRAM log |
| ESP32-S3 dual-core LX7 family | CONFIRMED module specification | ROM chip identity before flash |
| Two connector positions | CONFIRMED listing photo | Actual connector types, labels and PCB routes |
| DevKitC-like layout | LIKELY visual resemblance | Never use reference pin order as actual PCB identity |
| USB D- GPIO19 / D+ GPIO20, full-speed 12 Mbit/s | CONFIRMED SoC mapping | Which connector reaches these signals |
| OTG and USB Serial/JTAG share internal PHY | CONFIRMED SoC constraint | No eFuse switch required; ROM/app can enumerate differently |
| External UART bridge | LIKELY on this board family | Read IC marking; compare USB Hardware IDs; no assumed CP210x/CH34x part |
| BOOT and RESET functions | CONFIRMED SoC/download workflow | Read button silkscreen before pressing; BOOT normally straps GPIO0 |
| Accessible GPIO headers | CONFIRMED listing appearance | Photograph actual labels/orientation; continuity to named nets |
| GPIO26..32 flash, GPIO33..37 octal memory reservations | CONFIRMED module-dependent reservation | Avoid all 26..37; N16R8 specifically uses 35..37 for octal PSRAM |
| GPIO0/3/45/46 strapping | CONFIRMED SoC constraint | Keep initial microphone profile away from straps |
| RGB LED | PHYSICAL_INSPECTION_REQUIRED | Official revisions use GPIO48 or GPIO38; neither is assumed for this PCB |
| PCB revision / manufacturer schematic | PHYSICAL_INSPECTION_REQUIRED | Record front/back text; obtain seller/manufacturer matching schematic |
| Power isolation / VBUS sense | PHYSICAL_INSPECTION_REQUIRED | Do not attach two powered USB cables on an unknown power design |

The RGB revision difference is documented in the
[Espressif development-board FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/hardware-related/development-board.html).
It illustrates why a board-family name is insufficient for a pin assignment.

## G0 identity record to complete in the laboratory

- Photographs: both PCB sides, module marking, bridge chip, connectors, BOOT/RESET,
  header labels, PCB revision and seller bag.
- One cable/connector at a time: save COM, VID/PID, serial number, Windows instance
  path and observed unplug/replug association. Enumeration is not HELLO verification.
- Through the selected programming route, save esptool chip-id and flash-id output.
  Silicon must be ESP32-S3, flash 16 MB; PSRAM still needs module/boot evidence.
- Confirm power/backfeed and VBUS handling before any second power source.
- Store these physical observations beside the generated board_identity.json.
  The CLI ROM report does not invent a PCB revision or PSRAM measurement.

No physical unit was identified in this development run. The observed workstation
ports were a Prolific PL2303 bridge and Intel SOL; neither was opened or treated
as an ESP32. An external bridge may connect many different devices.
