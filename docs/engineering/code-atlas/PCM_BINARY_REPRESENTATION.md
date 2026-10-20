# AuscultaForge — PCM Binary Representation & Normalization Standards
**Document ID:** `AF-CODE-PCM-REPRESENTATION-V02`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Files:**
- `tools/c_golden_vectors/fixtures/manifest.json`
- `tools/c_golden_vectors/golden_common.h`
- `software/pcg_core/models.py` (`SampleBlock`)
- `software/pcg_app/device_runtime.py` (`packet_to_sample_block`)

---

## 1. Pulse Code Modulation (PCM) Fundamentals

Pulse Code Modulation (PCM) represents continuous acoustic pressure signals $p(t)$ as discrete digital sequences. This conversion involves two discrete operations:
1. **Sampling:** Discretizing the continuous time axis at regular intervals $T_s = 1 / f_s$, yielding the discrete-time sequence $x[n] = x(n T_s)$. In AuscultaForge, the baseline sampling frequency is $f_s = 48,000 \text{ Hz}$ ($T_s \approx 20.833 \ \mu\text{s}$).
2. **Quantization:** Discretizing continuous sample amplitudes into one of $2^B$ discrete levels, where $B$ is the nominal bit depth.

---

## 2. Theoretical SQNR vs. Real Physical Dynamic Range

A fundamental engineering distinction must be maintained between **mathematical quantizer limits** and **physical sensor performance**:

### 2.1 Theoretical Quantizer SQNR
For an ideal, mathematically perfect $B$-bit uniform linear quantizer with a full-scale sinusoidal input, the Signal-to-Quantization-Noise Ratio ($\text{SQNR}$) is given by:
$$\text{SQNR} = 6.02 \times B + 1.76 \ \text{dB}$$

* For $B = 16\text{ bits}$: $\text{SQNR}_{\text{ideal}} \approx 98.09 \ \text{dB}$.
* For $B = 24\text{ bits}$: $\text{SQNR}_{\text{ideal}} \approx 146.24 \ \text{dB}$.
* For $B = 32\text{ bits}$: $\text{SQNR}_{\text{ideal}} \approx 194.40 \ \text{dB}$.

### 2.2 Physical Sensor Dynamic Range (INMP441 MEMS)
A digital 24-bit I2S output word does **not** imply that the physical microphone achieves $146.24 \ \text{dB}$ of usable dynamic range. In real physical transducers, thermal Brownian motion of the diaphragm, pre-amplifier Johnson noise, and internal $\Sigma\Delta$ modulator noise establish a physical noise floor well above the 24th bit:

* **INMP441 Datasheet Specifications:**
  - **Acoustic Overload Point (AOP):** $120 \ \text{dB SPL}$ (maximum input sound pressure at $10\%$ THD).
  - **Signal-to-Noise Ratio (SNR):** $61 \ \text{dBA}$ (measured at $1 \ \text{kHz}, 94 \ \text{dB SPL}$).
  - **Equivalent Input Noise (EIN):** $94 \ \text{dB SPL} - 61 \ \text{dBA} = 33 \ \text{dBA SPL}$.
  - **Usable Acoustic Dynamic Range:** $\text{AOP} - \text{EIN} = 120 - 33 = 87 \ \text{dB}$.
* **Effective Number of Bits (ENOB):**
  $$\text{ENOB} = \frac{\text{Dynamic Range} - 1.76}{6.02} \approx \frac{87 - 1.76}{6.02} \approx 14.16 \ \text{bits}$$
  Consequently, approximately 9 to 10 of the least significant bits in the 24-bit word carry acoustic and electrical thermal noise, not clean physiological signal. The 24-bit container is selected to ensure that digital quantization noise remains negligible compared to physical microphone noise.

### 2.3 Quantization Step Size ($\Delta$)
The step size between adjacent discrete codes is dimensionless in the digital domain ($\Delta = 1 \ \text{LSB}$). It can only be expressed in physical units (volts or nanovolts) when an explicit analog reference voltage $V_{\text{ref}}$ is defined:
$$\Delta = \frac{2 V_{\text{ref}}}{2^B}$$
*For example, if an external ADC uses $V_{\text{ref}} = 1.0 \ \text{V}$ ($\pm 1.0 \ \text{V}$ range, $2.0 \ \text{V}_{\text{p-p}}$):*
- 16-bit: $\Delta = 2.0 / 65536 \approx 30.52 \ \mu\text{V}$.
- 24-bit: $\Delta = 2.0 / 16777216 \approx 119.2 \ \text{nV}$.
Without an explicit reference voltage, quoting step sizes in nanovolts is physically meaningless.

---

## 3. Data Representation Across System Layers

| System Layer | Representation | Bit Depth / Format | Physical / Numerical Meaning |
| :--- | :--- | :--- | :--- |
| **INMP441 Microphone** | I2S Serial Stream | 24-bit active data | Two's-complement integer output from internal $\Sigma\Delta$ ADC |
| **ESP32-S3 DMA Buffer** | RAM array | 32-bit container (`S32_LE`) | 24-bit integer packed into 32-bit slot (MSB- or LSB-aligned) |
| **Proposed USB Protocol** | CDC-ACM Packet | 32-bit container (`S32_LE`) | Frame of 256 or 512 raw integer samples per packet |
| **Host Ingestion (`pcg_app`)** | `DeviceSamplePacket` | `np.int32` | Raw integer codes preserved for sequence and drop checking |
| **Host Pipeline (`pcg_core`)** | `SampleBlock.samples` | `np.float32` | Normalized dimensionless audio in $[-1.0, 1.0]$ |
| **Persistent Storage** | `raw.wav` | IEEE `float32` | Normalized linear audio written via `scipy.io.wavfile.write()` |

---

## 4. The `S32_LE` Container Convention

Because microcontrollers and PC host processors operate natively on 32-bit registers, AuscultaForge standardizes on **`S32_LE`**:
* **Container Size:** 4 bytes (32 bits) per audio sample.
* **Byte Order:** Little-Endian (Least significant byte at lowest memory address).
* **Alignment Options:**
  1. **MSB-Aligned (`msb`):** Active 24 bits occupy bits 31..8; bits 7..0 are padded with zeros. Common in standard I2S DMA transfers where data lines shift MSB first.
  2. **LSB-Aligned (`lsb`):** Active 24 bits occupy bits 23..0; bits 31..24 replicate bit 23 (arithmetic sign extension). Common when converting to signed 32-bit integers in software.

### 4.1 Boundary Value Representation Table

| Mathematical Value | 24-bit Decimal | MSB-Aligned Hex (32-bit) | LSB-Aligned Hex (32-bit) | Little-Endian Wire Bytes (MSB) | Little-Endian Wire Bytes (LSB) | Normalized Float ([-1.0, 1.0]) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Positive Full-Scale** | $+8,388,607$ | `0x7FFFFF00` | `0x007FFFFF` | `00 FF FF 7F` | `FF FF 7F 00` | $+0.99999988$ |
| **Positive Half-Scale** | $+4,194,304$ | `0x40000000` | `0x00400000` | `00 00 00 40` | `00 00 40 00` | $+0.50000000$ |
| **Smallest Positive** | $+1$ | `0x00000100` | `0x00000001` | `00 01 00 00` | `01 00 00 00` | $+0.00000012$ |
| **Digital Zero** | $0$ | `0x00000000` | `0x00000000` | `00 00 00 00` | `00 00 00 00` | $0.00000000$ |
| **Smallest Negative** | $-1$ | `0xFFFFFF00` | `0xFFFFFFFF` | `00 FF FF FF` | `FF FF FF FF` | $-0.00000012$ |
| **Negative Half-Scale** | $-4,194,304$ | `0xC0000000` | `0xFFC00000` | `00 00 00 C0` | `00 00 C0 FF` | $-0.50000000$ |
| **Negative Full-Scale** | $-8,388,608$ | `0x80000000` | `0xFF800000` | `00 00 00 80` | `00 00 80 FF` | $-1.00000000$ |

---

## 5. Normalization to IEEE-754 Floating-Point

To execute digital filtering (Butterworth SOS), spectral estimation (Welch PSD), and segmentation models (Springer HSMM) in Python, integer samples must be converted to dimensionless floating-point values in $[-1.0, 1.0]$.

### 5.1 Normalization Formulas
- **For MSB-Aligned Samples ($x_{\text{msb}} \in [-2^{31}, +2^{31}-1]$):**
  $$y[n] = \frac{x_{\text{msb}}[n]}{2^{31}} = \frac{x_{\text{msb}}[n]}{2147483648.0}$$
- **For LSB-Aligned Samples ($x_{\text{lsb}} \in [-2^{23}, +2^{23}-1]$):**
  $$y[n] = \frac{x_{\text{lsb}}[n]}{2^{23}} = \frac{x_{\text{lsb}}[n]}{8388608.0}$$

### 5.2 Decibels Relative to Full Scale (dBFS)
Signal amplitude relative to digital saturation is defined as **dBFS**:
$$\text{Peak Level (dBFS)} = 20 \log_{10} (|y[n]|)$$
$$\text{RMS Level (dBFS)} = 20 \log_{10} \left( \sqrt{\frac{1}{N} \sum_{n=0}^{N-1} y^2[n]} \right)$$

* A full-scale sine wave $y[n] = \sin(2\pi f n / f_s)$ has a peak level of $0 \ \text{dBFS}$ and an RMS level of $-3.01 \ \text{dBFS}$.
* Any digital sample exceeding $0 \ \text{dBFS}$ ($|y[n]| > 1.0$) indicates digital clipping.
