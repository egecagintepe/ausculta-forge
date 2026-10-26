import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { FooterStatus } from './components/FooterStatus';
import { HomeView } from './components/HomeView';
import { LiveWorkspace } from './components/LiveWorkspace';
import { SamplesView } from './components/SamplesView';
import { DeviceView } from './components/DeviceView';
import { SettingsView } from './components/SettingsView';
import { AnalysisWorkbench } from './components/AnalysisWorkbench';
import { ResearchLabView } from './components/ResearchLabView';
import { DiagnosticsDrawer } from './components/DiagnosticsDrawer';
import { ConfirmDiscardDialog, SaveAsDialog, ToastNotification, ToastInfo } from './components/Dialogs';
import { audioEngine } from './audio/audioEngine';
import { STARTER_SAMPLES, generateSyntheticHeartAudio } from './audio/samplesData';
import { bridgeClient, SignalFrameData, DisplayFrameData, StreamStateData, RecordingStateData } from './api/bridgeClient';
import {
  NavigationDestination,
  AudioSourceType,
  FilterPreset,
  FilterStrength,
  ListeningTrack,
  HeartSoundMetadata,
  DiagnosticState,
  DiagnosticLogEvent,
  AudioMetrics,
  StethoscopeDevice,
  DeviceRuntimeState,
  DeviceIntegrityStats,
  DeviceEventItem,
  SpectralFrameData,
} from './types';

export default function App() {
  // Theme state (Porcelain Light is default primary)
  const [isDark, setIsDark] = useState<boolean>(() => {
    return false;
  });

  // Navigation & Acquisition Source
  const [currentDestination, setCurrentDestination] = useState<NavigationDestination>('live');
  const [analysisTargetSessionId, setAnalysisTargetSessionId] = useState<string | null>(null);
  const [sourceType, setSourceType] = useState<AudioSourceType>('none');
  const [activeMetadata, setActiveMetadata] = useState<HeartSoundMetadata | null>(null);

  // Audio Data (Empty at startup until source selected)
  const [rawData, setRawData] = useState<Float32Array>(new Float32Array(0));
  const [filteredData, setFilteredData] = useState<Float32Array>(new Float32Array(0));
  const [sampleRate, setSampleRate] = useState<number>(4000);
  const [duration, setDuration] = useState<number>(0.0);
  const [currentTime, setCurrentTime] = useState<number>(0.0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(0.78);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [filterPreset, setFilterPreset] = useState<FilterPreset>('recommended');
  const [filterStrength, setFilterStrength] = useState<FilterStrength>('Normal');
  const [showRaw, setShowRaw] = useState<boolean>(true);
  const [listeningTrack, setListeningTrack] = useState<ListeningTrack>('filtered');
  const [visibleWindowSec, setVisibleWindowSec] = useState<number>(10);
  const visibleWindowSecRef = useRef(visibleWindowSec);
  visibleWindowSecRef.current = visibleWindowSec;

  // Fullscreen & Presentation
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  // Diagnostics Drawer
  const [diagnosticsOpen, setDiagnosticsOpen] = useState<boolean>(false);
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  // Hardware Device State (Truthful device runtime)
  const [deviceRuntimeState, setDeviceRuntimeState] = useState<DeviceRuntimeState | null>(null);
  const [deviceStats, setDeviceStats] = useState<DeviceIntegrityStats | null>(null);
  const [deviceEvents, setDeviceEvents] = useState<DeviceEventItem[]>([]);
  const [deviceState, setDeviceState] = useState<StethoscopeDevice>({
    connected: false,
    state: 'Not connected',
    deviceId: 'None (Waiting for Probe)',
    port: 'Pending Native USB Descriptor Decision',
    firmwareVersion: 'Pending',
    sampleRateHz: 4000,
  });
  const [deviceConnecting, setDeviceConnecting] = useState<boolean>(false);
  const [hasUnsavedRecording, setHasUnsavedRecording] = useState<boolean>(false);

  // Python Backend Bridge Integration State
  const [backendConnected, setBackendConnected] = useState<boolean>(false);
  const [liveMetrics, setLiveMetrics] = useState<{ rms: number; peak: number; crest_factor: number }>({
    rms: 0.0,
    peak: 0.0,
    crest_factor: 0.0,
  });
  const [streamQuality, setStreamQuality] = useState<{
    total_blocks: number;
    dropped_blocks: number;
    repeated_sequences: number;
    sequence_discontinuities: number;
    is_healthy: boolean;
  }>({
    total_blocks: 0,
    dropped_blocks: 0,
    repeated_sequences: 0,
    sequence_discontinuities: 0,
    is_healthy: true,
  });
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingElapsedSeconds, setRecordingElapsedSeconds] = useState<number>(0);
  const [recordingSessionId, setRecordingSessionId] = useState<string | null>(null);
  const [activeSourceName, setActiveSourceName] = useState<string>('None');
  const [spectralFrame, setSpectralFrame] = useState<SpectralFrameData | null>(null);
  useEffect(() => { setSpectralFrame(null); }, [sourceType, activeMetadata?.id]);
  const [droppedDisplayFrames, setDroppedDisplayFrames] = useState<number>(0);
  const currentSourceTypeRef = useRef<AudioSourceType>(sourceType);
  currentSourceTypeRef.current = sourceType;

  // Dialogs & Modals
  const [saveAsOpen, setSaveAsOpen] = useState<boolean>(false);
  const [confirmDiscardOpen, setConfirmDiscardOpen] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  const [toasts, setToasts] = useState<ToastInfo[]>([]);

  // Telemetry Log history
  const [logs, setLogs] = useState<DiagnosticLogEvent[]>([
    {
      id: 'log-1',
      timestamp: '16:42:10',
      severity: 'info',
      message: 'App started (v0.1 Windows x64)',
      component: 'Core'
    },
    {
      id: 'log-2',
      timestamp: '16:42:12',
      severity: 'warning',
      message: 'Device scan initiated (No hardware found)',
      component: 'Hardware'
    },
    {
      id: 'log-3',
      timestamp: '16:43:05',
      severity: 'info',
      message: 'File opened: normal_sample_01.wav',
      component: 'FileIO'
    },
    {
      id: 'log-4',
      timestamp: '16:43:06',
      severity: 'info',
      message: 'Waveform buffer precomputed (15.0s)',
      component: 'DSP'
    },
    {
      id: 'log-5',
      timestamp: '16:43:18',
      severity: 'info',
      message: 'Playback ready at 00:08.40',
      component: 'AudioEngine'
    },
    {
      id: 'log-6',
      timestamp: '16:43:26',
      severity: 'info',
      message: 'Filter set to Narrow (20–200 Hz Dev Preset)',
      component: 'DSP'
    }
  ]);

  const addLog = useCallback((message: string, severity: 'info' | 'warning' | 'error' = 'info', component: string = 'System') => {
    const d = new Date();
    const ts = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
    const newLog: DiagnosticLogEvent = {
      id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      timestamp: ts,
      severity,
      message,
      component
    };
    setLogs(prev => [newLog, ...prev.slice(0, 49)]);
  }, []);

  const addToast = useCallback((message: string, type: 'info' | 'success' | 'warning' = 'info') => {
    const id = `toast-${Date.now()}`;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3500);
  }, []);

  // Sync dark theme class on document element
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  // Connect to Python Bridge WebSocket and ingest real live stream
  useEffect(() => {
    let isCancelled = false;
    bridgeClient.initDesktopBridge().then(() => {
      if (!isCancelled) {
        bridgeClient.connect();
      }
    });

    const unsubConn = bridgeClient.onConnectionChange((connected) => {
      setBackendConnected(connected);
      if (connected) {
        addLog(`Connected to Python DSP Bridge (${bridgeClient.getSanitizedWsUrl()})`, 'info', 'Bridge');
        addToast(`Connected to Python DSP Bridge (${bridgeClient.getEndpoint()})`, 'success');
      } else {
        addLog('Disconnected from Python DSP Bridge. Retrying...', 'warning', 'Bridge');
        setDeviceRuntimeState({
          connected: false,
          state: 'absent',
          discovery_status: 'Bridge offline — awaiting connection',
          device_id: null,
          firmware_version: null,
          candidate: null,
        });
        setDeviceState(prev => ({
          ...prev,
          connected: false,
          state: 'Not connected',
          deviceId: 'None (Bridge Offline)'
        }));
      }
    });

    const unsubState = bridgeClient.onStreamState((st: StreamStateData) => {
      const localAudition = ['file', 'sample'].includes(currentSourceTypeRef.current);
      if (localAudition && !st.is_streaming) return;
      if (st.source_type !== 'none') setActiveMetadata(null);
      if (st.filter_preset) setFilterPreset(st.filter_preset);
      if (st.sample_rate_hz) setSampleRate(st.sample_rate_hz);
      if (st.active_source_name) setActiveSourceName(st.active_source_name);
      if (st.source_type === 'hardware') setSourceType(st.active_source_name?.startsWith('SOFTWARE SIMULATION:') ? 'synthetic' : 'device');
      else if (st.source_type === 'synthetic_dev') setSourceType('synthetic');
      else if (st.source_type === 'session' || st.source_type === 'realtime_wav') setSourceType('session');
      if (typeof st.is_paused === 'boolean') {
        setIsPlaying(!st.is_paused && st.is_streaming);
      }
    });

    const unsubRec = bridgeClient.onRecordingState((rec: RecordingStateData) => {
      setIsRecording(rec.is_recording);
      setRecordingElapsedSeconds(rec.elapsed_seconds);
      setRecordingSessionId(rec.session_id);
      if (rec.is_recording) {
        addLog(`Session recording started: ${rec.session_id}`, 'info', 'Recorder');
      } else if (rec.session_id) {
        addLog(`Session recording saved: ${rec.session_id} (${rec.samples_recorded} samples)`, 'info', 'Recorder');
        addToast(`Session saved: ${rec.session_id}`, 'success');
      }
    });

    const unsubDevState = bridgeClient.onDeviceState((dev) => {
      setDeviceRuntimeState(dev);
      setDeviceState(prev => ({
        ...prev,
        connected: dev.connected,
        state: dev.connected ? (dev.state === 'streaming' ? 'Streaming' : 'Connected') : 'Not connected',
        deviceId: dev.device_id || (dev.candidate ? dev.candidate.description || 'USB Candidate' : 'None (Waiting for Probe)'),
        firmwareVersion: dev.firmware_version || 'Pending',
      }));
    });

    const unsubDevEvt = bridgeClient.onDeviceEvent((evt) => {
      setDeviceEvents(prev => [evt, ...prev.slice(0, 199)]);
      addLog(`[${evt.code}] ${evt.message}`, evt.severity, 'Device');
    });

    const unsubDevStats = bridgeClient.onDeviceStats((stats) => {
      setDeviceStats(stats);
    });

    // Fetch initial device state & history snapshot
    bridgeClient.fetchDeviceState().then(dev => {
      if (dev) {
        setDeviceRuntimeState(dev);
        setDeviceState(prev => ({
          ...prev,
          connected: dev.connected,
          state: dev.connected ? (dev.state === 'streaming' ? 'Streaming' : 'Connected') : 'Not connected',
          deviceId: dev.device_id || (dev.candidate ? dev.candidate.description || 'USB Candidate' : 'None (Waiting for Probe)'),
          firmwareVersion: dev.firmware_version || 'Pending',
        }));
      }
    });

    bridgeClient.fetchDeviceEvents().then(evts => {
      if (evts && evts.length > 0) {
        setDeviceEvents(evts);
      }
    });

    bridgeClient.fetchDeviceStats().then(stats => {
      if (stats) {
        setDeviceStats(stats);
      }
    });

    // Bounded rolling display buffers (max 15s of decimated display points ~ 48,000 points)
    const maxDisplayPoints = 15 * 3200;
    const rawDisplayBuf = new Float32Array(maxDisplayPoints);
    const filtDisplayBuf = new Float32Array(maxDisplayPoints);
    let totalWritten = 0;
    let animFrameId: number | null = null;
    let pendingUpdate = false;
    let latestMetrics: { rms: number; peak: number; crest_factor: number } | null = null;
    let latestQuality: { total_blocks: number; dropped_blocks: number; repeated_sequences: number; sequence_discontinuities: number; is_healthy: boolean } | null = null;
    let latestTimestamp = 0;
    let currentFs = 48000;
    let latestSpectral: SpectralFrameData | null = null;
    let latestDroppedFrames = 0;
    let displayStreamId: string | undefined;

    const commitDisplayUpdate = () => {
      animFrameId = null;
      if (!pendingUpdate) return;
      pendingUpdate = false;

      if (latestMetrics) setLiveMetrics(latestMetrics);
      if (latestQuality) setStreamQuality(latestQuality);
      if (latestSpectral) setSpectralFrame(latestSpectral);
      setDroppedDisplayFrames(latestDroppedFrames);

      setRawData(new Float32Array(rawDisplayBuf.subarray(0, totalWritten)));
      setFilteredData(new Float32Array(filtDisplayBuf.subarray(0, totalWritten)));
      setSampleRate(currentFs);
      setCurrentTime(latestTimestamp);
      setDuration(Math.max(visibleWindowSecRef.current, latestTimestamp));
    };

    const scheduleUpdate = () => {
      pendingUpdate = true;
      if (animFrameId === null) {
        animFrameId = requestAnimationFrame(commitDisplayUpdate);
      }
    };

    // 1. Primary decoupled display-frame listener (runs at controlled UI cadence ~25 Hz)
    const unsubDisplay = bridgeClient.onDisplayFrame((frame: DisplayFrameData) => {
      // Guard against stream cross-talk: only write to display buffer if active source is a live stream
      const src = currentSourceTypeRef.current;
      if (src !== 'device' && src !== 'synthetic' && src !== 'session') {
        return;
      }

      if (frame.stream_id !== displayStreamId) {
        displayStreamId = frame.stream_id;
        totalWritten = 0;
        latestSpectral = null;
        setSpectralFrame(null);
      }

      latestMetrics = frame.metrics;
      latestQuality = frame.stream_quality;
      latestTimestamp = frame.window_end_ts;
      currentFs = frame.sample_rate_hz;
      if (frame.spectral_frame) {
        latestSpectral = frame.spectral_frame;
      }
      latestDroppedFrames = frame.dropped_display_frames || 0;

      const raw = frame.raw_points;
      const filt = frame.filtered_points;
      const n = raw.length;

      if (totalWritten + n <= maxDisplayPoints) {
        rawDisplayBuf.set(raw, totalWritten);
        filtDisplayBuf.set(filt, totalWritten);
        totalWritten += n;
      } else {
        rawDisplayBuf.copyWithin(0, n);
        filtDisplayBuf.copyWithin(0, n);
        rawDisplayBuf.set(raw, maxDisplayPoints - n);
        filtDisplayBuf.set(filt, maxDisplayPoints - n);
        totalWritten = maxDisplayPoints;
      }

      scheduleUpdate();
    });

    // 2. Legacy fallback listener (if legacy signal_frame emitted)
    const unsubFrame = bridgeClient.onSignalFrame((frame: SignalFrameData) => {
      latestMetrics = frame.metrics;
      latestQuality = frame.stream_quality;
      latestTimestamp = frame.timestamp_s;
      currentFs = frame.sample_rate_hz;

      const n = frame.raw_samples.length;
      if (totalWritten + n <= maxDisplayPoints) {
        rawDisplayBuf.set(frame.raw_samples, totalWritten);
        filtDisplayBuf.set(frame.filtered_samples, totalWritten);
        totalWritten += n;
      } else {
        rawDisplayBuf.copyWithin(0, n);
        filtDisplayBuf.copyWithin(0, n);
        rawDisplayBuf.set(frame.raw_samples, maxDisplayPoints - n);
        filtDisplayBuf.set(frame.filtered_samples, maxDisplayPoints - n);
        totalWritten = maxDisplayPoints;
      }

      scheduleUpdate();
    });

    return () => {
      if (animFrameId !== null) {
        cancelAnimationFrame(animFrameId);
      }
      unsubConn();
      unsubState();
      unsubRec();
      unsubDevState();
      unsubDevEvt();
      unsubDevStats();
      unsubDisplay();
      unsubFrame();
      bridgeClient.disconnect();
    };
  }, [addLog, addToast]);

  // Subscribe to audio engine time updates
  useEffect(() => {
    const unsubscribe = audioEngine.subscribeTime((time) => {
      setCurrentTime(time);
      setIsPlaying(audioEngine.getIsPlaying());
    });
    return () => unsubscribe();
  }, []);

  // Load a starter sample
  const loadSample = useCallback((sample: HeartSoundMetadata) => {
    const { raw, filtered } = generateSyntheticHeartAudio(sample.id, sample.durationSeconds, sample.sampleRateHz);
    audioEngine.setAudioData(raw, filtered, sample.sampleRateHz);
    audioEngine.seek(0);
    setRawData(raw);
    setFilteredData(filtered);
    setSampleRate(sample.sampleRateHz);
    setDuration(sample.durationSeconds);
    setCurrentTime(0);
    setIsPlaying(false);
    setActiveMetadata(sample);
    setSourceType('sample');
    setCurrentDestination('live');

    addLog(`Loaded specimen: ${sample.title} (${sample.filename})`, 'info', 'FileIO');
    addToast(`Loaded ${sample.title}`, 'success');
  }, [addLog, addToast]);

  // Open a user file
  const handleOpenFile = useCallback(async (file: File) => {
    try {
      addLog(`Decoding auscultation file: ${file.name}`, 'info', 'Decoder');
      const decoded = await audioEngine.decodeUserFile(file);
      setRawData(decoded.raw);
      setFilteredData(decoded.filtered);
      setSampleRate(decoded.sampleRate);
      setDuration(decoded.duration);
      setCurrentTime(0);
      setIsPlaying(false);

      const metadata: HeartSoundMetadata = {
        id: `custom-${Date.now()}`,
        title: file.name,
        filename: file.name,
        category: 'Imported User Audio',
        durationSeconds: decoded.duration,
        sampleRateHz: decoded.sampleRate,
        channels: 1,
        description: 'Locally imported phonocardiography auscultation recording.',
        sourceAttribution: 'Workstation Local Storage',
        quality: {
          rating: 'Unavailable',
          score: null,
          message: 'Local audio file decoded'
        }
      };

      setActiveMetadata(metadata);
      setActiveSourceName(file.name);
      setSourceType('file');
      setCurrentDestination('live');
      addLog(`File successfully decoded · Duration: ${decoded.duration.toFixed(2)}s`, 'info', 'Decoder');
      addToast(`Opened ${file.name}`, 'success');
    } catch (err) {
      addLog(`Failed to open audio file: ${String(err)}`, 'error', 'Decoder');
      addToast('Could not open audio file. Supported formats: WAV, MP3', 'warning');
    }
  }, [addLog, addToast]);

  // Truthful Device Discovery and Disconnect
  const handleDetectDevice = useCallback(async () => {
    if (!backendConnected) {
      addToast('Python Bridge is offline. Cannot scan hardware.', 'warning');
      addLog('Hardware scan aborted: Python Bridge is offline', 'warning', 'Hardware');
      return;
    }
    setDeviceConnecting(true);
    addLog('Executing USB bus discovery scan via Python host provider...', 'info', 'Hardware');

    try {
      const res = await bridgeClient.pollDevice();
      setDeviceConnecting(false);
      const devState = res?.state;
      if (devState && devState.connected) {
        addLog(`Hardware verified: ${devState.device_id || 'ESP32-S3'} on ${devState.port || 'Native USB'}`, 'info', 'Hardware');
        addToast(`Hardware connected: ${devState.device_id || 'ESP32-S3'}`, 'success');
      } else {
        const statusMsg = devState?.discovery_status || 'No AuscultaForge device found on USB bus';
        addLog(`Hardware scan complete: ${statusMsg}`, 'info', 'Hardware');
        addToast('No AuscultaForge hardware detected', 'info');
      }
    } catch (err) {
      setDeviceConnecting(false);
      addLog(`Hardware discovery request failed: ${String(err)}`, 'error', 'Hardware');
      addToast('Device scan failed', 'warning');
    }
  }, [backendConnected, addLog, addToast]);

  const handleDisconnectDevice = useCallback(async () => {
    if (!backendConnected) return;
    try {
      addLog('Sending graceful disconnect request to hardware runtime...', 'info', 'Hardware');
      const res = await bridgeClient.disconnectDevice();
      if (sourceType === 'device') {
        setSourceType('none');
        setActiveSourceName('None');
      }
      addLog(`Hardware disconnected successfully: ${res?.state || 'absent'}`, 'info', 'Hardware');
      addToast('Stethoscope disconnected', 'info');
    } catch (err) {
      addLog(`Disconnect command failed: ${String(err)}`, 'error', 'Hardware');
      addToast('Disconnect failed', 'warning');
    }
  }, [backendConnected, addLog, addToast, sourceType]);

  const handleUseDeviceInLive = useCallback(() => {
    if (deviceRuntimeState?.connected) {
      bridgeClient.selectSource('hardware');
      setSourceType('device');
      setActiveSourceName(`Physical Hardware: ${deviceRuntimeState.device_id || 'ESP32-S3'}`);
      setActiveMetadata({
        id: 'hardware-live-stream',
        title: 'ESP32-S3 Physical Transducer Stream',
        filename: 'ESP32S3_Live_Acquisition.pcm',
        category: 'Live Hardware Acquisition',
        durationSeconds: 0,
        sampleRateHz: sampleRate,
        channels: 1,
        description: 'Real-time telemetry stream from connected ESP32-S3 stethoscope transducer.',
        sourceAttribution: 'AuscultaForge Live Physical Transducer',
        quality: {
          rating: 'Optimal',
          score: 100,
          message: 'Authoritative hardware streaming'
        }
      });
      setCurrentDestination('live');
      addLog('Live physical hardware stream bound to workspace', 'info', 'Acquisition');
      addToast('Bound live hardware stream to workspace', 'success');
    } else {
      addToast('No physical hardware connected. Connect device or activate synthetic benchmark.', 'warning');
      addLog('Cannot bind hardware stream: No physical device in READY or STREAMING state', 'warning', 'Acquisition');
    }
  }, [deviceRuntimeState, sampleRate, addLog, addToast]);

  const handleStartRecording = useCallback(() => {
    bridgeClient.startRecording();
    addLog('Initiating session recording...', 'info', 'Recorder');
  }, [addLog]);

  const handleStopRecording = useCallback(() => {
    bridgeClient.stopRecording();
    addLog('Finalizing session recording...', 'info', 'Recorder');
  }, [addLog]);

  const handleReplaySession = useCallback((sessionId: string) => {
    bridgeClient.selectSource('session', undefined, sessionId);
    setSourceType('session');
    setActiveSourceName(`Session Replay: ${sessionId}`);
    setCurrentDestination('live');
    addLog(`Replaying session ${sessionId} through Python DSP pipeline`, 'info', 'Pipeline');
    addToast(`Replaying session ${sessionId}`, 'info');
  }, [addLog, addToast]);

  const handleAnalyzeSession = useCallback((sessionId: string) => {
    setAnalysisTargetSessionId(sessionId);
    setCurrentDestination('analysis');
    addLog(`Opening Validation Workbench for session: ${sessionId}`, 'info', 'Analysis');
  }, [addLog]);

  const handleSelectMockSource = useCallback(() => {
    bridgeClient.selectSource('synthetic_dev');
    setSourceType('synthetic');
    setActiveSourceName('Synthetic Development Signal — Not Hardware');
    setActiveMetadata({
      id: 'synthetic-dev-benchmark',
      title: 'Synthetic Development Signal',
      filename: 'synthetic_dev_benchmark.wav',
      category: 'DSP Benchmark Signal',
      durationSeconds: 30,
      sampleRateHz: 4000,
      channels: 1,
      description: 'Synthetic S1/S2 acoustic PCG benchmark for filter testing. Not hardware.',
      sourceAttribution: 'AuscultaForge synthetic development signal',
      quality: {
        rating: 'Unavailable',
        score: null,
        message: 'Synthetic development benchmark — Not hardware'
      }
    });
    addLog('Activated Synthetic Development Signal — Not Hardware', 'info', 'Source');
    addToast('Activated Synthetic Benchmark', 'info');
    setCurrentDestination('live');
  }, [addLog, addToast]);

  // Audio Playback Controls
  const handleTogglePlay = useCallback(() => {
    if (isPlaying) {
      bridgeClient.pauseStream();
      audioEngine.pause();
      setIsPlaying(false);
      addLog('Stream & playback paused', 'info', 'Transport');
    } else {
      bridgeClient.resumeStream();
      audioEngine.play();
      setIsPlaying(true);
      addLog('Stream & playback resumed', 'info', 'Transport');
    }
  }, [isPlaying, addLog]);

  const handleRestart = useCallback(() => {
    audioEngine.seek(0);
    setCurrentTime(0);
    addLog('Playback reset to origin (00:00.0)', 'info', 'AudioEngine');
  }, [addLog]);

  const handleStepForwardCycle = useCallback(() => {
    audioEngine.stepForwardCycle();
    addLog('Step forward by cardiac cycle (~0.83s)', 'info', 'AudioEngine');
  }, [addLog]);

  const handleSeek = useCallback((time: number) => {
    audioEngine.seek(time);
    setCurrentTime(time);
  }, []);

  const handleVolumeChange = useCallback((vol: number) => {
    audioEngine.setVolume(vol);
    setVolume(vol);
  }, []);

  const handleToggleMute = useCallback(() => {
    const muted = audioEngine.toggleMute();
    setIsMuted(muted);
    addLog(muted ? 'Audio output muted' : 'Audio output unmuted', 'info', 'AudioEngine');
  }, [addLog]);

  const handleChangeFilterPreset = useCallback((preset: FilterPreset) => {
    if (sourceType !== 'file' && sourceType !== 'sample') bridgeClient.setFilter(preset);
    audioEngine.setFilterPreset(preset);
    setFilterPreset(preset);
    addLog(`DSP passband switched to: ${preset.toUpperCase()}`, 'info', 'DSP');
    addToast(`Filter: ${preset.toUpperCase()}`, 'info');
  }, [addLog, addToast, sourceType]);

  const handleChangeFilterStrength = useCallback((strength: FilterStrength) => {
    audioEngine.setFilterStrength(strength);
    setFilterStrength(strength);
    addLog(`Filter strength set to: ${strength}`, 'info', 'DSP');
  }, [addLog]);

  const handleToggleShowRaw = useCallback(() => {
    setShowRaw(prev => {
      const next = !prev;
      addLog(next ? 'Raw comparison track enabled' : 'Raw track hidden', 'info', 'DSP');
      return next;
    });
  }, [addLog]);

  const handleToggleListeningTrack = useCallback((track: ListeningTrack) => {
    audioEngine.setListeningTrack(track);
    setListeningTrack(track);
    addLog(`Listening audition track switched to: ${track}`, 'info', 'AudioEngine');
  }, [addLog]);

  const handleExportFilteredAudio = useCallback(() => {
    const originalName = activeMetadata?.filename.replace(/\.[^/.]+$/, '') || 'HeartSound';
    const filename = `${originalName}_filtered.wav`;
    const blob = audioEngine.exportWav('filtered');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    addLog(`Exported filtered audio file: ${filename}`, 'info', 'FileIO');
    addToast(`Exported ${filename}`, 'success');
  }, [activeMetadata, addLog, addToast]);

  const handleSaveRecordingConfirm = useCallback((filename: string) => {
    const blob = audioEngine.exportWav('filtered');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setSaveAsOpen(false);
    setHasUnsavedRecording(false);
    addLog(`Recording archive saved: ${filename}`, 'info', 'FileIO');
    addToast(`Saved: ${filename}`, 'success');
  }, [addLog, addToast]);

  // Destination navigation with unsaved safeguard
  const navigateTo = useCallback((dest: NavigationDestination) => {
    if (hasUnsavedRecording && dest !== currentDestination) {
      setPendingAction(() => () => setCurrentDestination(dest));
      setConfirmDiscardOpen(true);
    } else {
      setCurrentDestination(dest);
    }
  }, [hasUnsavedRecording, currentDestination]);

  // Fullscreen toggle
  const handleToggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  }, []);

  // Keyboard Shortcuts (Section 22 & 29)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
        return;
      }

      // Space: Play/Pause
      if (e.code === 'Space') {
        e.preventDefault();
        handleTogglePlay();
      }

      // M: Mute
      if (e.key === 'm' || e.key === 'M') {
        if (!e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          handleToggleMute();
        }
      }

      // R: Show Raw
      if (e.key === 'r' || e.key === 'R') {
        if (!e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          handleToggleShowRaw();
        }
      }

      // Ctrl+Shift+D: Toggle Diagnostics
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
        e.preventDefault();
        setDiagnosticsOpen(prev => !prev);
      }

      // F11: Fullscreen
      if (e.key === 'F11') {
        e.preventDefault();
        handleToggleFullscreen();
      }

      // Esc: Close diagnostics drawer or modals
      if (e.key === 'Escape') {
        if (diagnosticsOpen) setDiagnosticsOpen(false);
        if (saveAsOpen) setSaveAsOpen(false);
        if (confirmDiscardOpen) setConfirmDiscardOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    handleTogglePlay,
    handleToggleMute,
    handleToggleShowRaw,
    handleToggleFullscreen,
    diagnosticsOpen,
    saveAsOpen,
    confirmDiscardOpen
  ]);

  // Diagnostics State Object
  const diagnosticState: DiagnosticState = {
    sourceType,
    fileName: activeMetadata?.filename,
    filePath: activeMetadata ? `/workstation/specimens/${activeMetadata.filename}` : undefined,
    inputFormat: 'WAV PCM (Linear)',
    inputSampleRate: `${sampleRate / 1000} kHz`,
    channels: '1 (Mono Bell Acoustic)',
    duration: `00:${duration.toFixed(3)} (60,000 samples)`,
    decodeStatus: 'Buffer Ready',
    internalProcessingRate: '4.0 kHz',
    resamplingStatus: 'None (Native 4 kHz match)',
    filterPreset: filterPreset === 'recommended' ? 'Narrow (20–200 Hz Dev Preset)' : filterPreset.toUpperCase(),
    filterStrength,
    packetsReceived: sourceType === 'device' ? 1420 : 0,
    droppedFrames: 0,
    estimatedLatencyMs: 0.4,
    bufferFillPercent: 98,
    recordingActive: false,
    recordingFramesWritten: 0,
    recordingElapsedSeconds: currentTime,
    logs
  };

  const audioMetrics: AudioMetrics = audioEngine.getMetrics();

  // Copy diagnostic summary
  const handleCopyDiagnostics = () => {
    const summary = `--- AUSCULTAFORGE DIAGNOSTIC TELEMETRY ---
Source: ${activeSourceName} (${sourceType})
Sample Rate: ${sampleRate} Hz
Device Lifecycle: ${deviceRuntimeState?.state ?? 'absent'}
Transport: ESP32-S3 Native USB (Hardware Rev-A proposal: CDC-ACM under review)
Telemetry: ${deviceStats ? `${deviceStats.packets_received} pkts, ${deviceStats.samples_received} smp, ${deviceStats.sequence_gaps} gaps, ${deviceStats.crc_failures} crc` : 'No hardware telemetry'}
DSP Filter: Preset ${filterPreset} (Active DSP Pipeline)`;

    navigator.clipboard.writeText(summary);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
    addToast('Diagnostic summary copied to clipboard', 'info');
  };

  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10);
  const timeStr = `${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}`;
  const defaultSaveFilename = `HeartSound_${dateStr}_${timeStr}.wav`;

  return (
    <div
      id="app-container"
      className="flex flex-col h-screen w-screen overflow-hidden select-none transition-colors"
      style={{
        backgroundColor: 'var(--bg-canvas)',
        color: 'var(--on-surface)',
      }}
    >
      {/* 1. Window Header Bar */}
      <Header
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
        onToggleDiagnostics={() => setDiagnosticsOpen(!diagnosticsOpen)}
        isFullscreen={isFullscreen}
        onToggleFullscreen={handleToggleFullscreen}
        backendConnected={backendConnected}
        deviceState={deviceRuntimeState?.state ?? 'absent'}
        sampleRate={sampleRate}
        isRecording={isRecording}
        recordingElapsedSeconds={recordingElapsedSeconds}
        recordingSessionId={recordingSessionId}
        onStopRecording={handleStopRecording}
      />

      {/* 2. Main Window Body: Fixed Sidebar + Fluid Content */}
      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar
          currentDestination={currentDestination}
          onNavigate={navigateTo}
          isDark={isDark}
          onToggleTheme={() => setIsDark(!isDark)}
          onToggleDiagnostics={() => setDiagnosticsOpen(!diagnosticsOpen)}
          diagnosticsOpen={diagnosticsOpen}
          hasActiveFileOrDevice={rawData.length > 0}
        />

        {/* Center Main Viewport */}
        <main className="pl-48 pt-8 pb-6 flex-1 flex flex-col overflow-hidden relative">
          {currentDestination === 'home' && (
            <HomeView
              onOpenFile={handleOpenFile}
              onNavigate={navigateTo}
              onSelectSample={loadSample}
              onDetectDevice={handleDetectDevice}
              deviceConnected={deviceRuntimeState?.connected ?? false}
              deviceConnecting={deviceConnecting}
              onToggleDiagnostics={() => setDiagnosticsOpen(true)}
              backendConnected={backendConnected}
              deviceRuntimeState={deviceRuntimeState}
              sampleRate={sampleRate}
            />
          )}

          {currentDestination === 'live' && (
            <LiveWorkspace
              activeSourceName={activeSourceName}
              sourceType={sourceType}
              activeMetadata={activeMetadata}
              rawData={rawData}
              filteredData={filteredData}
              sampleRate={sampleRate}
              duration={duration}
              currentTime={currentTime}
              isPlaying={isPlaying}
              onTogglePlay={handleTogglePlay}
              onRestart={handleRestart}
              onStepForwardCycle={handleStepForwardCycle}
              onSeek={handleSeek}
              volume={volume}
              onVolumeChange={handleVolumeChange}
              isMuted={isMuted}
              onToggleMute={handleToggleMute}
              filterPreset={filterPreset}
              onChangeFilterPreset={handleChangeFilterPreset}
              filterStrength={filterStrength}
              onChangeFilterStrength={handleChangeFilterStrength}
              showRaw={showRaw}
              onToggleShowRaw={handleToggleShowRaw}
              listeningTrack={listeningTrack}
              onToggleListeningTrack={handleToggleListeningTrack}
              visibleWindowSec={visibleWindowSec}
              onChangeWindowSec={setVisibleWindowSec}
              isDark={isDark}
              isFullscreen={isFullscreen}
              onToggleFullscreen={handleToggleFullscreen}
              onToggleDiagnostics={() => setDiagnosticsOpen(true)}
              onExportFiltered={handleExportFilteredAudio}
              liveMetrics={liveMetrics}
              streamQuality={streamQuality}
              backendConnected={backendConnected}
              isRecording={isRecording}
              onStartRecording={handleStartRecording}
              onStopRecording={handleStopRecording}
              recordingElapsedSeconds={recordingElapsedSeconds}
              droppedDisplayFrames={droppedDisplayFrames}
              spectralFrame={spectralFrame}
              displayPointsPerSec={sourceType === 'file' || sourceType === 'sample' ? sampleRate : 3200}
            />
          )}

          {currentDestination === 'samples' && (
            <SamplesView
              onSelectSample={loadSample}
              onReplaySession={handleReplaySession}
              onAnalyzeSession={handleAnalyzeSession}
              activeSampleId={activeMetadata?.id}
              isDark={isDark}
            />
          )}

          {currentDestination === 'analysis' && (
            <AnalysisWorkbench
              initialSessionId={analysisTargetSessionId}
              isDark={isDark}
              onNavigateToLive={() => setCurrentDestination('live')}
              onNavigateToSamples={() => setCurrentDestination('samples')}
              addToast={addToast}
            />
          )}

          {currentDestination === 'device' && (
            <DeviceView
              deviceState={deviceState}
              deviceRuntimeState={deviceRuntimeState}
              deviceStats={deviceStats}
              onDetectDevice={handleDetectDevice}
              onDisconnectDevice={handleDisconnectDevice}
              onUseDevice={handleUseDeviceInLive}
              isConnecting={deviceConnecting}
              isDark={isDark}
              backendConnected={backendConnected}
              activeSourceName={activeSourceName}
              sourceType={sourceType}
              onSelectMockSource={handleSelectMockSource}
              onNavigateToSamples={() => setCurrentDestination('samples')}
            />
          )}

          {currentDestination === 'research' && (
            <ResearchLabView
              isDark={isDark}
              backendConnected={backendConnected}
              addToast={addToast}
            />
          )}

          {currentDestination === 'settings' && (

            <SettingsView
              isDark={isDark}
              onToggleTheme={() => setIsDark(!isDark)}
              volume={volume}
              onVolumeChange={handleVolumeChange}
              defaultWindowSec={visibleWindowSec}
              onChangeDefaultWindowSec={setVisibleWindowSec}
              defaultFilterPreset={filterPreset}
              onChangeDefaultFilterPreset={handleChangeFilterPreset}
              onToggleDiagnostics={() => setDiagnosticsOpen(true)}
              onClearLogs={() => setLogs([])}
            />
          )}
        </main>

        {/* 3. Engineering & Diagnostics Right Drawer ("Stats for Nerds") */}
        <DiagnosticsDrawer
          isOpen={diagnosticsOpen}
          onClose={() => setDiagnosticsOpen(false)}
          diagnosticState={diagnosticState}
          audioMetrics={audioMetrics}
          isPlaybackActive={audioEngine.getIsPlaying()}
          deviceState={deviceState}
          deviceRuntimeState={deviceRuntimeState}
          deviceStats={deviceStats}
          deviceEvents={deviceEvents}
          onCopySummary={handleCopyDiagnostics}
          copySuccess={copySuccess}
          isDark={isDark}
        />
      </div>

      {/* 4. Bottom Status Footer Strip */}
      <FooterStatus
        isStreaming={isPlaying}
        backendConnected={backendConnected}
        backendEndpoint={bridgeClient.getEndpoint()}
        deviceConnected={deviceRuntimeState?.connected ?? false}
        deviceState={deviceRuntimeState?.state ?? 'absent'}
        sampleRate={sampleRate}
        isHealthy={streamQuality.is_healthy}
        isRecording={isRecording}
        sourceName={activeSourceName}
        sourceType={sourceType}
        totalBlocks={streamQuality.total_blocks}
        droppedBlocks={streamQuality.dropped_blocks}
        uiDroppedFrames={droppedDisplayFrames}
      />

      {/* 5. Modals & Dialogs */}
      <SaveAsDialog
        isOpen={saveAsOpen}
        defaultFilename={defaultSaveFilename}
        duration={duration}
        onSaveConfirm={handleSaveRecordingConfirm}
        onCancel={() => setSaveAsOpen(false)}
      />

      <ConfirmDiscardDialog
        isOpen={confirmDiscardOpen}
        onSave={() => {
          setConfirmDiscardOpen(false);
          setSaveAsOpen(true);
        }}
        onDiscard={() => {
          setConfirmDiscardOpen(false);
          setHasUnsavedRecording(false);
          if (pendingAction) {
            pendingAction();
            setPendingAction(null);
          }
        }}
        onCancel={() => {
          setConfirmDiscardOpen(false);
          setPendingAction(null);
        }}
      />

      <ToastNotification
        toasts={toasts}
        onDismiss={(id) => setToasts(prev => prev.filter(t => t.id !== id))}
      />
    </div>
  );
}
