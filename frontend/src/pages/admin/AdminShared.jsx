import React from 'react';
import { Card } from '@/components/ui/card';
import { LOCALE_MAP } from '../../lib/format';

// Shared table cell/header classes used across Admin tabs.
export const TH_CLASS = 'text-left text-[11px] uppercase tracking-wide text-[var(--dz-muted)] font-medium px-3 py-2';
export const TD_CLASS = 'px-3 py-2 text-sm border-t border-[var(--dz-border)] align-middle';

// Locale-aware date formatter shared by Admin tabs.
export function fmtDate(iso, locale) {
  try {
    return new Date(iso).toLocaleDateString(LOCALE_MAP[locale] || 'en-CA', { dateStyle: 'medium' });
  } catch {
    return iso;
  }
}

// Small KPI card used in Overview and Billing tabs.
export function Metric({ label, value, icon: Icon, accent }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-[var(--dz-muted)]">{label}</p>
        <Icon size={16} style={{ color: accent || 'var(--dz-primary)' }} />
      </div>
      <p className="mt-2 font-heading font-bold text-2xl tnum">{value}</p>
    </Card>
  );
}
