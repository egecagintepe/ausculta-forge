# AuscultaForge — Code Reading & Analysis Defense Exercises
**Document ID:** `AF-DEFENSE-EXERCISES-V01`  
**Classification:** `ACADEMIC_DEFENSE`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Codebases:** `software/pcg_core/`, `software/pcg_app/`, `tools/c_golden_vectors/`

---

## 1. Pedagogical Objective

During an advanced academic code defense, the examiner does not merely ask theoretical questions; the examiner opens an actual source file on the projector, highlights 10–20 lines of code, and asks the student to:
1. Explain the line-by-line execution flow.
2. Predict the exact mathematical output for specific edge-case inputs.
3. Identify potential bugs, race conditions, or undefined behaviors.
4. Modify boundary conditions on the fly.
5. Explain how the routine is covered in the automated test suite.

This document contains 6 structured code-reading exercises directly taken from the AuscultaForge codebase.

---

## Exercise 1: C Two's-Complement Sign Extension (`golden_common.h`)

### Code Excerpt:
```c
uint32_t pack_and_align_sample(int32_t sample_24bit, int is_msb_aligned) {
    uint32_t u24 = (uint32_t)sample_24bit & 0x00FFFFFFU;
    
    if (is_msb_aligned) {
        return (u24 << 8);
    } else {
        if (u24 & 0x00800000U) {
            return (u24 | 0xFF000000U);
        } else {
            return u24;
        }
    }
}
```

### Examiner Questions:
1. **Predict Output:** What is the exact 32-bit hexadecimal return value when `sample_24bit = -4,194,304` (`-2^22`, negative half scale) and `is_msb_aligned = 0`?
   * *Solution:* In 24-bit two's complement, $-4,194,304 = 2^{24} - 2^{22} = 12,582,912 = 0\text{xC00000}$.
   * Bit 23 is 1 (`0xC00000 & 0x800000 != 0`).
   * The sign-extension branch executes: `0x00C00000 | 0xFF000000 = 0xFFC00000`.
   * Return value: `0xFFC00000` (which evaluates to $-4,194,304$ in standard 32-bit signed integer arithmetic).
2. **Boundary Modification:** If the hardware was upgraded to a 28-bit ADC, what constants in this function must be modified?
   * *Solution:* The bitmask `0x00FFFFFFU` becomes `0x0FFFFFFFU`. The sign check `0x00800000U` (bit 23) becomes `0x08000000U` (bit 27). The sign-extension mask `0xFF000000U` becomes `0xF0000000U`. The MSB shift `<< 8` becomes `<< 4`.
3. **Bug Spotting:** Why did the author write `(uint32_t)sample_24bit & 0x00FFFFFFU` instead of just `sample_24bit & 0x00FFFFFF`?
   * *Solution:* If `sample_24bit` is negative, in C it is sign-extended to 32-bit signed before the bitwise operation. Without `uint32_t` casting, performing bitwise shifts on signed types later can invoke undefined behavior.

---

## Exercise 2: Causal SOS Filter State Update (`pcg_core/dsp.py`)

### Code Excerpt:
```python
def process_block(self, samples: np.ndarray) -> np.ndarray:
    if len(samples) == 0:
        return samples.astype(np.float64)
    
    # Apply SOS filter preserving causal state
    filtered_samples, self._zi = scipy.signal.sosfilt(
        self._sos, 
        samples.astype(np.float64), 
        zi=self._zi
    )
    return filtered_samples
```

### Examiner Questions:
1. **Explain Behavior:** What is `self._zi` and why is it stored as an instance variable?
   * *Solution:* `self._zi` is the internal delay line state vector of the second-order sections. Storing it across calls ensures that the initial condition for block $k+1$ is the final condition of block $k$.
2. **Predict Failure Mode:** What happens if a developer replaces `self._zi` with `zi = scipy.signal.sosfilt_zi(self._sos)` inside this method?
   * *Solution:* The filter state would be re-initialized at the start of every 512-sample block ($\approx 10.67\text{ ms}$). This causes a transient step response spike at the beginning of every single block, creating a loud $93.75\text{ Hz}$ buzzing artifact in the audio.
3. **Unit Test Strategy:** How would you write a test proving that filtering a 1024-sample array in two 512-sample chunks produces identical output to filtering all 1024 samples at once?
   * *Solution:* See `software/tests/test_scientific_dsp_quality.py::test_streaming_bandpass_sos`. It asserts `np.allclose(chunked_out, batch_out, atol=1e-12)`.

---

## Exercise 3: Peak-Preserving Display Decimation (`display_pipeline.py`)

### Code Excerpt:
```python
num_buckets = self.target_points // 2
bucket_size = int(np.ceil(n_samples / num_buckets))

padded_len = num_buckets * bucket_size
if padded_len > n_samples:
    padded = np.pad(samples, (0, padded_len - n_samples), mode='edge')
else:
    padded = samples[:padded_len]

buckets = padded.reshape(num_buckets, bucket_size)
mins = np.min(buckets, axis=1)
maxs = np.max(buckets, axis=1)

decimated = np.empty(num_buckets * 2, dtype=np.float32)
decimated[0::2] = mins
decimated[1::2] = maxs
```

### Examiner Questions:
1. **Explain Behavior:** Why does the output array alternate between `mins` and `maxs`?
   * *Solution:* Interleaving `decimated[0::2] = mins` and `decimated[1::2] = maxs` provides an envelope bounding box for each temporal bucket, allowing the canvas drawing loop to paint a vertical min-to-max line for each column, guaranteeing visual peak retention.
2. **Boundary Analysis:** What happens if `samples` contains a single sharp Dirac spike: `samples = [0, 0, ..., 0, 1.0, 0, ..., 0]`?
   * *Solution:* In whichever bucket the $1.0$ falls, $\max(\text{bucket}) = 1.0$ and $\min(\text{bucket}) = 0.0$. The $1.0$ is guaranteed to be present in `maxs` and will be rendered on screen. Under naive subsampling, the $1.0$ would be completely missed if its index was not an exact multiple of the stride.
3. **Edge Case:** Why is `mode='edge'` used in `np.pad`?
   * *Solution:* To prevent padding with artificial zeros at the end of the block, which would artificially pull `mins` down to zero if all samples in the final bucket were positive.

---

## Exercise 4: Least-Squares Path Gain Estimation (`validation.py`)

### Code Excerpt:
```python
def estimate_least_squares_gain(x: np.ndarray, y: np.ndarray) -> float:
    denom = float(np.sum(x ** 2))
    if denom < 1e-12:
        return 0.0
    numer = float(np.sum(x * y))
    return numer / denom
```

### Examiner Questions:
1. **Derive Formula:** Where does `numer / denom` come from mathematically?
   * *Solution:* Minimize squared error $J(g) = \sum (y[n] - g x[n])^2$. Derivative $\frac{dJ}{dg} = -2 \sum x[n] \cdot (y[n] - g x[n]) = 0 \implies g \sum x^2[n] = \sum x[n]y[n] \implies g = \frac{\sum x[n]y[n]}{\sum x^2[n]}$.
2. **Predict Output:** What is the returned gain if $y[n] = -0.5 x[n]$?
   * *Solution:*
     $$\text{numer} = \sum x[n] (-0.5 x[n]) = -0.5 \sum x^2[n]$$
     $$\text{gain} = \frac{-0.5 \sum x^2[n]}{\sum x^2[n]} = -0.5000$$
3. **Robustness Check:** What happens if the stimulus is completely silent ($x[n] = 0$ for all $n$)?
   * *Solution:* `denom` is $0.0 < 10^{-12}$. The guard condition executes and safely returns `0.0`, preventing a ZeroDivisionError.

---

## Exercise 5: Rolling Buffer Wrap Mechanics (`pcg_core/buffers.py`)

### Code Excerpt:
```python
def append(self, samples: np.ndarray) -> None:
    n = len(samples)
    if n >= self.capacity:
        self._buffer[:] = samples[-self.capacity:]
        self._write_idx = 0
        return

    space_at_end = self.capacity - self._write_idx
    if n <= space_at_end:
        self._buffer[self._write_idx:self._write_idx + n] = samples
        self._write_idx = (self._write_idx + n) % self.capacity
    else:
        self._buffer[self._write_idx:] = samples[:space_at_end]
        overflow = n - space_at_end
        self._buffer[:overflow] = samples[space_at_end:]
        self._write_idx = overflow
```

### Examiner Questions:
1. **Execution Flow:** What occurs when incoming samples exceed the space remaining at the end of the circular buffer?
   * *Solution:* The operation splits into two contiguous slice copies: the first slice (`samples[:space_at_end]`) fills the tail of the buffer, and the remaining overflow slice (`samples[space_at_end:]`) wraps around to overwrite the beginning of the buffer (`self._buffer[:overflow]`).
2. **Predict Output:** If `capacity = 100`, `_write_idx = 90`, and `len(samples) = 25`, where are the samples placed?
   * *Solution:* `space_at_end = 10`. The first 10 samples are written to indices `[90..99]`. `overflow = 15`. The remaining 15 samples are written to indices `[0..14]`. `_write_idx` becomes `15`.
3. **Thread Safety:** Why must this entire operation be wrapped inside `with self._lock:`?
   * *Solution:* If a reader thread (such as the spectral analysis loop) reads from the buffer while `append` is midway between the tail copy and the head copy, it reads a torn, non-contiguous block of audio.

---

## Exercise 6: Springer HSMM Cyclic Trellis Transition (`springer_hsmm.py`)

### Code Excerpt:
```python
# Transition matrix for Springer LR-HSMM (1-indexed states: 1=S1, 2=Sys, 3=S2, 4=Dia)
TRANSITION_MATRIX = np.array([
    [0.0, 1.0, 0.0, 0.0],  # S1 -> Systole
    [0.0, 0.0, 1.0, 0.0],  # Systole -> S2
    [0.0, 0.0, 0.0, 1.0],  # S2 -> Diastole
    [1.0, 0.0, 0.0, 0.0],  # Diastole -> S1
], dtype=np.float64)
```

### Examiner Questions:
1. **Explain Biological Basis:** Why are all self-transitions ($A_{i,i}$) zero in this transition matrix?
   * *Solution:* In an HSMM, state duration is explicitly parameterized by duration distributions $p_j(d)$ rather than self-transitions. When a state finishes its duration $d$, it MUST transition to the next physiological state.
2. **Mathematical Implication:** In log-space, what value do the zero entries take?
   * *Solution:* $\ln(0) = -\infty$. In Viterbi dynamic programming, adding $-\infty$ immediately eliminates any path attempting an illegal physiological transition (e.g. $S_1 \to S_2$ without intervening systole).
3. **Edge Case:** How does the Viterbi trellis handle a recording that begins halfway through systole?
   * *Solution:* The initial state probability distribution $\boldsymbol{\pi}$ is set to uniform ($\pi_j = 0.25$) or derived from the first detected peak, allowing the Viterbi path to begin in any physiological state.
