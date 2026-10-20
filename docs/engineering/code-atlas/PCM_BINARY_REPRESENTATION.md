# AuscultaForge — PCM Binary Representation & Normalization Standards
**Document ID:** `AF-CODE-PCM-REPRESENTATION-V01`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Files:**
- `tools/c_golden_vectors/fixtures/manifest.json`
- `tools/c_golden_vectors/golden_common.h`
- `software/pcg_core/models.py`

---

## 1. Pulse Code Modulation (PCM) Fundamentals

Pulse Code Modulation (PCM) is the digital representation of a continuous analogue audio signal $x_a(t)$. The conversion process involves two discrete mathematical steps:
1. **Sampling:** Discretizing the continuous time axis at regular intervals $T_s = 1 / f_s$, yielding the discrete-time sequence $x[n] = x_a(n T_s)$. For AuscultaForge, $f_s = 48,000 \text{ Hz}$ ($T_s \approx 20.833 \ \mu\text{s}$).
2. **Quantization:** Discretizing the continuous amplitude range into one of $2^B$ discrete levels, where $B$ is the bit depth.

---

## 2. Dynamic Range & Bit Depth Comparison

The theoretical Signal-to-Quantization-Noise Ratio ($\text{SQNR}$) for an ideal $B$-bit uniform linear quantizer is given by:
$$\text{SQNR} \approx 6.02 \times B + 1.76 \ \text{dB}$$

| Format | Bit Depth ($B$) | Discrete Levels | Quantization Step ($\Delta$ at $\pm 1 \text{ V}$) | Theoretical Dynamic Range | AuscultaForge System Role |
|---|---|---|---|---|---|
| **`S16_LE`** | 16 bits | $65,536$ | $30.52 \ \mu\text{V}$ | $98.08 \ \text{dB}$ | Standard CD audio; optional lightweight export. |
| **`S24_LE`** | 24 bits | $16,777,216$ | $119.2 \ \text{nV}$ | $146.24 \ \text{dB}$ | INMP441 native ADC resolution; lossless scientific storage. |
| **`S32_LE`** | 32 bits | $4,294,967,296$ | $0.465 \ \text{nV}$ | $194.40 \ \text{dB}$ | Microcontroller bus container; wire transport container. |
| **`Float64`** | 53-bit mantissa | $\approx 9 \times 10^{15}$ | Variable | $> 300 \ \text{dB}$ | Host DSP processing (`SampleBlock.samples`). |

---

## 3. The `S32_LE` Container Format

The INMP441 sensor outputs 24 active bits. To transfer these across 32-bit hardware interfaces without endianness ambiguity, AuscultaForge adopts the **`S32_LE`** container convention:
* **Storage Size:** Exactly 4 bytes per sample (32 bits).
* **Byte Order:** Little-Endian (Least significant byte at lowest byte offset).
* **Two Supported Alignment Modes:**
  1. **MSB-Aligned (`msb`):** 24 audio bits occupy bits 31..8; bits 7..0 are padded with zeros.
  2. **LSB-Aligned (`lsb`):** 24 audio bits occupy bits 23..0; bits 31..24 replicate bit 23 (sign extension).

### 3.1 Comprehensive Value Representation Table

The following table documents the exact bit-level representation of critical boundary values across binary, hexadecimal, and floating-point representations:

| Mathematical Description | 24-bit Decimal | MSB-Aligned Hex (32-bit) | LSB-Aligned Hex (32-bit) | Little-Endian Wire Bytes (MSB) | Little-Endian Wire Bytes (LSB) | Normalized Float64 |
|---|---|---|---|---|---|---|
| **Positive Full-Scale** | $+8,388,607$ | `0x7FFFFF00` | `0x007FFFFF` | `00 FF FF 7F` | `FF FF 7F 00` | $+0.99999988$ |
| **Positive Half-Scale** | $+4,194,304$ | `0x40000000` | `0x00400000` | `00 00 00 40` | `00 00 40 00` | $+0.50000000$ |
| **Smallest Positive** | $+1$ | `0x00000100` | `0x00000001` | `00 01 00 00` | `01 00 00 00` | $+0.00000012$ |
| **Digital Zero** | $0$ | `0x00000000` | `0x00000000` | `00 00 00 00` | `00 00 00 00` | $0.00000000$ |
| **Smallest Negative** | $-1$ | `0xFFFFFF00` | `0xFFFFFFFF` | `00 FF FF FF` | `FF FF FF FF` | $-0.00000012$ |
| **Negative Half-Scale** | $-4,194,304$ | `0xC0000000` | `0xFFC00000` | `00 00 00 C0` | `00 00 C0 FF` | $-0.50000000$ |
| **Negative Full-Scale** | $-8,388,608$ | `0x80000000` | `0xFF800000` | `00 00 00 80` | `00 00 80 FF` | $-1.00000000$ |

---

## 4. Normalization to IEEE-754 Floating-Point

To perform digital filtering, Fourier analysis, and envelope extraction in Python, raw integers must be normalized to dimensionless floating-point values $y[n] \in [-1.0, +1.0)$.

### 4.1 Normalization Mathematics
* **For MSB-Aligned Samples ($x_{\text{msb}} \in [-2^{31}, +2^{31}-1]$):**
  $$y[n] = \frac{x_{\text{msb}}[n]}{2^{31}} = \frac{x_{\text{msb}}[n]}{2147483648.0}$$
* **For LSB-Aligned Samples ($x_{\text{lsb}} \in [-2^{23}, +2^{23}-1]$):**
  $$y[n] = \frac{x_{\text{lsb}}[n]}{2^{23}} = \frac{x_{\text{lsb}}[n]}{8388608.0}$$

### 4.2 Decibels Relative to Full Scale (dBFS)
The amplitude of an audio signal relative to the maximum representable digital peak is expressed in **dBFS** (decibels relative to full scale):
$$\text{Peak Level (dBFS)} = 20 \log_{10} (|y[n]|)$$
$$\text{RMS Level (dBFS)} = 20 \log_{10} \left( \sqrt{\frac{1}{N} \sum_{n=0}^{N-1} y^2[n]} \right)$$

* A full-scale sine wave has a peak level of $0 \text{ dBFS}$ and an RMS level of $-3.01 \text{ dBFS}$.
* Any signal exceeding $0 \text{ dBFS}$ suffers digital hard clipping (clipping distortion).

---

## 5. Golden Fixtures & Automated Verification

In `tools/c_golden_vectors/fixtures/`, binary golden vectors (`.bin`) and CSV reference tables (`.csv`) are generated deterministically by C11 routines:
* `counter_ramp_512s_lsb.bin` / `counter_ramp_512s_msb.bin`: Ramp vectors from $-256$ to $+255$.
* `sine_100hz_48khz_512s_lsb.bin` / `sine_100hz_48khz_512s_msb.bin`: 512 samples of a 100 Hz tone.
* `boundary_stress_lsb.bin` / `boundary_stress_msb.bin`: Extreme positive, negative, and zero transitions.

Automated Python test `software/tests/test_c_golden_vectors.py` parses these binary files and asserts bit-for-bit equivalence against Python normalization routines with floating-point tolerance $\epsilon = 0.0$.
