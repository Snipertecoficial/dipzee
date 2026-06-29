import React from 'react';

// Dipzee logo: a curve that dips then rises (V) ending in an upward arrow.
export function LogoMark({ size = 28, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <rect width="48" height="48" rx="12" fill="var(--dz-primary)" />
      <path
        d="M11 18 L22 32 L31 16 L38 23"
        stroke="var(--dz-mint)"
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path d="M33 13 L39 13 L39 19" stroke="var(--dz-mint)" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function Logo({ className = '', dark = false }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <LogoMark size={30} />
      <span
        className="text-xl font-heading font-bold"
        style={{ color: dark ? '#fff' : 'var(--dz-primary)' }}
      >
        Dipzee
      </span>
    </div>
  );
}
