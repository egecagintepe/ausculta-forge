import React from 'react';

interface FooterStatusProps {
  backendConnected?: boolean;
  sampleRate?: number;
  isHealthy?: boolean;
  isRecording?: boolean;
  sourceName?: string;
}

export const FooterStatus: React.FC<FooterStatusProps> = ({
  backendConnected = false,
  sampleRate = 4000,
  isHealthy = true,
  isRecording = false,
  sourceName = 'Synthetic PCG',
}) => {
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
            {backendConnected ? 'CONNECTED (127.0.0.1:8000)' : 'DISCONNECTED'}
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
