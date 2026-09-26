import React from 'react';
import {
  Activity,
  FolderOpen,
  Stethoscope,
  Sliders,
  Sun,
  Moon,
  Terminal,
  Layers
} from 'lucide-react';
import { NavigationDestination } from '../types';

interface SidebarProps {
  currentDestination: NavigationDestination;
  onNavigate: (destination: NavigationDestination) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  onToggleDiagnostics: () => void;
  diagnosticsOpen: boolean;
  hasActiveFileOrDevice: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentDestination,
  onNavigate,
  isDark,
  onToggleTheme,
  onToggleDiagnostics,
  diagnosticsOpen,
  hasActiveFileOrDevice,
}) => {
  const navItems: { id: NavigationDestination; label: string; subLabel: string; icon: React.ReactNode }[] = [
    {
      id: 'live',
      label: 'Live Telemetry',
      subLabel: 'Live',
      icon: <Activity size={18} strokeWidth={2} />
    },
    {
      id: 'samples',
      label: 'Specimen Archives',
      subLabel: 'Samples',
      icon: <FolderOpen size={18} strokeWidth={2} />
    },
    {
      id: 'device',
      label: 'Sensor Hardware',
      subLabel: 'Device',
      icon: <Stethoscope size={18} strokeWidth={2} />
    },
    {
      id: 'settings',
      label: 'DSP & Calibration',
      subLabel: 'Settings',
      icon: <Sliders size={18} strokeWidth={2} />
    }
  ];

  return (
    <aside
      id="app-sidebar"
      className="fixed left-0 top-8 bottom-6 w-48 z-40 flex flex-col justify-between py-3 border-r select-none transition-colors"
      style={{
        backgroundColor: 'var(--surface-card)',
        borderColor: 'var(--border-subtle)',
        color: 'var(--on-surface)'
      }}
    >
      {/* Top Header & Navigation Section */}
      <div className="flex flex-col gap-3">
        {/* Modality Console Header */}
        <button
          onClick={() => onNavigate('home')}
          className="px-3 pb-2 border-b text-left group cursor-pointer"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="font-mono-code text-[10px] uppercase tracking-wider text-[var(--accent-metal)] font-bold">
            Modality Console
          </div>
          <div className="font-serif-display text-lg font-semibold text-[var(--accent-oxblood)] tracking-tight">
            Precision IV
          </div>
        </button>

        {/* Primary Navigation Items */}
        <nav className="flex flex-col gap-1 px-2">
          {navItems.map(item => {
            const isSelected = currentDestination === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded text-xs transition-colors text-left cursor-pointer ${
                  isSelected
                    ? 'bg-[var(--accent-oxblood)] text-white font-semibold border-l-2 border-[var(--accent-metal)] shadow-xs'
                    : 'text-[var(--on-surface-variant)] hover:bg-[var(--surface-muted)] hover:text-[var(--on-surface)] font-medium'
                }`}
              >
                <span className={isSelected ? 'text-white' : 'text-[var(--accent-metal)]'}>
                  {item.icon}
                </span>
                <div className="flex flex-col leading-tight">
                  <span>{item.label}</span>
                </div>
                {item.id === 'live' && hasActiveFileOrDevice && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[var(--status-success)] animate-pulse" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Console Utilities */}
      <div className="px-3 flex flex-col gap-2.5 border-t pt-3" style={{ borderColor: 'var(--border-subtle)' }}>
        {/* Illumination toggle */}
        <button
          id="btn-sidebar-illumination"
          onClick={onToggleTheme}
          className="flex items-center justify-between text-xs text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] cursor-pointer"
        >
          <span className="font-mono-code text-[10px] uppercase tracking-wider text-[var(--on-surface-variant)]">
            ILLUMINATION
          </span>
          <div className="flex items-center">
            {isDark ? <Moon size={16} className="text-[var(--status-warning)]" /> : <Sun size={16} className="text-[var(--accent-metal)]" />}
          </div>
        </button>

        {/* Diagnostics Terminal Button */}
        <button
          id="btn-sidebar-diagnostics"
          onClick={onToggleDiagnostics}
          className={`flex items-center justify-between px-2 py-1 rounded border text-xs transition-colors cursor-pointer ${
            diagnosticsOpen
              ? 'bg-[var(--accent-soft)] border-[var(--accent-oxblood)] text-[var(--accent-oxblood)]'
              : 'bg-[var(--surface-muted)] border-[var(--border-subtle)] text-[var(--on-surface)] hover:border-[var(--border-strong)]'
          }`}
        >
          <div className="flex items-center gap-1.5 font-mono-code text-[11px] font-semibold">
            <Terminal size={14} className="text-[var(--accent-metal)]" />
            <span>DIAGNOSTICS</span>
          </div>
          <kbd className="font-mono-code text-[10px] text-[var(--on-surface-variant)] bg-[var(--surface-card)] px-1 rounded border border-[var(--border-subtle)]">
            ^⇧D
          </kbd>
        </button>

        {/* OS / Platform Metadata */}
        <div className="flex items-center justify-between font-mono-code text-[10px] text-[var(--on-surface-variant)] pt-1 border-t border-[var(--border-subtle)]/50">
          <span className="tracking-wider">OS: WIN-X64</span>
          <span className="font-bold">v0.1.4-PROD</span>
        </div>
      </div>
    </aside>
  );
};
