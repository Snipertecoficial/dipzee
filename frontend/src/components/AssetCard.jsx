import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Card } from '@/components/ui/card';
import { SignalBadge } from './SignalBadge';
import { signalForScore, SIGNAL_COLORS, formatCurrency, formatPercent } from '../lib/format';

export function AssetCard({ item, locale = 'en' }) {
  const { t } = useTranslation();
  const asset = item.asset || {};
  const score = asset.score;
  const signal = asset.classification || signalForScore(score);
  const color = SIGNAL_COLORS[signal];
  const upside = (asset.target_mean && asset.price) ? (asset.target_mean - asset.price) / asset.price : null;

  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Link to={`/app/asset/${encodeURIComponent(item.ticker)}`}>
        <Card data-testid="watchlist-asset-card" className="p-4 sm:p-5 hover:shadow-[var(--dz-elev-2)] transition-shadow cursor-pointer h-full">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-heading font-semibold text-[var(--dz-fg)] truncate">{item.ticker}</span>
                <span className="text-[10px] uppercase rounded px-1.5 py-0.5 bg-[var(--dz-canvas)] text-[var(--dz-muted)] border border-[var(--dz-border)]">{asset.currency || ''}</span>
              </div>
              <p className="text-xs text-[var(--dz-muted)] truncate mt-0.5">{asset.name || item.ticker}</p>
            </div>
            <div className="flex flex-col items-center shrink-0">
              <div className="h-12 w-12 rounded-full flex items-center justify-center font-heading font-bold tnum" style={{ border: `3px solid ${color}`, color: 'var(--dz-fg)' }}>
                {score ?? '\u2014'}
              </div>
            </div>
          </div>
          <div className="mt-3"><SignalBadge classification={signal} size="sm" /></div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-[10px] text-[var(--dz-muted)]">{t('asset.price')}</p>
              <p className="text-sm font-medium tnum">{formatCurrency(asset.price, asset.currency, locale)}</p>
            </div>
            <div>
              <p className="text-[10px] text-[var(--dz-muted)]">{t('asset.dividendYield')}</p>
              <p className="text-sm font-medium tnum">{formatPercent(asset.dividend_yield, locale, 1)}</p>
            </div>
            <div>
              <p className="text-[10px] text-[var(--dz-muted)]">{t('asset.subUpside')}</p>
              <p className="text-sm font-medium tnum" style={{ color: upside > 0 ? 'var(--dz-buy)' : 'var(--dz-muted)' }}>{upside != null ? formatPercent(upside, locale, 0) : '\u2014'}</p>
            </div>
          </div>
        </Card>
      </Link>
    </motion.div>
  );
}
