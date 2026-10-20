import React from 'react';

interface FooterStatusProps {
  backendConnected?: boolean;
  backendEndpoint?: string;
  deviceConnected?: boolean;
  deviceState?: string;
  sampleRate?: number;
  isHealthy?: boolean;
  isRecording?: boolean;
  sourceName?: string;
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
}) => {
  const getDeviceDisplay = () => {
    if (!backendConnected) {
      return { text: 'UNKNOWN (BRIDGE OFFLINE)', color: 'text-[var(--status-warning)]' };
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
        return { text: 'ABSENT (NO HARDWARE)', color: 'text-[var(--on-surface-variant)]' };
    }
  };

  const devInfo = getDeviceDisplay();

  return (
    <footer
      id="app-footer"
      className="fixed bottom-0 left-48 right-0 h-6 z-40 border-t flex items-center justify-between px-4 font-mono-code text-[10px] select-none transition-colors"
      style={{
        backgroundColor: 'var(--surface-muted)',
        borderColor: 'var(--border-subtle)',
        color: 'var(--on-surface-variant)'
      }}
    >
      <div className="flex items-center gap-3">
        <span>
          BRIDGE:{' '}
          <strong className={backendConnected ? 'text-[var(--status-success)] font-semibold' : 'text-[var(--status-warning)] font-semibold'}>
            {backendConnected ? `CONNECTED (${backendEndpoint || '127.0.0.1:8000'})` : 'DISCONNECTED'}
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
          SAMPLE RATE: <strong className="text-[var(--on-surface)] font-semibold">{(sampleRate / 1000).toFixed(1)} kHz · Float32 App</strong>
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span>
          STREAM HEALTH:{' '}
          <strong className={isHealthy ? 'text-[var(--status-success)] font-semibold' : 'text-[var(--status-warning)] font-semibold'}>
            {isHealthy ? 'OPTIMAL' : 'ANOMALY DETECTED'}
          </strong>
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
