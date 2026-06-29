// Currency + number formatting and signal helpers (currency-aware, i18n-aware)

export const LOCALE_MAP = {
  en: 'en-CA',
  fr: 'fr-CA',
  pt: 'pt-BR',
  es: 'es-ES',
};

export function formatCurrency(value, currency = 'USD', locale = 'en') {
  if (value === null || value === undefined || isNaN(value)) return '\u2014';
  try {
    return new Intl.NumberFormat(LOCALE_MAP[locale] || 'en-CA', {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 2,
    }).format(value);
  } catch (e) {
    return `${currency} ${Number(value).toFixed(2)}`;
  }
}

export function formatNumber(value, locale = 'en', digits = 2) {
  if (value === null || value === undefined || isNaN(value)) return '\u2014';
  return new Intl.NumberFormat(LOCALE_MAP[locale] || 'en-CA', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function formatPercent(value, locale = 'en', digits = 1) {
  if (value === null || value === undefined || isNaN(value)) return '\u2014';
  return new Intl.NumberFormat(LOCALE_MAP[locale] || 'en-CA', {
    style: 'percent',
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

// classification -> signal token name
export function signalForScore(score) {
  if (score === null || score === undefined) return 'unknown';
  if (score >= 85) return 'strong_buy';
  if (score >= 65) return 'buy';
  if (score >= 45) return 'hold';
  if (score >= 30) return 'reduce';
  return 'sell';
}

export const SIGNAL_COLORS = {
  strong_buy: 'var(--dz-buy-deep)',
  buy: 'var(--dz-buy)',
  hold: 'var(--dz-hold)',
  reduce: 'var(--dz-reduce)',
  sell: 'var(--dz-sell)',
  unknown: 'var(--dz-slate)',
};

export const SIGNAL_BADGE_CLASSES = {
  strong_buy: 'bg-[rgba(22,163,74,0.12)] text-[var(--dz-buy-deep)] border border-[rgba(22,163,74,0.25)]',
  buy: 'bg-[rgba(22,163,74,0.10)] text-[var(--dz-buy)] border border-[rgba(22,163,74,0.22)]',
  hold: 'bg-[rgba(245,158,11,0.14)] text-[rgba(146,64,14,1)] border border-[rgba(245,158,11,0.28)]',
  reduce: 'bg-[rgba(249,115,22,0.14)] text-[rgba(154,52,18,1)] border border-[rgba(249,115,22,0.28)]',
  sell: 'bg-[rgba(229,72,77,0.12)] text-[var(--dz-sell)] border border-[rgba(229,72,77,0.26)]',
  unknown: 'bg-[rgba(91,100,120,0.12)] text-[var(--dz-slate)] border border-[rgba(91,100,120,0.22)]',
};
