# Hardware As-Built Specification — 25 November 2026

## 1. ESP32-S3 & INMP441 I²S Pin Map

* **MCU Board:** ESP32-S3 (`UID: 0xb1aa7cc4`), USB CDC port `COM10` (`VID: 0x303a`, `PID: 0x4001`), G2 Firmware `1.1.0` (`source_mode=0`, `48000 Hz`, `S32_LE` 24-bit in 32-bit Philips stereo slot, Left slot `slot=0`).
* **INMP441 Connections:**
  * `VDD` $\rightarrow$ ESP32-S3 `3.3 V`
  * `GND` $\rightarrow$ ESP32-S3 `GND`
  * `L/R` $\rightarrow$ `GND` (selects Left I²S slot `slot=0`, matching `# CONFIG_AF_I2S_RIGHT_SLOT is not set`)
  * `SCK (BCLK)` $\rightarrow$ **`GPIO 4`** *(Note: initially miswired to `GPIO 3` in `session_20261125_074126_5317e121`, corrected to `GPIO 4` prior to `075205`)*
  * `WS (LRCLK)` $\rightarrow$ **`GPIO 5`**
  * `SD (DOUT)` $\rightarrow$ **`GPIO 6`**

---

## 2. Audio Excitation Chain (PC $\rightarrow$ AUX $\rightarrow$ PAM8403 $\rightarrow$ Exciter)

* **Audio Output Device:** Windows WinMM `dev[0]` (`Kulaklıklar (2- Realtek(R) Audio)`, 3.5 mm AUX TRS jack).
* **AUX TRS Conductor Identification:** Verified via multimeter before energizing PAM8403.
* **Amplifier:** PAM8403 Class-D stereo amplifier powered by an **independent regulated 5 V / 2 A DC supply** (isolated from ESP32-S3 USB power).
* **BTL Output Safety:** PAM8403 outputs (`OUT+` / `OUT-`) are Bridge-Tied Load (BTL). **Neither `OUT+` nor `OUT-` may ever be connected to `GND`.**
* **Transducer:** 30 mm / 12 Ω acoustic exciter driven by one PAM8403 BTL channel.

---

## 3. Acoustic Phantom & Stethoscope Coupling

* **Support Plate:** Suspended rigid cardboard support plate coupling the 12 Ω exciter to the silicone phantom (`trial_20261125_095717_275ae8`).
* **Phantom:** Cured experimental RTV-2 silicone phantom.
* **Stethoscope Coupling:** Dual-head stethoscope diaphragm placed on the silicone phantom; one branch of the Y-tubing coupled to the INMP441 sound port and sealed with electrical tape, with the unused Y-tubing branch closed/sealed.
* **Photographic References:** See [photos/README.md](photos/README.md) (laboratory photos pending local import into `docs/lab/2026-11-25/photos/`).

---

## 4. Known Mechanical Weaknesses

1. **Breadboard/Jumper Strain:** Moving the stethoscope tubing or reconfiguring the phantom/plate can tug INMP441 jumper wires, causing intermittent `0.0` I²S frames (observed in `100205`, `100347`, `100747`). Strain-relief taping or soldered headers are recommended.
2. **Cardboard Plate Damping & Repeatability:** Suspended cardboard introduces frequency-dependent damping and resonance (`~50–56 Hz`, `~386 Hz`) and imperfect mechanical repeatability when repositioned.

---

## 5. Safe Power-On / Power-Off Procedures

* **Power-On:** Verify `L/R = GND` and `OUT+`/`OUT-` BTL isolation $\rightarrow$ set Windows volume to `0%` / muted $\rightarrow$ connect ESP32-S3 USB (`COM10`) $\rightarrow$ power on independent 5 V PAM8403 supply $\rightarrow$ verify `HELLO` and `source_mode=0` $\rightarrow$ raise Windows volume gradually (10% $\rightarrow$ 20%).
* **Power-Off:** Mute Windows audio $\rightarrow$ power off PAM8403 5 V supply $\rightarrow$ disconnect `COM10` in software $\rightarrow$ unplug ESP32-S3 USB.
