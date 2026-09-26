import React, { useState } from 'react';
import { Download, AlertTriangle, CheckCircle2, X } from 'lucide-react';

// Unsaved Recording Protection Modal (Section 21 & 33)
interface ConfirmDiscardDialogProps {
  isOpen: boolean;
  onSave: () => void;
  onDiscard: () => void;
  onCancel: () => void;
}

export const ConfirmDiscardDialog: React.FC<ConfirmDiscardDialogProps> = ({
  isOpen,
  onSave,
  onDiscard,
  onCancel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs select-none p-4">
      <div
        className="w-full max-w-md rounded-xl border p-6 flex flex-col gap-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150"
        style={{
          backgroundColor: 'var(--surface-card)',
          borderColor: 'var(--border-strong)',
        }}
      >
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-[var(--status-warning)]/15 border border-[var(--status-warning)] text-[var(--status-warning)] flex items-center justify-center shrink-0">
            <AlertTriangle size={20} />
          </div>

          <div className="flex flex-col gap-1">
            <h3 className="font-serif-display text-lg font-semibold text-[var(--on-surface)]">
              Unsaved Recording
            </h3>
            <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
              You have a recording that has not been saved. What would you like to do before opening another source?
            </p>
          </div>
        </div>

        <div
          className="flex items-center justify-end gap-2.5 pt-3 border-t"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <button
            onClick={onCancel}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium border border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onDiscard}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium border border-[var(--status-danger)] text-[var(--status-danger)] hover:bg-[var(--status-danger)]/10 transition-colors cursor-pointer"
          >
            Discard
          </button>
          <button
            onClick={onSave}
            className="px-4 py-1.5 rounded-lg text-xs font-medium text-white shadow-xs transition-transform active:scale-95 cursor-pointer"
            style={{ backgroundColor: 'var(--accent-oxblood)' }}
          >
            Save Recording
          </button>
        </div>
      </div>
    </div>
  );
};

// Save As Dialog (Windows Desktop Native-Style Dialog)
interface SaveAsDialogProps {
  isOpen: boolean;
  defaultFilename: string;
  duration: number;
  onSaveConfirm: (filename: string) => void;
  onCancel: () => void;
}

export const SaveAsDialog: React.FC<SaveAsDialogProps> = ({
  isOpen,
  defaultFilename,
  duration,
  onSaveConfirm,
  onCancel,
}) => {
  const [filename, setFilename] = useState(defaultFilename);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveConfirm(filename.endsWith('.wav') ? filename : `${filename}.wav`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs select-none p-4">
      <form
        onSubmit={handleSave}
        className="w-full max-w-lg rounded-xl border p-6 flex flex-col gap-5 shadow-2xl animate-in fade-in zoom-in-95 duration-150"
        style={{
          backgroundColor: 'var(--surface-card)',
          borderColor: 'var(--border-strong)',
        }}
      >
        <div
          className="flex items-center justify-between border-b pb-3"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2">
            <Download size={18} className="text-[var(--accent-oxblood)]" />
            <h3 className="font-serif-display text-base font-semibold text-[var(--on-surface)]">
              Save Audio Recording As
            </h3>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 rounded text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-3.5 text-xs">
          <div className="flex flex-col gap-1.5">
            <label className="text-[var(--on-surface-variant)] font-medium">File name:</label>
            <input
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-raised)] text-[var(--on-surface)] font-mono-code text-xs outline-none focus:border-[var(--accent-oxblood)]"
              autoFocus
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[var(--on-surface-variant)] font-medium">Save as type:</label>
            <div className="px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-muted)] text-[var(--on-surface)] font-mono-code text-xs">
              Waveform Audio File (*.wav) · 16-bit PCM Linear 4.0 kHz
            </div>
          </div>

          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border-subtle)] font-mono-code text-[11px] text-[var(--on-surface-variant)]">
            <span>Duration: {duration.toFixed(1)} seconds</span>
            <span>Channels: 1 (Mono Bell/Diaphragm)</span>
          </div>
        </div>

        <div
          className="flex items-center justify-end gap-2.5 pt-2 border-t"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <button
            type="button"
            onClick={onCancel}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium border border-[var(--border-subtle)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] hover:bg-[var(--surface-muted)] transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-1.5 rounded-lg text-xs font-medium text-white shadow-xs transition-transform active:scale-95 cursor-pointer flex items-center gap-1.5"
            style={{ backgroundColor: 'var(--accent-oxblood)' }}
          >
            <Download size={13} />
            <span>Save Recording</span>
          </button>
        </div>
      </form>
    </div>
  );
};

// Toast notification component
export interface ToastInfo {
  id: string;
  message: string;
  type?: 'info' | 'success' | 'warning';
}

export const ToastNotification: React.FC<{
  toasts: ToastInfo[];
  onDismiss: (id: string) => void;
}> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-9 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className="pointer-events-auto flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-lg border shadow-lg text-xs font-medium animate-in slide-in-from-bottom-2 duration-150"
          style={{
            backgroundColor: 'var(--surface-raised)',
            borderColor: 'var(--border-strong)',
            color: 'var(--on-surface)',
          }}
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 size={15} className="text-[var(--status-success)] shrink-0" />
            <span>{t.message}</span>
          </div>
          <button
            onClick={() => onDismiss(t.id)}
            className="text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] cursor-pointer"
          >
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
};
