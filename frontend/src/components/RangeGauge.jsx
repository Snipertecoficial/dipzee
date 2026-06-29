import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Flag } from 'lucide-react';
import { formatCurrency } from '../lib/format';

// 52-week range gauge with low/high/current markers + analyst target flag.
// Stacks gracefully below 380px so the current marker and target flag don't overlap.
export function RangeGauge52w({ low, high, current, target, currency = 'USD', locale = 'en' }) {
  const { t } = useTranslation();
  const ref = useRef(null);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setNarrow(e.contentRect.width < 380);
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  if (low == null || high == null || high === low) {
    return null;
  }
  const clampPct = (v) => Math.max(2, Math.min(98, ((v - low) / (high - low)) * 100));
  const curPct = current != null ? clampPct(current) : null;
  const tgtPct = target != null && target > 0 ? clampPct(target) : null;
  const overlap = curPct != null && tgtPct != null && Math.abs(curPct - tgtPct) < 8;
  const stackTarget = narrow && overlap;

  return (
    <div ref={ref} data-testid="range-gauge-52w" className="w-full">
      {/* Target flag row (above track on desktop, or stacked when narrow+overlap) */}
      {tgtPct != null && !stackTarget && (
        <div className="relative h-7">
          <div
            className="absolute -translate-x-1/2 flex flex-col items-center"
            style={{ left: `${tgtPct}%` }}
            data-testid="range-gauge-target-marker"
          >
            <span className="inline-flex items-center gap-1 rounded-full border border-[var(--dz-mint)] bg-[rgba(22,224,163,0.10)] px-2 py-0.5 text-[11px] text-[var(--dz-primary)] tnum whitespace-nowrap">
              <Flag size={11} /> {formatCurrency(target, currency, locale)}
            </span>
            <span className="h-2 w-px bg-[var(--dz-mint)]" />
          </div>
        </div>
      )}

      {/* Track */}
      <div className="relative h-2 rounded-full bg-[var(--dz-line)]">
        {curPct != null && (
          <div
            className="absolute top-1/2 h-2 rounded-full"
            style={{ left: '0%', width: `${curPct}%`, background: 'rgba(26,31,77,0.12)', transform: 'translateY(-50%)' }}
          />
        )}
        {curPct != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full border-2 border-[var(--dz-primary)] bg-white shadow"
            style={{ left: `${curPct}%` }}
            data-testid="range-gauge-current-marker"
          />
        )}
      </div>

      {/* Low / High labels */}
      <div className="mt-1.5 flex justify-between text-[11px] text-[var(--dz-muted)] tnum">
        <span data-testid="range-gauge-low-label">{t('asset.low')} {formatCurrency(low, currency, locale)}</span>
        <span className="font-medium text-[var(--dz-fg)]">{t('asset.now')} {formatCurrency(current, currency, locale)}</span>
        <span data-testid="range-gauge-high-label">{t('asset.high')} {formatCurrency(high, currency, locale)}</span>
      </div>

      {/* Stacked target chip (narrow + overlap) */}
      {stackTarget && tgtPct != null && (
        <div className="mt-2" data-testid="range-gauge-target-marker">
          <span className="inline-flex items-center gap-1 rounded-full border border-[var(--dz-mint)] bg-[rgba(22,224,163,0.10)] px-2 py-0.5 text-[11px] text-[var(--dz-primary)] tnum">
            <Flag size={11} /> {t('asset.target')}: {formatCurrency(target, currency, locale)}
          </span>
        </div>
      )}

      {/* Accessible summary */}
      <span className="sr-only">
        {t('asset.rangeSummary', {
          low: formatCurrency(low, currency, locale),
          high: formatCurrency(high, currency, locale),
          current: formatCurrency(current, currency, locale),
          target: formatCurrency(target, currency, locale),
        })}
      </span>
    </div>
  );
}
