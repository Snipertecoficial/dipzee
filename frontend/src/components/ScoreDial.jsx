import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { signalForScore, SIGNAL_COLORS } from '../lib/format';
import { SignalBadge } from './SignalBadge';

// Signature circular Opportunity Score dial (SVG).
export function ScoreDial({ score, classification, size = 'card', showBadge = true }) {
  const { t } = useTranslation();
  const dim = size === 'hero' ? 240 : 176;
  const stroke = size === 'hero' ? 14 : 12;
  const radius = (dim - stroke * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const signal = classification || signalForScore(score);
  const color = SIGNAL_COLORS[signal] || 'var(--dz-slate)';
  const hasScore = score !== null && score !== undefined;
  const pct = hasScore ? Math.max(0, Math.min(100, score)) / 100 : 0;

  const [offset, setOffset] = useState(circumference);
  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { setOffset(circumference * (1 - pct)); return; }
    const id = requestAnimationFrame(() => setOffset(circumference * (1 - pct)));
    return () => cancelAnimationFrame(id);
  }, [pct, circumference]);

  return (
    <div className="flex flex-col items-center" data-testid="opportunity-score-dial">
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} className="-rotate-90">
          <circle cx={dim / 2} cy={dim / 2} r={radius} fill="none" stroke="var(--dz-line)" strokeWidth={stroke} />
          <circle
            cx={dim / 2} cy={dim / 2} r={radius} fill="none"
            stroke={color} strokeWidth={stroke + 2} strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 650ms ease-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-heading font-bold tnum"
            style={{ fontSize: size === 'hero' ? 56 : 44, color: 'var(--dz-fg)', lineHeight: 1 }}
            data-testid="opportunity-score-value"
          >
            {hasScore ? score : '\u2014'}
          </span>
          <span className="text-xs mt-1" style={{ color: 'var(--dz-muted)' }}>
            {t('asset.opportunityScore')}
          </span>
        </div>
      </div>
      {showBadge && (
        <div className="mt-3">
          <SignalBadge classification={signal} />
        </div>
      )}
    </div>
  );
}
