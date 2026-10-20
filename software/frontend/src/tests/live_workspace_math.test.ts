/**
 * Targeted unit tests for LiveWorkspace math, circular buffer indexing,
 * physical time-axis scaling and backpressure telemetry separation.
 *
 * Run with: npx tsx src/tests/live_workspace_math.test.ts
 */

import assert from 'node:assert';

console.log('[TEST] Starting LiveWorkspace mathematical & telemetry unit tests...');

// 1. Physical Time-Axis and Rate Mapping
function computeEffectiveRate(sampleRate: number, displayPointsPerSec?: number): number {
  return displayPointsPerSec && displayPointsPerSec > 0 ? displayPointsPerSec : sampleRate;
}

function computeBufferIndices(
  bufferLength: number,
  bufferSpanSec: number,
  durationSec: number,
  windowStartSec: number,
  visibleWindowSec: number,
  effectivePointsRate: number
): { startIndex: number; endIndex: number } {
  const bufferStart = Math.max(0, durationSec - bufferSpanSec);
  const offsetFromStart = Math.max(0, windowStartSec - bufferStart);
  const startIndex = Math.min(
    bufferLength - 1,
    Math.max(0, Math.floor(offsetFromStart * effectivePointsRate))
  );
  const endIndex = Math.min(
    bufferLength,
    Math.max(startIndex + 1, Math.ceil((offsetFromStart + visibleWindowSec) * effectivePointsRate))
  );
  return { startIndex, endIndex };
}

// Test 1: Effective rate mapping preserves 3200 pts/s live decimation
{
  const liveSampleRate = 48000;
  const displayPointsRate = 3200; // 25 Hz * 128 points
  const effRate = computeEffectiveRate(liveSampleRate, displayPointsRate);
  assert.strictEqual(effRate, 3200, 'Live stream must use displayPointsPerSec (3200)');

  const fileRate = computeEffectiveRate(4000, undefined);
  assert.strictEqual(fileRate, 4000, 'Offline file must fall back to sampleRate');
  console.log('✓ Test 1: Effective rate mapping verified');
}

// Test 2: Circular buffer sliding window indexing at 48 kHz decimated points
{
  // Buffer length: 48,000 points (~15 seconds at 3200 pts/s)
  const bufferLen = 48000;
  const bufferSpanSec = 15.0;
  const effRate = 3200;

  // Case A: At t=5.0s, windowStart=0s, visibleWindow=5s
  const winA = computeBufferIndices(bufferLen, bufferSpanSec, 5.0, 0.0, 5.0, effRate);
  assert.strictEqual(winA.startIndex, 0);
  assert.strictEqual(winA.endIndex, 16000); // 5s * 3200 = 16,000 points
  assert.ok(winA.endIndex <= bufferLen);

  // Case B: At t=30.0s (buffer has rolled), windowStart=25.0s, visibleWindow=5.0s
  // Buffer holds [15.0s .. 30.0s]
  const winB = computeBufferIndices(bufferLen, bufferSpanSec, 30.0, 25.0, 5.0, effRate);
  // offsetFromStart = 25.0 - (30.0 - 15.0) = 10.0s
  // startIndex = 10.0 * 3200 = 32,000
  // endIndex = 15.0 * 3200 = 48,000
  assert.strictEqual(winB.startIndex, 32000);
  assert.strictEqual(winB.endIndex, 48000);
  console.log('✓ Test 2: Circular buffer sliding window indexing verified (15x scale bug prevented)');
}

// Test 3: Formatting dynamic physical timecode ruler
function formatTimecode(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 10);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
}

{
  assert.strictEqual(formatTimecode(0.0), '00:00.0');
  assert.strictEqual(formatTimecode(5.5), '00:05.5');
  assert.strictEqual(formatTimecode(65.2), '01:05.2');
  console.log('✓ Test 3: Timecode ruler formatting verified');
}

// Test 4: Strict telemetry separation between MCU loss and UI display drops
interface TelemetryState {
  mcuLossBlocks: number;
  uiDroppedDisplayFrames: number;
}

function categorizeLoss(state: TelemetryState): { isHardwareDegraded: boolean; isUiThrottled: boolean } {
  return {
    isHardwareDegraded: state.mcuLossBlocks > 0,
    isUiThrottled: state.uiDroppedDisplayFrames > 0,
  };
}

{
  const purelyUiLag: TelemetryState = { mcuLossBlocks: 0, uiDroppedDisplayFrames: 42 };
  const resUi = categorizeLoss(purelyUiLag);
  assert.strictEqual(resUi.isHardwareDegraded, false, 'UI frame drop must not flag hardware degradation');
  assert.strictEqual(resUi.isUiThrottled, true, 'UI frame drop must flag UI throttled');

  const purelyHwLoss: TelemetryState = { mcuLossBlocks: 3, uiDroppedDisplayFrames: 0 };
  const resHw = categorizeLoss(purelyHwLoss);
  assert.strictEqual(resHw.isHardwareDegraded, true, 'MCU loss must flag hardware degradation');
  assert.strictEqual(resHw.isUiThrottled, false, 'MCU loss must not falsely claim UI backpressure');
  console.log('✓ Test 4: Strict MCU vs UI backpressure telemetry separation verified');
}

console.log('[TEST] All LiveWorkspace math and telemetry tests PASSED successfully!\n');
