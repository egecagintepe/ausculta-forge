/**
 * AuscultaForge — Scientific UI Truthfulness & Stream Health Demarcation Unit Tests.
 *
 * Verifies:
 * 1. Welch FFT resolution labels derive dynamically from active session sample rate
 *    (48 kHz vs 4 kHz vs unselected/null fallback).
 * 2. Idle stream states never falsely display "OPTIMAL" when uninitialized.
 * 3. Synthetic benchmarks clearly indicate simulated status without implying physical USB packets.
 * 4. Legitimate hardware drops and degraded states are accurately classified.
 *
 * Run with: npx tsx src/tests/scientific_ui_truth.test.ts
 */

import assert from 'node:assert';
import { formatWelchBinLabel } from '../components/ScientificLab';
import { resolveStreamHealthState } from '../components/FooterStatus';

console.log('[TEST] Starting Scientific UI Truthfulness & Stream Health Demarcation unit tests...');

// =========================================================================
// TEST SUITE 1: Welch Resolution Dynamic Calculation (B1)
// =========================================================================

// Test 1.1: 48 kHz standard acquisition session
{
  const fs = 48000;
  assert.strictEqual(formatWelchBinLabel(512, fs), '512 (Δf ≈ 93.75 Hz @ 48 kHz)');
  assert.strictEqual(formatWelchBinLabel(1024, fs), '1024 (Δf ≈ 46.88 Hz @ 48 kHz)');
  assert.strictEqual(formatWelchBinLabel(2048, fs), '2048 (Δf ≈ 23.44 Hz @ 48 kHz)');
  assert.strictEqual(formatWelchBinLabel(4096, fs), '4096 (Δf ≈ 11.72 Hz @ 48 kHz)');
  console.log('✓ Test 1.1: 48 kHz session Welch labels correctly formatted (e.g. 2048 -> 23.44 Hz @ 48 kHz)');
}

// Test 1.2: 4 kHz downsampled / research session
{
  const fs = 4000;
  assert.strictEqual(formatWelchBinLabel(512, fs), '512 (Δf ≈ 7.81 Hz @ 4 kHz)');
  assert.strictEqual(formatWelchBinLabel(1024, fs), '1024 (Δf ≈ 3.91 Hz @ 4 kHz)');
  assert.strictEqual(formatWelchBinLabel(2048, fs), '2048 (Δf ≈ 1.95 Hz @ 4 kHz)');
  assert.strictEqual(formatWelchBinLabel(4096, fs), '4096 (Δf ≈ 0.98 Hz @ 4 kHz)');
  console.log('✓ Test 1.2: 4 kHz session Welch labels correctly formatted (e.g. 2048 -> 1.95 Hz @ 4 kHz)');
}

// Test 1.3: Honest fallback when no session is selected or sample rate is unknown/zero
{
  assert.strictEqual(formatWelchBinLabel(512, null), '512 (Δf requires active session)');
  assert.strictEqual(formatWelchBinLabel(1024, undefined), '1024 (Δf requires active session)');
  assert.strictEqual(formatWelchBinLabel(2048, 0), '2048 (Δf requires active session)');
  console.log('✓ Test 1.3: Unselected/null session honest fallback verified');
}

// =========================================================================
// TEST SUITE 2: Idle & Source-Specific Stream Health Demarcation (B2)
// =========================================================================

// Test 2.1: Backend offline must override all stream states
{
  const res = resolveStreamHealthState({
    backendConnected: false,
    sourceType: 'device',
    totalBlocks: 100,
    isHealthy: true,
  });
  assert.strictEqual(res.state, 'BACKEND_OFFLINE');
  assert.strictEqual(res.label, 'BACKEND OFFLINE');
  assert.ok(res.badgeClass.includes('danger'), 'Offline must use warning/danger styling');
  console.log('✓ Test 2.1: Backend offline state verified');
}

// Test 2.2: No active acquisition (sourceType: 'none') must NEVER display OPTIMAL
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'none',
    totalBlocks: 0,
    isHealthy: true, // Default uninitialized flag should NOT produce OPTIMAL
  });
  assert.strictEqual(res.state, 'NO_ACTIVE_ACQUISITION');
  assert.strictEqual(res.label, 'NO ACTIVE ACQUISITION');
  assert.notStrictEqual(res.label, 'OPTIMAL');
  console.log('✓ Test 2.2: Idle workspace truthfully reports NO ACTIVE ACQUISITION (never OPTIMAL)');
}

// Test 2.3: Source selected but zero blocks received yet (totalBlocks: 0)
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'device',
    totalBlocks: 0,
    isHealthy: true,
  });
  assert.strictEqual(res.state, 'NOT_EVALUATED');
  assert.strictEqual(res.label, 'STREAM HEALTH NOT EVALUATED');
  assert.notStrictEqual(res.label, 'OPTIMAL');
  console.log('✓ Test 2.3: Zero-block uninitialized stream reports NOT EVALUATED');
}

// Test 2.4: Synthetic source active without claiming physical USB packets
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'synthetic',
    totalBlocks: 500,
    isHealthy: true,
    droppedBlocks: 0,
    uiDroppedFrames: 0,
  });
  assert.strictEqual(res.state, 'SYNTHETIC_ACTIVE');
  assert.strictEqual(res.label, 'SYNTHETIC ACTIVE (SIMULATED)');
  assert.ok(res.telemetrySummary?.includes('HOST MEMORY'), 'Must indicate simulated memory source');
  console.log('✓ Test 2.4: Synthetic stream demarcation verified (no physical USB implication)');
}

// Test 2.5: Synthetic source with simulated dropped blocks
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'synthetic',
    totalBlocks: 500,
    isHealthy: false,
    droppedBlocks: 3,
    uiDroppedFrames: 0,
  });
  assert.strictEqual(res.state, 'SYNTHETIC_DEGRADED');
  assert.strictEqual(res.label, 'SYNTHETIC DEGRADED');
  assert.ok(res.telemetrySummary?.includes('SIM LOSS: 3'));
  console.log('✓ Test 2.5: Synthetic degraded stream verified');
}

// Test 2.6: File playback source
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'file',
    totalBlocks: 120,
    isHealthy: true,
  });
  assert.strictEqual(res.state, 'FILE_ACTIVE');
  assert.strictEqual(res.label, 'FILE PLAYBACK (HEALTHY)');
  console.log('✓ Test 2.6: File playback status verified');
}

// Test 2.7: Physical hardware device streaming healthy
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'device',
    totalBlocks: 1000,
    isHealthy: true,
    droppedBlocks: 0,
    uiDroppedFrames: 0,
  });
  assert.strictEqual(res.state, 'STREAM_HEALTHY');
  assert.strictEqual(res.label, 'STREAM HEALTHY');
  assert.ok(res.telemetrySummary?.includes('USB SYNCHRONIZED'));
  console.log('✓ Test 2.7: Physical hardware healthy stream verified');
}

// Test 2.8: Physical hardware device streaming degraded
{
  const res = resolveStreamHealthState({
    backendConnected: true,
    sourceType: 'device',
    totalBlocks: 1000,
    isHealthy: false,
    droppedBlocks: 4,
    uiDroppedFrames: 1,
  });
  assert.strictEqual(res.state, 'STREAM_DEGRADED');
  assert.strictEqual(res.label, 'STREAM DEGRADED');
  assert.ok(res.telemetrySummary?.includes('MCU LOSS: 4'));
  assert.ok(res.telemetrySummary?.includes('UI DROPS: 1'));
  console.log('✓ Test 2.8: Physical hardware degraded stream telemetry verified');
}

console.log('[TEST] All Scientific UI Truthfulness & Stream Health Demarcation tests PASSED successfully!');
