import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, Bitcoin, Newspaper, Search, RefreshCw, ExternalLink, ArrowUpRight, ArrowDownRight, Compass, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import api from '../lib/api';

const CRYPTO = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'AVAX-USD'];

const TABS = [
  { key: 'explore', icon: Compass, kind: 'explore' },
  { key: 'day_gainers', icon: TrendingUp, kind: 'screen' },
  { key: 'day_losers', icon: TrendingDown, kind: 'screen' },
  { key: 'most_actives', icon: Activity, kind: 'screen' },
  { key: 'crypto', icon: Bitcoin, kind: 'crypto' },
  { key: 'news', icon: Newspaper, kind: 'news' },
];

// Asset-class chips for the Explore tab. Primary = investable, ordered
// conservative -> aggressive; advanced = structured/derivative, shown only
// when "Advanced" is on. Chips render only for classes present in the facets,
// so the row adapts to what's actually in the catalog (US + London).
const PRIMARY_CLASSES = ['stock', 'etf', 'adr', 'bond', 'index', 'commodity', 'forex', 'crypto'];
const ADVANCED_CLASSES = ['preferred', 'warrant', 'unit', 'right', 'note', 'yield', 'credit', 'future', 'fx_deriv', 'rate', 'volatility'];

const PAGE_SIZE = 25;

function pctColor(v) {
  if (v == null) return 'var(--dz-muted)';
  return v >= 0 ? 'var(--dz-buy)' : 'var(--dz-sell)';
}
function fmtPct(v) {
  if (v == null) return '—';
  const s = v >= 0 ? '+' : '';
  return `${s}${Number(v).toFixed(2)}%`;
}
function fmtPrice(v, cur = 'USD') {
  if (v == null) return '—';
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: cur, maximumFractionDigits: 2 }).format(v); }
  catch { return `${Number(v).toFixed(2)}`; }
}

function MoverCard({ r, onClick, classLabel }) {
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
            {(r.exchange || r.dividend_yield > 0) && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1">
                {r.exchange && (
                  <span className="inline-flex items-center rounded-full bg-[var(--dz-surface-2,rgba(0,0,0,0.04))] px-2 py-0.5 text-[10px] font-medium text-[var(--dz-muted)]">{r.exchange}</span>
                )}
                {classLabel && (
                  <span className="inline-flex items-center rounded-full bg-[var(--dz-surface-2,rgba(0,0,0,0.04))] px-2 py-0.5 text-[10px] font-medium text-[var(--dz-muted)]">{classLabel}</span>
                )}
                {r.dividend_yield > 0 && (
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold tnum" style={{ background: 'color-mix(in srgb, var(--dz-buy) 16%, transparent)', color: 'var(--dz-buy)' }}>
                    {(r.dividend_yield * 100).toFixed(2)}% div
                  </span>
                )}
              </div>
            )}
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

function Chip({ active, onClick, children, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      aria-pressed={active}
      className={`shrink-0 rounded-full px-3 py-1.5 text-sm font-medium border transition-colors ${
        active
          ? 'bg-[var(--dz-primary)] text-white border-[var(--dz-primary)]'
          : 'bg-[var(--dz-surface)] text-[var(--dz-fg)] border-[var(--dz-border)] hover:border-[var(--dz-primary)]'
      }`}
    >
      {children}
    </button>
  );
}

export default function Markets() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState('explore');
  const [rows, setRows] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null); // null = not searching -> show the tab's rows
  const [searching, setSearching] = useState(false);
  const searchTimer = useRef(null);

  // Explore (catalog) state
  const [facets, setFacets] = useState({ exchanges: [], asset_classes: [] });
  const [exExchange, setExExchange] = useState(null);
  const [exClass, setExClass] = useState(null);     // null | 'stock' | 'etf' | 'adr'
  const [exAdvanced, setExAdvanced] = useState(false);
  const [exDividends, setExDividends] = useState(false);
  const [exPage, setExPage] = useState(1);
  const [exRows, setExRows] = useState([]);
  const [exMeta, setExMeta] = useState({ total: 0, pages: 0, page: 1 });
  const [exLoading, setExLoading] = useState(false);

  const clsLabel = (c) => (c ? t(`markets.cls.${c}`, { defaultValue: c }) : '');

  const labelFor = (key) => ({
    explore: t('markets.explore'), day_gainers: t('markets.gainers'), day_losers: t('markets.losers'),
    most_actives: t('markets.active'), crypto: t('markets.crypto'), news: t('markets.news'),
  }[key] || key);

  const load = useCallback(async (key) => {
    if (key === 'explore') return; // Explore has its own loader below.
    setLoading(true);
    try {
      if (key === 'news') {
        const { data } = await api.get('/news/market');
        setNews(data.news || []);
      } else if (key === 'crypto') {
        const { data } = await api.get('/market/quotes', { params: { symbols: CRYPTO.join(',') } });
        setRows((data.data || []).map((d) => ({
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
  // tab happens to have loaded). The Explore tab handles its own query below.
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    const value = query.trim();
    if (tab === 'news' || tab === 'explore' || !value) { setSearchResults(null); return; }
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await api.get('/assets/search', { params: { q: value } });
        const top = (data.results || []).slice(0, 15);
        const { data: qd } = await api.get('/market/quotes', { params: { symbols: top.map((r) => r.ticker).join(',') } });
        const byTicker = Object.fromEntries((qd.data || []).map((q) => [q.ticker, q]));
        setSearchResults(top.map((r) => ({
          ticker: r.ticker,
          name: r.name,
          price: byTicker[r.ticker]?.price,
          change_pct: byTicker[r.ticker]?.change_pct,
          currency: byTicker[r.ticker]?.currency,
          dividend_yield: byTicker[r.ticker]?.dividend_yield,
        })));
      } catch (e) {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [query, tab]);

  // --- Explore: facets (exchange/class chips) ---
  useEffect(() => {
    if (tab !== 'explore') return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get('/catalog/facets', { params: exAdvanced ? { advanced: true } : {} });
        if (!cancelled) setFacets({ exchanges: data.exchanges || [], asset_classes: data.asset_classes || [] });
      } catch {
        if (!cancelled) setFacets({ exchanges: [], asset_classes: [] });
      }
    })();
    return () => { cancelled = true; };
  }, [tab, exAdvanced]);

  // --- Explore: reset to page 1 whenever a filter or the query changes ---
  useEffect(() => { if (tab === 'explore') setExPage(1); }, [query, exExchange, exClass, exAdvanced, exDividends, tab]);

  // --- Explore: load the catalog page + batch-quote the visible rows ---
  const loadExplore = useCallback(async () => {
    setExLoading(true);
    try {
      const params = { page: exPage };
      const q = query.trim();
      if (q) params.q = q;
      if (exExchange) params.exchange = exExchange;
      if (exClass) params.asset_class = exClass;
      if (exAdvanced) params.advanced = true;
      if (exDividends) params.min_dividend = 0.0001; // only verified payers
      const { data } = await api.get('/catalog', { params });
      const metaRows = data.results || [];
      setExMeta({ total: data.total || 0, pages: data.pages || 0, page: data.page || 1 });

      // Prices are fetched on demand for the visible page only — the directory
      // itself is metadata, so this scales to the whole universe.
      let quotes = {};
      if (metaRows.length) {
        try {
          const { data: qd } = await api.get('/market/quotes', { params: { symbols: metaRows.map((r) => r.symbol).join(',') } });
          quotes = Object.fromEntries((qd.data || []).map((qt) => [qt.ticker, qt]));
        } catch { /* best-effort: rows still render with metadata */ }
      }
      setExRows(metaRows.map((r) => ({
        ticker: r.symbol, name: r.name, exchange: r.exchange, asset_class: r.asset_class,
        price: quotes[r.symbol]?.price, change_pct: quotes[r.symbol]?.change_pct, currency: quotes[r.symbol]?.currency,
        // Prefer the live quote's yield; fall back to the catalog's verified value.
        dividend_yield: quotes[r.symbol]?.dividend_yield ?? r.dividend_yield,
      })));
    } catch {
      setExRows([]); setExMeta({ total: 0, pages: 0, page: 1 });
    } finally {
      setExLoading(false);
    }
  }, [exPage, query, exExchange, exClass, exAdvanced, exDividends]);

  useEffect(() => {
    if (tab !== 'explore') return undefined;
    const timer = setTimeout(loadExplore, 300);
    return () => clearTimeout(timer);
  }, [tab, loadExplore]);

  const pickClass = (assetClass, advanced) => { setExClass(assetClass); setExAdvanced(advanced); };
  const classActive = (assetClass, advanced) => exClass === assetClass && exAdvanced === advanced;
  const presentClasses = new Set((facets.asset_classes || []).map((c) => c.name));

  const filtered = searchResults !== null ? searchResults : rows;
  const isExplore = tab === 'explore';

  return (
    <div data-testid="markets-page">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('markets.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('markets.subtitle')}</p>
        </div>
        <Button variant="outline" onClick={() => (isExplore ? loadExplore() : load(tab))} data-testid="markets-refresh-button" className="self-start border-[var(--dz-border)]">
          <RefreshCw size={15} className={`mr-2 ${(loading || exLoading) ? 'animate-spin' : ''}`} /> {t('landing.refresh')}
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

      {/* Explore filter bar: exchange chips + asset-class chips */}
      {isExplore && (
        <div className="mt-4 space-y-3">
          <div className="flex gap-2 overflow-x-auto pb-1" data-testid="explore-exchange-chips">
            <Chip active={!exExchange} onClick={() => setExExchange(null)} testid="explore-exchange-all">{t('markets.allExchanges')}</Chip>
            {facets.exchanges.map((e) => (
              <Chip key={e.name} active={exExchange === e.name} onClick={() => setExExchange(e.name)} testid={`explore-exchange-${e.name}`}>
                {e.name} <span className="opacity-60">{e.count}</span>
              </Chip>
            ))}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1" data-testid="explore-class-chips">
            <Chip active={classActive(null, false)} onClick={() => pickClass(null, false)} testid="explore-class-essential">{t('markets.essential')}</Chip>
            {PRIMARY_CLASSES.filter((c) => presentClasses.has(c)).map((c) => (
              <Chip key={c} active={classActive(c, false)} onClick={() => pickClass(c, false)} testid={`explore-class-${c}`}>
                {t(`markets.cls.${c}`, { defaultValue: c })}
              </Chip>
            ))}
            <Chip active={classActive(null, true)} onClick={() => pickClass(null, true)} testid="explore-class-advanced">{t('markets.advanced')}</Chip>
          </div>
          {exAdvanced && (
            <div className="flex gap-2 overflow-x-auto pb-1" data-testid="explore-class-chips-adv">
              {ADVANCED_CLASSES.filter((c) => presentClasses.has(c)).map((c) => (
                <Chip key={c} active={classActive(c, true)} onClick={() => pickClass(c, true)} testid={`explore-class-${c}`}>
                  {t(`markets.cls.${c}`, { defaultValue: c })}
                </Chip>
              ))}
            </div>
          )}
          <div className="flex gap-2 overflow-x-auto pb-1" data-testid="explore-dividend-filter">
            <Chip active={exDividends} onClick={() => setExDividends((v) => !v)} testid="explore-dividends-toggle">
              💰 {t('markets.dividendsOnly')}
            </Chip>
          </div>
        </div>
      )}

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
        ) : isExplore ? (
          exLoading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => <Skeleton key={i} className="h-36 rounded-[14px]" />)}
            </div>
          ) : exRows.length === 0 ? (
            <Card className="p-10 text-center text-[var(--dz-muted)]">{t('dashboard.noMatch')}</Card>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3 text-sm text-[var(--dz-muted)]">
                <span data-testid="explore-count">{t('markets.assetsCount', { count: exMeta.total })}</span>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {exRows.map((r) => (
                  <MoverCard key={`${r.exchange}:${r.ticker}`} r={r} classLabel={clsLabel(r.asset_class)} onClick={() => navigate(`/app/asset/${encodeURIComponent(r.ticker)}`)} />
                ))}
              </div>
              {exMeta.pages > 1 && (
                <div className="mt-6 flex items-center justify-center gap-3" data-testid="explore-pagination">
                  <Button variant="outline" className="border-[var(--dz-border)]" disabled={exPage <= 1}
                    onClick={() => setExPage((p) => Math.max(1, p - 1))} data-testid="explore-prev">
                    <ChevronLeft size={16} className="mr-1" /> {t('markets.prev')}
                  </Button>
                  <span className="text-sm text-[var(--dz-muted)] tnum">{t('markets.pageOf', { page: exMeta.page, pages: exMeta.pages })}</span>
                  <Button variant="outline" className="border-[var(--dz-border)]" disabled={exPage >= exMeta.pages}
                    onClick={() => setExPage((p) => Math.min(exMeta.pages, p + 1))} data-testid="explore-next">
                    {t('markets.next')} <ChevronRight size={16} className="ml-1" />
                  </Button>
                </div>
              )}
            </>
          )
        ) : (loading || searching) ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-32 rounded-[14px]" />)}
          </div>
        ) : filtered.length === 0 ? (
          <Card className="p-10 text-center text-[var(--dz-muted)]">{t('dashboard.noMatch')}</Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map((r) => (
              <MoverCard key={r.ticker} r={r} onClick={() => navigate(`/app/asset/${encodeURIComponent(r.ticker)}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
