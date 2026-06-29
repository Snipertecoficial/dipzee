import React from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, TrendingDown, Pause, MinusCircle, HelpCircle } from 'lucide-react';
import { SIGNAL_BADGE_CLASSES } from '../lib/format';

const ICONS = {
  strong_buy: TrendingUp,
  buy: TrendingUp,
  hold: Pause,
  reduce: TrendingDown,
  sell: TrendingDown,
  unknown: HelpCircle,
};

export function SignalBadge({ classification, size = 'md' }) {
  const { t } = useTranslation();
  const cls = classification || 'unknown';
  const Icon = ICONS[cls] || MinusCircle;
  const padding = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${padding} ${SIGNAL_BADGE_CLASSES[cls]}`}
      data-testid="opportunity-score-badge"
      aria-label={t(`signals.${cls}`)}
    >
      <Icon size={size === 'sm' ? 12 : 14} />
      {t(`signals.${cls}`)}
    </span>
  );
}
