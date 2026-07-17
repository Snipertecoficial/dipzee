import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Loader2, Plus, Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SignalBadge } from './SignalBadge';
import { signalForScore, SIGNAL_COLORS, formatCurrency, formatPercent } from '../lib/format';

// `onAdd` is optional: pass it (plus `adding`/`added`) to show a quick
// "add to watchlist" action on the card, e.g. in the Dashboard's Discover
// grid. Screener/Watchlist usage omits it and gets the plain card.
export function AssetCard({ item, locale = 'en', onAdd, adding = false, added = false }) {
  const { t } = useTranslation();
  const asset = item.asset || {};
  const score = asset.score;
  const signal = asset.classification || signalForScore(score);
  const color = SIGNAL_COLORS[signal];
  const upside = (asset.target_mean && asset.price) ? (asset.target_mean - asset.price) / asset.price : null;

  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="h-full">
      <Card data-testid="watchlist-asset-card" className="relative p-4 sm:p-5 hover:shadow-[var(--dz-elev-2)] transition-shadow h-full">
        <Link to={`/app/asset/${encodeURIComponent(item.ticker)}`} className="block">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-heading font-semibold text-[var(--dz-fg)] truncate">{item.ticker}</span>
                <span className="text-[10px] uppercase rounded px-1.5 py-0.5 bg-[var(--dz-canvas)] text-[var(--dz-muted)] border border-[var(--dz-border)]">{asset.currency || ''}</span>
              </div>
              <p className="text-xs text-[var(--dz-muted)] truncate mt-0.5 pr-8">{asset.name || item.ticker}</p>
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
        </Link>
        {onAdd && (
          <Button
            size="icon"
            variant="outline"
            className="absolute top-4 right-4 h-7 w-7 rounded-full bg-[var(--dz-surface)]"
            disabled={adding || added}
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onAdd(item.ticker); }}
            data-testid="discover-add-button"
            aria-label={t('asset.addToWatchlist')}
          >
            {adding ? <Loader2 size={14} className="animate-spin" /> : added ? <Check size={14} className="text-[var(--dz-buy)]" /> : <Plus size={14} />}
          </Button>
        )}
      </Card>
    </motion.div>
  );
}
