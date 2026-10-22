import React from 'react';
import { AudioSourceType } from '../types';

export type StreamHealthState =
  | 'BACKEND_OFFLINE'
  | 'NO_ACTIVE_ACQUISITION'
  | 'NOT_EVALUATED'
  | 'SYNTHETIC_ACTIVE'
  | 'SYNTHETIC_DEGRADED'
  | 'FILE_ACTIVE'
  | 'FILE_DEGRADED'
  | 'STREAM_HEALTHY'
  | 'STREAM_DEGRADED';

export interface StreamHealthResolution {
  state: StreamHealthState;
  label: string;
  badgeClass: string;
  telemetrySummary?: string;
}

export function resolveStreamHealthState(params: {
  backendConnected?: boolean;
  sourceType?: AudioSourceType;
  totalBlocks?: number;
  isHealthy?: boolean;
  droppedBlocks?: number;
  uiDroppedFrames?: number;
}): StreamHealthResolution {
  const {
    backendConnected = false,
    sourceType = 'none',
    totalBlocks = 0,
    isHealthy = true,
    droppedBlocks = 0,
    uiDroppedFrames = 0,
  } = params;

  if (!backendConnected) {
    return {
      state: 'BACKEND_OFFLINE',
      label: 'BACKEND OFFLINE',
      badgeClass: 'text-[var(--status-danger)] font-bold',
    };
  }

  if (sourceType === 'none') {
    return {
      state: 'NO_ACTIVE_ACQUISITION',
      label: 'NO ACTIVE ACQUISITION',
      badgeClass: 'text-[var(--on-surface-variant)] font-normal',
    };
  }

  if (totalBlocks === 0) {
    return {
      state: 'NOT_EVALUATED',
      label: 'STREAM HEALTH NOT EVALUATED',
      badgeClass: 'text-[var(--on-surface-variant)] font-normal',
    };
  }

  const hasDrops = !isHealthy || droppedBlocks > 0 || uiDroppedFrames > 0;

  if (sourceType === 'synthetic') {
    if (hasDrops) {
      return {
        state: 'SYNTHETIC_DEGRADED',
        label: 'SYNTHETIC DEGRADED',
        badgeClass: 'text-[var(--status-warning)] font-bold',
        telemetrySummary: `SIM LOSS: ${droppedBlocks} · UI DROPS: ${uiDroppedFrames}`,
      };
    }
    return {
      state: 'SYNTHETIC_ACTIVE',
      label: 'SYNTHETIC ACTIVE (SIMULATED)',
      badgeClass: 'text-[var(--accent-metal)] font-semibold',
      telemetrySummary: '0 LOSS (HOST MEMORY)',
    };
  }

  if (sourceType === 'file' || sourceType === 'sample' || sourceType === 'session') {
    if (hasDrops) {
      return {
        state: 'FILE_DEGRADED',
        label: 'FILE PLAYBACK DEGRADED',
        badgeClass: 'text-[var(--status-warning)] font-bold',
        telemetrySummary: `LOSS: ${droppedBlocks} · UI DROPS: ${uiDroppedFrames}`,
      };
    }
    return {
      state: 'FILE_ACTIVE',
      label: 'FILE PLAYBACK (HEALTHY)',
      badgeClass: 'text-[var(--accent-metal)] font-semibold',
      telemetrySummary: 'REPLAY VERIFIED',
    };
  }

  // Physical hardware source (sourceType === 'device')
  if (hasDrops) {
    return {
      state: 'STREAM_DEGRADED',
      label: 'STREAM DEGRADED',
      badgeClass: 'text-[var(--status-warning)] font-bold',
      telemetrySummary: `MCU LOSS: ${droppedBlocks} · UI DROPS: ${uiDroppedFrames}`,
    };
  }

  return {
    state: 'STREAM_HEALTHY',
    label: 'STREAM HEALTHY',
    badgeClass: 'text-[var(--status-success)] font-semibold',
    telemetrySummary: '0 LOSS · USB SYNCHRONIZED',
  };
}

export interface FooterStatusProps {
  backendConnected?: boolean;
  backendEndpoint?: string;
  deviceConnected?: boolean;
  deviceState?: string;
  sampleRate?: number;
  isHealthy?: boolean;
  isRecording?: boolean;
  sourceName?: string;
  sourceType?: AudioSourceType;
  totalBlocks?: number;
  droppedBlocks?: number;
  uiDroppedFrames?: number;
}

export const FooterStatus: React.FC<FooterStatusProps> = ({
  backendConnected = false,
  backendEndpoint,
  deviceConnected = false,
  deviceState = 'absent',
  sampleRate = 4000,
  isHealthy = true,
  isRecording = false,
  sourceName = 'None',
  sourceType = 'none' as AudioSourceType,
  totalBlocks = 0,
  droppedBlocks = 0,
  uiDroppedFrames = 0,
}) => {
  const getDeviceDisplay = () => {
    if (!backendConnected) {
      return { text: 'BRIDGE OFFLINE', color: 'text-[var(--status-warning)]' };
    }
    switch (deviceState.toLowerCase()) {
      case 'ready':
        return { text: 'READY (ESP32-S3)', color: 'text-[var(--status-success)]' };
      case 'streaming':
        return { text: 'STREAMING (ESP32-S3)', color: 'text-[var(--status-success)] font-bold animate-pulse' };
      case 'detected':
        return { text: 'DETECTED (PENDING OPEN)', color: 'text-blue-500' };
      case 'opening':
      case 'handshaking':
        return { text: `${deviceState.toUpperCase()}...`, color: 'text-amber-500 animate-pulse' };
      case 'interrupted':
        return { text: 'INTERRUPTED (USB LOST)', color: 'text-[var(--status-warning)] font-bold' };
      case 'error':
        return { text: 'ERROR (DEVICE FAULT)', color: 'text-[var(--status-danger)] font-bold' };
      case 'incompatible':
        return { text: 'INCOMPATIBLE', color: 'text-[var(--status-danger)] font-bold' };
      case 'absent':
      default:
        return { text: 'HARDWARE DISCONNECTED', color: 'text-[var(--on-surface-variant)]' };
    }
  };

  const devInfo = getDeviceDisplay();
  const streamStatus = resolveStreamHealthState({
    backendConnected,
    sourceType,
    totalBlocks,
    isHealthy,
    droppedBlocks,
    uiDroppedFrames,
  });

  return (
    <footer
      id="app-footer"
      className="fixed bottom-0 left-48 right-0 h-7 z-40 border-t flex items-center justify-between px-4 font-mono-code text-[11px] select-none transition-colors"
      style={{
        backgroundColor: 'var(--surface-muted)',
        borderColor: 'var(--border-subtle)',
        color: 'var(--on-surface-variant)'
      }}
    >
      <div className="flex items-center gap-3">
        <span>
          BRIDGE:{' '}
          <strong className={backendConnected ? 'text-[var(--status-success)] font-semibold' : 'text-[var(--status-warning)] font-bold'}>
            {backendConnected ? `CONNECTED (${backendEndpoint || '127.0.0.1:8000'})` : 'OFFLINE'}
          </strong>
        </span>
        <span className="text-[var(--border-strong)]">|</span>
        <span>
          DEVICE:{' '}
          <strong className={`${devInfo.color} font-semibold`}>
            {devInfo.text}
          </strong>
        </span>
        <span className="text-[var(--border-strong)]">|</span>
        <span>
          SOURCE: <strong className="text-[var(--on-surface)] font-semibold">{sourceName}</strong>
        </span>
        <span className="text-[var(--border-strong)]">|</span>
        <span>
          SAMPLE RATE:{' '}
          <strong className="text-[var(--on-surface)] font-semibold">
            {sourceType === 'none'
              ? 'IDLE (NO STREAM)'
              : `${(sampleRate / 1000).toFixed(1)} kHz · Float32 App`}
          </strong>
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span>
          STREAM HEALTH:{' '}
          <strong className={streamStatus.badgeClass}>
            {streamStatus.label}
          </strong>
          {streamStatus.telemetrySummary && (
            <span className="text-[10px] text-[var(--on-surface-variant)] ml-1.5 hidden md:inline">
              ({streamStatus.telemetrySummary})
            </span>
          )}
        </span>
        <span className="text-[var(--border-strong)]">|</span>
        <span>
          RECORDING:{' '}
          <strong className={isRecording ? 'text-[var(--status-danger)] font-bold animate-pulse' : 'text-[var(--on-surface-variant)]'}>
            {isRecording ? 'ACTIVE (CAPTURING RAW)' : 'OFF'}
          </strong>
        </span>
      </div>
    </footer>
  );
};
