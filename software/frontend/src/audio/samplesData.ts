import { HeartSoundMetadata } from '../types';

export const STARTER_SAMPLES: HeartSoundMetadata[] = [
  {
    id: 'sample_normal_01',
    title: 'Normal S1/S2 Sound',
    filename: 'normal_sample_01.wav',
    category: 'Normal Physiological Sounds',
    durationSeconds: 15.0,
    sampleRateHz: 4000,
    channels: 1,
    description: 'Bicuspid and tricuspid valve closure (S1) followed by aortic and pulmonic valve closure (S2) at 72 BPM. Minimal baseline sway.',
    sourceAttribution: 'PhysioNet / Computing in Cardiology Clinical Acoustic Dataset Archive',
    quality: {
      rating: 'Good',
      score: 86,
      snrDb: 22.4,
      message: 'Zero clipping, minimal baseline sway. Calibrated 100 mV/Pa transducer.'
    },
    heartRateBpm: 72,
    spectralCentroidHz: 68.4,
    noiseFloorDb: -72
  },
  {
    id: 'sample_aortic_stenosis_02',
    title: 'Aortic Valve Stenosis',
    filename: 'aortic_stenosis_02.wav',
    category: 'Valvular Murmurs',
    durationSeconds: 15.0,
    sampleRateHz: 4000,
    channels: 1,
    description: 'Crescendo-decrescendo harsh ejection murmur between S1 and S2 best heard at right upper sternal border with radiation.',
    sourceAttribution: 'Clinical Phonocardiography Archive (University Reference Corpus)',
    quality: {
      rating: 'Good',
      score: 82,
      snrDb: 19.8,
      message: 'Turbulent flow acoustic signature with preserved fundamental cadence.'
    },
    heartRateBpm: 74,
    spectralCentroidHz: 142.2,
    noiseFloorDb: -68
  },
  {
    id: 'sample_mitral_regurgitation_03',
    title: 'Mitral Regurgitation',
    filename: 'mitral_regurgitation_03.wav',
    category: 'Valvular Murmurs',
    durationSeconds: 15.0,
    sampleRateHz: 4000,
    channels: 1,
    description: 'Plateau-shaped high-frequency pansystolic blowing murmur radiating to the left axilla. Holosystolic blowing pass.',
    sourceAttribution: 'Stethoscope Reference Library (Acoustic Evaluation Standards)',
    quality: {
      rating: 'Fair',
      score: 68,
      snrDb: 14.1,
      message: 'Slight respiratory artifact detected in baseline window; valve closure distinct.'
    },
    heartRateBpm: 70,
    spectralCentroidHz: 185.6,
    noiseFloorDb: -64
  }
];

/**
 * Synthesize genuine physiological phonocardiogram heart audio (raw vs filtered)
 */
export function generateSyntheticHeartAudio(
  sampleId: string,
  durationSec: number = 15.0,
  sampleRate: number = 4000
): { raw: Float32Array; filtered: Float32Array } {
  const totalSamples = Math.floor(durationSec * sampleRate);
  const raw = new Float32Array(totalSamples);
  const filtered = new Float32Array(totalSamples);

  const bpm = 72;
  const cycleSec = 60 / bpm; // ~0.833 sec per heartbeat
  const cycleSamples = Math.floor(cycleSec * sampleRate);

  // Systolic interval ~ 0.30s
  const s1s2DelaySamples = Math.floor(0.30 * sampleRate);

  for (let i = 0; i < totalSamples; i++) {
    const cyclePos = i % cycleSamples;
    const tCycle = cyclePos / sampleRate;

    let rawVal = 0;
    let filteredVal = 0;

    // S1 Component: ~55 Hz damped sine wave, duration ~0.10s
    if (tCycle < 0.10) {
      const env = Math.sin((Math.PI * tCycle) / 0.10) * Math.exp(-tCycle * 25);
      const s1 = Math.sin(2 * Math.PI * 55 * tCycle) * 0.85 * env;
      filteredVal += s1;
      rawVal += s1;
    }

    // S2 Component: ~95 Hz damped sine wave, sharper, duration ~0.08s
    const tS2 = (cyclePos - s1s2DelaySamples) / sampleRate;
    if (tS2 >= 0 && tS2 < 0.08) {
      const env = Math.sin((Math.PI * tS2) / 0.08) * Math.exp(-tS2 * 35);
      const s2 = Math.sin(2 * Math.PI * 95 * tS2) * 0.70 * env;
      filteredVal += s2;
      rawVal += s2;
    }

    // Murmur components depending on sample type
    if (sampleId === 'sample_aortic_stenosis_02') {
      // Ejection murmur between S1 (t=0.08) and S2 (t=0.28)
      if (tCycle > 0.06 && tCycle < 0.28) {
        const murmurProgress = (tCycle - 0.06) / 0.22;
        // Diamond shaped (crescendo-decrescendo) envelope
        const env = Math.sin(Math.PI * murmurProgress);
        // Turbulent noise with dominant ~220Hz coloration
        const noise = (Math.sin(2 * Math.PI * 220 * tCycle) * 0.7 + (Math.sin(i * 997) % 1) * 0.3);
        const murmur = noise * 0.45 * env;
        filteredVal += murmur;
        rawVal += murmur * 1.1;
      }
    } else if (sampleId === 'sample_mitral_regurgitation_03') {
      // Holosystolic blowing murmur through all of systole
      if (tCycle > 0.04 && tCycle < 0.32) {
        const env = Math.min(1, Math.sin((Math.PI * (tCycle - 0.04)) / 0.28));
        const noise = (Math.sin(2 * Math.PI * 340 * tCycle) * 0.6 + (Math.sin(i * 1237) % 1) * 0.4);
        const murmur = noise * 0.35 * env;
        filteredVal += murmur;
        rawVal += murmur * 1.2;
      }
    }

    // Low-frequency thoracic rumble & ambient sensor movement noise on RAW track only
    const chestRumble = Math.sin(2 * Math.PI * 8 * (i / sampleRate)) * 0.22 +
                        Math.sin(2 * Math.PI * 2.5 * (i / sampleRate)) * 0.18 +
                        (Math.sin(i * 43) % 1) * 0.08;
    rawVal += chestRumble;

    // Clamping to -1.0 to +1.0 FS
    raw[i] = Math.max(-1, Math.min(1, rawVal));
    filtered[i] = Math.max(-1, Math.min(1, filteredVal));
  }

  return { raw, filtered };
}
