import React, { useEffect, useState } from 'react';
import {
  FolderArchive,
  Play,
  Check,
  Disc,
  ArrowRight,
  Sliders,
  ShieldCheck,
  RefreshCw,
  Clock,
  HardDrive
} from 'lucide-react';
import { HeartSoundMetadata } from '../types';
import { STARTER_SAMPLES } from '../audio/samplesData';
import { bridgeClient, SessionItem } from '../api/bridgeClient';

interface SamplesViewProps {
  onSelectSample: (sample: HeartSoundMetadata) => void;
  onReplaySession?: (sessionId: string) => void;
  activeSampleId?: string;
  isDark: boolean;
}

export const SamplesView: React.FC<SamplesViewProps> = ({
  onSelectSample,
  onReplaySession,
  activeSampleId,
}) => {
  const [activeTab, setActiveTab] = useState<'specimens' | 'sessions'>('specimens');
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(false);
  const [replayingId, setReplayingId] = useState<string | null>(null);

  const loadSessionsList = async () => {
    setLoadingSessions(true);
    try {
      const list = await bridgeClient.fetchSessions();
      setSessions(list);
    } catch {
      // ignore error
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'sessions') {
      loadSessionsList();
    }
  }, [activeTab]);

  const handleReplayClick = async (sessionId: string) => {
    setReplayingId(sessionId);
    try {
      const ok = await bridgeClient.replaySession(sessionId);
      if (ok && onReplaySession) {
        onReplaySession(sessionId);
      }
    } finally {
      setReplayingId(null);
    }
  };

  return (
    <div
      id="samples-view"
      className="flex-1 flex flex-col h-full overflow-y-auto px-6 py-5 select-none transition-colors"
      style={{
        backgroundColor: 'var(--bg-canvas)'
      }}
    >
      <div className="max-w-5xl mx-auto w-full flex flex-col gap-6 pb-8">
        {/* Header Section */}
        <div
          className="pb-4 border-b flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 font-mono-code text-[11px] uppercase tracking-widest text-[var(--accent-metal)] font-semibold">
              <span>Auscultation Signals &amp; Provenance</span>
              <span>•</span>
              <span>Corpus &amp; Sessions</span>
            </div>
            <h1 className="font-serif-display text-2xl font-semibold text-[var(--on-surface)] tracking-tight">
              Auscultation Signals &amp; Recorded Sessions
            </h1>
            <p className="font-serif-display italic text-xs text-[var(--on-surface-variant)] max-w-xl">
              Inspect starter cardiac sound models or browse and replay locally recorded acquisition sessions.
            </p>
          </div>

          {/* Sub-tab Switcher */}
          <div
            className="flex items-center p-1 rounded-lg border font-mono-code text-xs shadow-xs"
            style={{
              backgroundColor: 'var(--surface-muted)',
              borderColor: 'var(--border-subtle)'
            }}
          >
            <button
              onClick={() => setActiveTab('specimens')}
              className={`px-3 py-1 rounded transition-colors cursor-pointer font-medium ${
                activeTab === 'specimens'
                  ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                  : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
              }`}
            >
              Specimens ({STARTER_SAMPLES.length})
            </button>
            <button
              onClick={() => setActiveTab('sessions')}
              className={`px-3 py-1 rounded transition-colors cursor-pointer font-medium ${
                activeTab === 'sessions'
                  ? 'bg-[var(--surface-card)] text-[var(--accent-oxblood)] font-bold shadow-xs'
                  : 'text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]'
              }`}
            >
              Recorded Sessions ({sessions.length})
            </button>
          </div>
        </div>

        {/* Tab 1: Starter Specimens */}
        {activeTab === 'specimens' && (
          <div className="flex flex-col gap-4">
            {STARTER_SAMPLES.map((sample, idx) => {
              const isActive = sample.id === activeSampleId;

              return (
                <div
                  key={sample.id}
                  id={`specimen-card-${sample.id}`}
                  className={`rounded-xl border p-5 transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 relative overflow-hidden shadow-xs ${
                    isActive
                      ? 'border-[var(--accent-oxblood)] ring-1 ring-[var(--accent-oxblood)]'
                      : 'hover:border-[var(--border-strong)]'
                  }`}
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: isActive ? 'var(--accent-oxblood)' : 'var(--border-subtle)'
                  }}
                >
                  {isActive && (
                    <div className="absolute top-0 left-0 bottom-0 w-1 bg-[var(--accent-oxblood)]" />
                  )}

                  <div className="flex items-start gap-4">
                    <div
                      className="w-11 h-11 rounded-lg border flex items-center justify-center shrink-0 font-mono-code text-xs font-bold"
                      style={{
                        backgroundColor: 'var(--surface-muted)',
                        borderColor: 'var(--border-strong)',
                        color: 'var(--accent-oxblood)'
                      }}
                    >
                      0{idx + 1}
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono-code text-[10px] px-2 py-0.5 rounded bg-[var(--surface-muted)] text-[var(--on-surface-variant)] border border-[var(--border-subtle)] font-semibold">
                          {sample.category}
                        </span>
                        <span className="font-mono-code text-[10px] text-[var(--accent-metal)] font-medium">
                          {sample.durationSeconds.toFixed(1)}s · {sample.sampleRateHz / 1000} kHz · Float32 App
                        </span>
                      </div>

                      <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                        {sample.title}
                      </h3>

                      <p className="text-xs text-[var(--on-surface-variant)] max-w-xl leading-relaxed">
                        {sample.description}
                      </p>

                      <span className="font-mono-code text-[10px] text-[var(--on-surface-variant)] opacity-80 pt-0.5">
                        Source: {sample.sourceAttribution}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 self-end sm:self-center">
                    <div className="hidden md:flex flex-col items-end text-right font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                      {sample.quality.score != null ? (
                        <>
                          <span className="text-[var(--status-success)] font-semibold">
                            Quality · {sample.quality.score}/100
                          </span>
                          {sample.quality.snrDb != null && <span>SNR: {sample.quality.snrDb} dB</span>}
                        </>
                      ) : (
                        <span className="text-[var(--accent-metal)] font-semibold">
                          {sample.quality.message || 'Synthetic Model'}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => onSelectSample(sample)}
                      className={`px-4 py-2 rounded-lg text-xs font-medium border flex items-center gap-2 transition-all shadow-xs cursor-pointer active:scale-95 ${
                        isActive
                          ? 'bg-[var(--accent-oxblood)] text-white border-[var(--accent-oxblood)]'
                          : 'bg-[var(--surface-card)] text-[var(--on-surface)] border-[var(--border-strong)] hover:border-[var(--accent-oxblood)] hover:text-[var(--accent-oxblood)]'
                      }`}
                    >
                      {isActive ? (
                        <>
                          <Check size={14} />
                          <span>Active Ingest</span>
                        </>
                      ) : (
                        <>
                          <Play size={14} />
                          <span>Load Sample</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 2: Recorded Sessions Browser */}
        {activeTab === 'sessions' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="font-mono-code text-xs text-[var(--on-surface-variant)]">
                Local Sessions from <code className="font-mono-code text-[11px]">experiments/sessions/</code>
              </span>
              <button
                onClick={loadSessionsList}
                disabled={loadingSessions}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono-code text-xs text-[var(--accent-oxblood)] border-[var(--border-strong)] hover:bg-[var(--surface-muted)] cursor-pointer"
              >
                <RefreshCw size={13} className={loadingSessions ? 'animate-spin' : ''} />
                <span>Refresh Sessions</span>
              </button>
            </div>

            {sessions.length === 0 ? (
              <div
                className="rounded-xl border p-12 text-center flex flex-col items-center gap-3 shadow-xs"
                style={{
                  backgroundColor: 'var(--surface-card)',
                  borderColor: 'var(--border-subtle)'
                }}
              >
                <HardDrive size={36} className="text-[var(--accent-metal)]" />
                <h4 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
                  No recorded sessions yet
                </h4>
                <p className="text-xs text-[var(--on-surface-variant)] max-w-md">
                  Click the <strong>Record Session</strong> button in the Live Workspace to capture a raw audio session with full JSON provenance metadata.
                </p>
              </div>
            ) : (
              sessions.map((sess) => (
                <div
                  key={sess.session_id}
                  className="rounded-xl border p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs"
                  style={{
                    backgroundColor: 'var(--surface-card)',
                    borderColor: 'var(--border-subtle)'
                  }}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className="w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 text-[var(--accent-oxblood)]"
                      style={{
                        backgroundColor: 'var(--surface-muted)',
                        borderColor: 'var(--border-subtle)'
                      }}
                    >
                      <Disc size={20} />
                    </div>

                    <div className="flex flex-col gap-1">
                      <div className="flex flex-wrap items-center gap-2 font-mono-code text-[11px]">
                        <span className="font-bold text-[var(--accent-oxblood)]">
                          {sess.session_id}
                        </span>
                        <span className="text-[var(--accent-metal)]">•</span>
                        <span className="text-[var(--on-surface-variant)]">
                          {new Date(sess.started_at_utc).toLocaleString()}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 font-mono-code text-[10px] text-[var(--on-surface-variant)]">
                        <span>Source: <strong>{sess.source}</strong></span>
                        <span>•</span>
                        <span>{sess.duration_s.toFixed(2)}s ({sess.total_samples} samples)</span>
                        <span>•</span>
                        <span>{sess.sample_rate_hz} Hz</span>
                        <span>•</span>
                        <span className={sess.stream_quality.is_healthy ? 'text-[var(--status-success)]' : 'text-[var(--status-warning)]'}>
                          {sess.stream_quality.is_healthy ? 'Optimal (0 drops)' : `${sess.stream_quality.dropped_blocks} dropped`}
                        </span>
                      </div>

                      <div className="font-mono-code text-[9px] text-[var(--accent-metal)] truncate max-w-lg">
                        SHA-256: {sess.raw_wav_sha256}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleReplayClick(sess.session_id)}
                    disabled={replayingId === sess.session_id}
                    className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-[var(--accent-oxblood)] hover:opacity-90 flex items-center gap-2 shadow-xs cursor-pointer active:scale-95 shrink-0"
                  >
                    <Play size={14} className={replayingId === sess.session_id ? 'animate-spin' : ''} />
                    <span>Replay in Pipeline</span>
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
