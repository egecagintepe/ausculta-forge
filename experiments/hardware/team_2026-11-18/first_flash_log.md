# ESP32-S3 G2 Candidate Flash Log

`	ext
esptool v5.6.0
Serial port COM4:
Connecting...
Connected to ESP32-S3 on COM4:
Chip type:          ESP32-S3 (QFN56) (revision v0.2)
Features:           Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB (AP_3v3)
Crystal frequency:  40MHz
USB mode:           USB-Serial/JTAG
MAC:                7c:e8:b1:aa:7c:c4

Uploading stub flasher...
Running stub flasher...
Stub flasher running.

Configuring flash size...

Writing 'C:\Users\User\Desktop\bitirme projesi\firmware\releases\g2_candidate_20261117\bootloader\bootloader.bin' at 0x00000000...
SHA digest in image updated.
Flash will be erased from 0x00000000 to 0x00005fff...
Compressed 21056 bytes to 13395...
Writing at 0x00005240 ============================== 100.0% 13.08kB/13.08kB [0s] 
Wrote 21056 bytes (13395 compressed) at 0x00000000 in 0.2 seconds (818.6 kbit/s).
Verifying written data...
Hash of data verified.

Writing 'C:\Users\User\Desktop\bitirme projesi\firmware\releases\g2_candidate_20261117\auscultaforge_g1.bin' at 0x00010000...
Flash will be erased from 0x00010000 to 0x00057fff...
Compressed 294880 bytes to 155602...
Writing at 0x0001bf36 ===                             10.5% 16.00kB/151.96kB [0s] 
Writing at 0x000241cf ======                          21.1% 32.00kB/151.96kB [0s] 
Writing at 0x0002a90f =========                       31.6% 48.00kB/151.96kB [0s] 
Writing at 0x0003093b ============>                   42.1% 64.00kB/151.96kB [0s] 
Writing at 0x00036eea ===============>                52.6% 80.00kB/151.96kB [0s] 
Writing at 0x0003ee59 ==================>             63.2% 96.00kB/151.96kB [0s] 
Writing at 0x000483d4 ======================          73.7% 112.00kB/151.96kB [0s] 
Writing at 0x0004e41b =========================       84.2% 128.00kB/151.96kB [1s] 
Writing at 0x00054ace ============================    94.8% 144.00kB/151.96kB [1s] 
Writing at 0x00057fe0 ============================== 100.0% 151.96kB/151.96kB [1s] 
Wrote 294880 bytes (155602 compressed) at 0x00010000 in 1.4 seconds (1677.9 kbit/s).
Verifying written data...
Hash of data verified.

Writing 'C:\Users\User\Desktop\bitirme projesi\firmware\releases\g2_candidate_20261117\partition_table\partition-table.bin' at 0x00008000...
Flash will be erased from 0x00008000 to 0x00008fff...
Compressed 3072 bytes to 105...
Writing at 0x00008c00 ============================== 100.0% 105B/105B [0s] 
Wrote 3072 bytes (105 compressed) at 0x00008000 in 0.0 seconds (1605.5 kbit/s).
Verifying written data...
Hash of data verified.

Hard resetting via RTS pin...
WARNING: Deprecated: Option '--flash_mode' is deprecated. Use '--flash-mode' instead.
WARNING: Deprecated: Option '--flash_freq' is deprecated. Use '--flash-freq' instead.
WARNING: Deprecated: Option '--flash_size' is deprecated. Use '--flash-size' instead.
WARNING: Deprecated: Command 'write_flash' is deprecated. Use 'write-flash' instead.

`
