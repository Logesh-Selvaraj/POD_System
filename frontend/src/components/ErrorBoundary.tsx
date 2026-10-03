import { Component, type ErrorInfo, type ReactNode } from 'react';

/**
 * ErrorBoundary — Production-safe React class component that catches unhandled
 * JavaScript errors anywhere in its child component tree during rendering,
 * lifecycle methods, and constructors.
 *
 * WHY: React does not catch errors in event handlers (those use try/catch in
 * App.tsx), but it does not automatically recover from errors thrown during
 * render.  Without a boundary the entire application unmounts on the first
 * uncaught render error, leaving the user with a blank white screen and no
 * recovery path.  This boundary isolates failures so only the subtree that
 * threw is replaced by a user-friendly fallback while the rest of the app
 * remains operational.
 */

interface Props {
  /** Child tree to protect. */
  children: ReactNode;
  /**
   * Optional custom fallback element.  If omitted the default branded
   * fallback UI is rendered instead.
   */
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  /**
   * getDerivedStateFromError is called during the render phase after a child
   * throws.  It must be a static method because React calls it before the
   * component instance is fully re-initialised.
   *
   * Returning { hasError: true } triggers a re-render that displays the
   * fallback UI instead of the crashed subtree.
   */
  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  /**
   * componentDidCatch is called during the commit phase.  It receives the
   * error and the React component stack trace (errorInfo), which is safe to
   * log without exposing PII.
   *
   * In production this is the correct place to forward errors to a monitoring
   * service (e.g. Sentry, Datadog).  The console.error call is retained for
   * developer visibility during development.
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[POD ErrorBoundary] Uncaught render error:', error, errorInfo);
    // Future: send to monitoring service here.
    // e.g. Sentry.captureException(error, { contexts: { react: errorInfo } });
    this.setState({ errorInfo });
  }

  /** Allow the user to dismiss the fallback and attempt a fresh render. */
  handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Prefer a caller-supplied fallback (useful for targeted per-section
      // boundaries), otherwise show the default full-page recovery screen.
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0f172a',
            color: '#e2e8f0',
            padding: '2rem',
            fontFamily: 'Inter, system-ui, sans-serif',
            textAlign: 'center',
          }}
        >
          {/* Alert icon */}
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>

          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: '#f8fafc' }}>
            Something went wrong
          </h1>

          <p style={{ fontSize: '0.9rem', color: '#94a3b8', maxWidth: '420px', marginBottom: '1.5rem', lineHeight: 1.6 }}>
            An unexpected error occurred in the application. Your offline evidence queue
            and delivery data are safe.
          </p>

          {/* Show error message in development for quick diagnosis */}
          {import.meta.env.DEV && this.state.error && (
            <pre
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '1rem',
                fontSize: '0.75rem',
                color: '#f87171',
                maxWidth: '600px',
                overflowX: 'auto',
                textAlign: 'left',
                marginBottom: '1.5rem',
              }}
            >
              {this.state.error.toString()}
            </pre>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            {/* Try again — re-renders the child tree without a full page reload */}
            <button
              onClick={this.handleReset}
              style={{
                padding: '0.6rem 1.4rem',
                background: '#10b981',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              Try again
            </button>

            {/* Hard reload as the ultimate fallback */}
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '0.6rem 1.4rem',
                background: '#1e293b',
                color: '#cbd5e1',
                border: '1px solid #334155',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
