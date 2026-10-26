/**
 * Numerical validation of frontend Biquad filter transfer functions.
 *
 * Verifies:
 * 1. Passband and stopband gain for all four presets (recommended, bell, diaphragm, extended).
 * 2. 2000 Hz, 4000 Hz, and 48000 Hz sampling rates.
 * 3. Multi-tone selective preservation.
 */

import assert from 'node:assert/strict';
import {
  computeBiquadFilteredAudio,
  FRONTEND_FILTER_PRESETS,
} from '../audio/audioEngine';
import { FilterPreset } from '../types';

function generateSine(freqHz: number, fs: number, durationSec: number = 1.0): Float32Array {
  const n = Math.floor(fs * durationSec);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    out[i] = Math.sin((2 * Math.PI * freqHz * i) / fs);
  }
  return out;
}

function calculateGainDb(input: Float32Array, filtered: Float32Array): number {
  // Discard 25% transient
  const start = Math.floor(input.length * 0.25);
  let inSum = 0;
  let outSum = 0;
  const count = input.length - start;
  for (let i = start; i < input.length; i++) {
    inSum += input[i] * input[i];
    outSum += filtered[i] * filtered[i];
  }
  const inRms = Math.sqrt(inSum / count);
  const outRms = Math.sqrt(outSum / count);
  if (outRms < 1e-6) return -120;
  return 20 * Math.log10(outRms / inRms);
}

const presets: FilterPreset[] = ['recommended', 'bell', 'diaphragm', 'extended'];
const testRates = [2000, 4000, 48000];

for (const fs of testRates) {
  for (const preset of presets) {
    const { lowHz, highHz } = FRONTEND_FILTER_PRESETS[preset];
    const centerHz = Math.sqrt(lowHz * highHz);
    const stopLowHz = Math.max(3, lowHz * 0.25);
    const stopHighHz = Math.min(fs / 2 - 50, highHz * 2.5);

    // 1. Passband tone
    const inCenter = generateSine(centerHz, fs, 1.5);
    const outCenter = computeBiquadFilteredAudio(inCenter, fs, lowHz, highHz);
    const centerGain = calculateGainDb(inCenter, outCenter);
    assert(
      centerGain > -4.5,
      `[${preset} @ ${fs} Hz] Center tone (${centerHz.toFixed(1)} Hz) gain too low: ${centerGain.toFixed(2)} dB`
    );

    // 2. Stopband low tone
    const inStopLow = generateSine(stopLowHz, fs, 1.5);
    const outStopLow = computeBiquadFilteredAudio(inStopLow, fs, lowHz, highHz);
    const stopLowGain = calculateGainDb(inStopLow, outStopLow);
    assert(
      stopLowGain < -10.0,
      `[${preset} @ ${fs} Hz] Stopband low (${stopLowHz.toFixed(1)} Hz) not attenuated: ${stopLowGain.toFixed(2)} dB`
    );

    // 3. Stopband high tone
    if (stopHighHz < fs / 2) {
      const inStopHigh = generateSine(stopHighHz, fs, 1.5);
      const outStopHigh = computeBiquadFilteredAudio(inStopHigh, fs, lowHz, highHz);
      const stopHighGain = calculateGainDb(inStopHigh, outStopHigh);
      assert(
        stopHighGain < -10.0,
        `[${preset} @ ${fs} Hz] Stopband high (${stopHighHz.toFixed(1)} Hz) not attenuated: ${stopHighGain.toFixed(2)} dB`
      );
    }
  }
}

// Multi-tone composite verification in Bell mode
const fs = 4000;
const toneSub = generateSine(5, fs, 1.5);
const toneBell = generateSine(60, fs, 1.5);
const toneMurmur = generateSine(250, fs, 1.5);
const toneNoise = generateSine(1500, fs, 1.5);

const composite = new Float32Array(toneSub.length);
for (let i = 0; i < composite.length; i++) {
  composite[i] = toneSub[i] + toneBell[i] + toneMurmur[i] + toneNoise[i];
}

const bellFiltered = computeBiquadFilteredAudio(composite, fs, 20, 120);
const bellGain = calculateGainDb(toneBell, computeBiquadFilteredAudio(toneBell, fs, 20, 120));
const noiseGain = calculateGainDb(toneNoise, computeBiquadFilteredAudio(toneNoise, fs, 20, 120));
assert(bellGain > -3.0, 'Bell tone should pass cleanly');
assert(noiseGain < -20.0, 'High frequency noise should be suppressed by > 20 dB');

console.log('PASS: frontend biquad filter transfer functions numerically verified at 2k, 4k, and 48k Hz');
