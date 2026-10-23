import React, { Component, ReactNode } from 'react';
import { RefreshCw, ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: { componentStack?: string } | null;
  showDetails: boolean;
}

export class ResearchErrorBoundary extends (Component as new (props: Props) => {
  props: Props;
  state: State;
  setState(state: Partial<State> | ((prevState: State) => Partial<State>)): void;
}) {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: any): void {
    console.error('Application render boundary caught an unhandled error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      const title = this.props.fallbackTitle || 'Application Render Error';
      return (
        <div
          className="rounded-xl border p-5 flex flex-col gap-4 shadow-sm font-mono-code text-xs m-4"
          style={{
            backgroundColor: 'var(--surface-card, #ffffff)',
            borderColor: 'rgba(239, 68, 68, 0.4)',
            color: 'var(--on-surface, #1e293b)',
          }}
        >
          <div className="flex items-center gap-2.5 text-rose-500 font-bold text-sm">
            <ShieldAlert size={20} className="shrink-0" />
            <span>{title}</span>
          </div>

          <p className="text-[var(--on-surface-variant, #64748b)] leading-relaxed">
            An unhandled rendering exception occurred in this view. The error was caught so the failure
            and component stack remain visible instead of leaving a blank screen.
          </p>

          <div
            className="p-3 rounded-lg border text-rose-600 dark:text-rose-400 font-bold bg-rose-500/10"
            style={{ borderColor: 'rgba(239, 68, 68, 0.25)' }}
          >
            {this.state.error?.message || 'Unknown JavaScript exception'}
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={this.handleReset}
              className="px-3.5 py-1.5 rounded-lg font-bold flex items-center gap-2 transition-colors cursor-pointer bg-[var(--accent-oxblood, #881337)] text-white hover:opacity-90"
            >
              <RefreshCw size={14} />
              <span>Reset View</span>
            </button>

            <button
              onClick={() => this.setState({ showDetails: !this.state.showDetails })}
              className="px-3 py-1.5 rounded-lg border text-[var(--on-surface-variant, #64748b)] hover:text-[var(--on-surface, #1e293b)] flex items-center gap-1.5 transition-colors cursor-pointer"
              style={{ borderColor: 'var(--border-subtle, #e2e8f0)' }}
            >
              <span>{this.state.showDetails ? 'Hide Stack' : 'Show Stack'}</span>
              {this.state.showDetails ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>

          {this.state.showDetails && this.state.errorInfo && (
            <pre
              className="p-3 rounded-lg overflow-x-auto text-[11px] max-h-48 border select-all"
              style={{
                backgroundColor: 'var(--surface-muted, #f1f5f9)',
                borderColor: 'var(--border-subtle, #e2e8f0)',
                color: 'var(--on-surface, #1e293b)',
              }}
            >
              {this.state.error?.stack}
              {'\n\nComponent Stack:'}
              {this.state.errorInfo.componentStack}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
