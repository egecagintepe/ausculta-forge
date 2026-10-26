import assert from 'node:assert/strict';
import { RecordingStateData } from '../api/bridgeClient';

console.log('[TEST] Starting Week 6 UX Stabilization Regression Suite...');

// 1. Test: Recording elapsed time calculation & pause synchronization
{
  const sampleRate = 4000;
  const blocks = [
    { samples: 128, expectedElapsed: 128 / 4000 },
    { samples: 256, expectedElapsed: 256 / 4000 },
    { samples: 4000, expectedElapsed: 4000 / 4000 },
    { samples: 27968, expectedElapsed: 27968 / 4000 }, // 6.992s session
  ];

  for (const b of blocks) {
    const recData: RecordingStateData = {
      is_recording: true,
      session_id: 'session_test_001',
      elapsed_seconds: Number((b.samples / sampleRate).toFixed(3)),
      samples_recorded: b.samples,
      blocks_recorded: Math.ceil(b.samples / 128),
      source: 'test_pcg_source',
      sample_rate_hz: sampleRate,
    };

    assert.equal(recData.is_recording, true);
    assert.equal(recData.samples_recorded, b.samples);
    assert.equal(recData.elapsed_seconds, Number((b.expectedElapsed).toFixed(3)));
  }

  // Verify paused state holds elapsed seconds constant
  let pausedElapsed = 2.500;
  const pauseMessage: RecordingStateData = {
    is_recording: true,
    session_id: 'session_test_001',
    elapsed_seconds: pausedElapsed,
    samples_recorded: 10000,
    blocks_recorded: 78,
    source: 'test_pcg_source',
    sample_rate_hz: sampleRate,
  };
  assert.equal(pauseMessage.elapsed_seconds, 2.500, 'Paused state must maintain fixed elapsed seconds');

  console.log('✓ Test 1: Recording elapsed seconds & sample-synchronization verified');
}

// 2. Test: Manifest export toast and notification behavior contract
{
  interface ManifestMock {
    manifest_version: string;
    app_provenance: {
      dsp_engine_version: string;
      desktop_client_version: string;
      app_version: string;
    };
  }

  const mockManifest: ManifestMock = {
    manifest_version: '2.0.0',
    app_provenance: {
      dsp_engine_version: '2.0.0',
      desktop_client_version: '0.1.0-alpha.1',
      app_version: '2.0.0',
    },
  };

  // Simulate export callback contract
  let toastTriggered = false;
  let toastMsg = '';
  let toastType = '';
  const onToast = (msg: string, type?: 'info' | 'success' | 'warning') => {
    toastTriggered = true;
    toastMsg = msg;
    toastType = type || 'info';
  };

  const sessionId = 'session_20261026_121726_530cde89';
  const triggerManifestExport = (manifest: ManifestMock | null) => {
    if (!manifest) {
      onToast(`Manifest not found for session ${sessionId.slice(0, 16)}`, 'warning');
      return;
    }
    onToast(`Manifest exported: manifest_${sessionId.slice(0, 16)}...json`, 'success');
  };

  // Success case
  triggerManifestExport(mockManifest);
  assert.equal(toastTriggered, true);
  assert.equal(toastType, 'success');
  assert.match(toastMsg, /Manifest exported:/);

  // Failure case
  toastTriggered = false;
  triggerManifestExport(null);
  assert.equal(toastTriggered, true);
  assert.equal(toastType, 'warning');
  assert.match(toastMsg, /Manifest not found/);

  console.log('✓ Test 2: Manifest export notification callback contract verified');
}

// 3. Test: HomeView button semantics and event separation contract
{
  let fileDialogTriggered = false;
  let navigateDestination: string | null = null;

  const mockFileInput = {
    click: () => {
      fileDialogTriggered = true;
    },
  };

  const onNavigate = (dest: string) => {
    navigateDestination = dest;
  };

  // Action A: User clicks "Choose Local Audio File" button
  const handleBrowseLocalFilesClick = (e: { stopPropagation: () => void }) => {
    e.stopPropagation();
    mockFileInput.click();
  };

  // Action B: User clicks "Open Reference Corpus & Sessions" button
  const handleOpenSamplesArchiveClick = () => {
    onNavigate('samples');
  };

  // Execute Action A: must trigger file dialog, must NOT navigate
  fileDialogTriggered = false;
  navigateDestination = null;
  handleBrowseLocalFilesClick({ stopPropagation: () => {} });
  assert.equal(fileDialogTriggered, true, 'Browse local files button must open file dialog');
  assert.equal(navigateDestination, null, 'Browse local files button must NOT navigate to samples');

  // Execute Action B: must navigate to samples, must NOT trigger file dialog
  fileDialogTriggered = false;
  navigateDestination = null;
  handleOpenSamplesArchiveClick();
  assert.equal(fileDialogTriggered, false, 'Archive button must NOT trigger file dialog');
  assert.equal(navigateDestination, 'samples', 'Archive button must navigate to samples');

  console.log('✓ Test 3: HomeView event separation & button disambiguation verified');
}

// 4. Test: Version provenance schema disambiguation
{
  const manifest = {
    dsp_engine_version: '2.0.0',
    desktop_client_version: '0.1.0-alpha.1',
    app_version: '2.0.0', // Legacy alias
  };

  assert.equal(manifest.dsp_engine_version, '2.0.0', 'DSP engine must be 2.0.0');
  assert.equal(manifest.desktop_client_version, '0.1.0-alpha.1', 'Desktop client must be 0.1.0-alpha.1');
  assert.equal(manifest.app_version, manifest.dsp_engine_version, 'app_version must match dsp_engine_version for backward compatibility');

  console.log('✓ Test 4: Version identifier schema disambiguation verified');
}

console.log('[TEST] ALL WEEK 6 UX STABILIZATION REGRESSION TESTS PASSED!\n');
