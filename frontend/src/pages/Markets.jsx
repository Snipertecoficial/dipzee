import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, Bitcoin, Newspaper, Search, RefreshCw, ExternalLink, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import api from '../lib/api';

const CRYPTO = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'AVAX-USD'];

const TABS = [
  { key: 'day_gainers', icon: TrendingUp, kind: 'screen' },
  { key: 'day_losers', icon: TrendingDown, kind: 'screen' },
  { key: 'most_actives', icon: Activity, kind: 'screen' },
  { key: 'crypto', icon: Bitcoin, kind: 'crypto' },
  { key: 'news', icon: Newspaper, kind: 'news' },
];

function pctColor(v) {
  if (v == null) return 'var(--dz-muted)';
  return v >= 0 ? 'var(--dz-buy)' : 'var(--dz-sell)';
}
function fmtPct(v) {
  if (v == null) return '\u2014';
  const s = v >= 0 ? '+' : '';
  return `${s}${Number(v).toFixed(2)}%`;
}
function fmtPrice(v, cur = 'USD') {
  if (v == null) return '\u2014';
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: cur, maximumFractionDigits: 2 }).format(v); }
  catch { return `${Number(v).toFixed(2)}`; }
}

function MoverCard({ r, onClick }) {
  const up = r.change_pct == null ? null : r.change_pct >= 0;
  const color = pctColor(r.change_pct);
  const TrendIcon = up === null ? null : up ? ArrowUpRight : ArrowDownRight;
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card
        onClick={onClick}
        data-testid="markets-row"
        className="p-4 sm:p-5 hover:shadow-[var(--dz-elev-2)] transition-shadow cursor-pointer h-full"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="font-heading font-semibold text-[var(--dz-fg)] truncate block">{r.ticker}</span>
            <p className="text-xs text-[var(--dz-muted)] truncate mt-0.5">{r.name || r.ticker}</p>
          </div>
          {TrendIcon && (
            <div className="h-9 w-9 shrink-0 rounded-full flex items-center justify-center" style={{ background: `color-mix(in srgb, ${color} 16%, transparent)`, color }}>
              <TrendIcon size={18} />
            </div>
          )}
        </div>
        <div className="mt-4 flex items-end justify-between">
          <span className="text-lg font-heading font-bold tnum">{fmtPrice(r.price, r.currency)}</span>
          <span className="text-sm font-medium tnum" style={{ color }}>{fmtPct(r.change_pct)}</span>
        </div>
      </Card>
    </motion.div>
  );
}

export default function Markets() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState('day_gainers');
  const [rows, setRows] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null); // null = not searching -> show the tab's rows
  const [searching, setSearching] = useState(false);
  const searchTimer = useRef(null);

  const labelFor = (key) => ({
    day_gainers: t('markets.gainers'), day_losers: t('markets.losers'),
    most_actives: t('markets.active'), crypto: t('markets.crypto'), news: t('markets.news'),
  }[key] || key);

  const load = useCallback(async (key) => {
    setLoading(true);
    try {
      if (key === 'news') {
        const { data } = await api.get('/news/market');
        setNews(data.news || []);
      } else if (key === 'crypto') {
        const results = await Promise.all(CRYPTO.map((s) =>
          api.get(`/market/quote/${s}`).then(({ data }) => data.data).catch(() => null)));
        setRows(results.filter(Boolean).map((d) => ({
          ticker: d.ticker, name: d.name, price: d.price, change_pct: d.change_pct, currency: d.currency,
        })));
      } else {
        const { data } = await api.get('/market/screener', { params: { type: key, count: 30 } });
        setRows((data.data?.quotes || []).filter((q) => q.ticker));
      }
    } catch (e) {
      setRows([]); setNews([]);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(tab); setQuery(''); setSearchResults(null); }, [tab, load]);

  // Typing a query searches every asset (not just the ~30 rows the current
  // tab happens to have loaded) — a name like "microsoft" wouldn't be in
  // "day_gainers" today, so filtering only the loaded rows looked broken.
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    const value = query.trim();
    if (tab === 'news' || !value) { setSearchResults(null); return; }
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await api.get('/assets/search', { params: { q: value } });
        const top = (data.results || []).slice(0, 15);
        const quotes = await Promise.all(top.map((r) =>
          api.get(`/market/quote/${r.ticker}`).then(({ data }) => data.data).catch(() => null)));
        setSearchResults(top.map((r, i) => ({
          ticker: r.ticker,
          name: r.name,
          price: quotes[i]?.price,
          change_pct: quotes[i]?.change_pct,
          currency: quotes[i]?.currency,
        })));
      } catch (e) {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [query, tab]);

  const filtered = searchResults !== null ? searchResults : rows;

  return (
    <div data-testid="markets-page">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('markets.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('markets.subtitle')}</p>
        </div>
        <Button variant="outline" onClick={() => load(tab)} data-testid="markets-refresh-button" className="self-start border-[var(--dz-border)]">
          <RefreshCw size={15} className={`mr-2 ${loading ? 'animate-spin' : ''}`} /> {t('landing.refresh')}
        </Button>
      </div>

      <div className="mt-5 flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList data-testid="markets-tabs" className="flex-wrap h-auto">
            {TABS.map((tb) => (
              <TabsTrigger key={tb.key} value={tb.key} data-testid={`markets-tab-${tb.key}`} className="gap-1.5">
                <tb.icon size={15} /> {labelFor(tb.key)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        {tab !== 'news' && (
          <div className="relative w-full lg:w-64">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--dz-muted)]" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('markets.filterPh')} className="pl-9" data-testid="markets-filter-input" />
          </div>
        )}
      </div>

      <div className="mt-5">
        {tab === 'news' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="markets-news-grid">
            {loading ? [1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-40 rounded-xl" />)
              : news.length === 0 ? <p className="text-[var(--dz-muted)]">{t('news.empty')}</p>
                : news.slice(0, 24).map((n, i) => (
                  <a key={n.id || i} href={n.url} target="_blank" rel="noreferrer" data-testid="markets-news-card"
                    className="group block rounded-xl border border-[var(--dz-border)] bg-[var(--dz-surface)] overflow-hidden hover:shadow-[var(--dz-shadow-card)] transition-shadow">
                    {n.image && <img src={n.image} alt="" className="h-32 w-full object-cover" onError={(e) => { e.target.style.display = 'none'; }} />}
                    <div className="p-4">
                      <p className="text-xs text-[var(--dz-muted)]">{n.source}</p>
                      <p className="mt-1 font-medium text-sm line-clamp-3 group-hover:text-[var(--dz-primary)]">{n.headline}</p>
                      <span className="mt-2 inline-flex items-center gap-1 text-xs text-[var(--dz-primary)]">{t('news.read')} <ExternalLink size={12} /></span>
                    </div>
                  </a>
                ))}
          </div>
        ) : (loading || searching) ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-32 rounded-[14px]" />)}
          </div>
        ) : filtered.length === 0 ? (
          <Card className="p-10 text-center text-[var(--dz-muted)]">{t('dashboard.noMatch')}</Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map((r) => (
              <MoverCard key={r.ticker} r={r} onClick={() => navigate(`/app/asset/${r.ticker}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
