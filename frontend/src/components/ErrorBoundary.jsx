import React from 'react';
import i18n from '../i18n';

// Global render-error boundary. Without this, any exception thrown during
// render unmounts the whole React tree and leaves a blank white screen — a
// terrible failure mode. This catches it and shows a branded, localized
// fallback with a reload button. Uses inline styles + hardcoded brand colors
// so the fallback renders even if something in the styling layer is what broke.
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Optional reporting hook — if an error tracker (e.g. Sentry) is wired up
    // later it can set window.__dipzeeReportError; until then this is a no-op
    // beyond the console log.
    if (typeof window !== 'undefined' && typeof window.__dipzeeReportError === 'function') {
      try { window.__dipzeeReportError(error, info); } catch (_) { /* never let reporting throw */ }
    }
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px', background: '#0B0F1E', color: '#E7EAF5', textAlign: 'center',
        fontFamily: '-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
      }}>
        <div style={{ maxWidth: '440px' }}>
          <div style={{ fontSize: '22px', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '8px' }}>
            {i18n.t('common.errorTitle')}
          </div>
          <p style={{ color: '#98A2C0', fontSize: '15px', lineHeight: 1.6, marginBottom: '22px' }}>
            {i18n.t('common.errorDesc')}
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              background: '#16E0A3', color: '#0B0F1E', border: 'none', fontWeight: 600,
              padding: '11px 22px', borderRadius: '10px', fontSize: '15px', cursor: 'pointer',
            }}
          >
            {i18n.t('common.reload')}
          </button>
        </div>
      </div>
    );
  }
}
