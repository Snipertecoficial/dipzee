import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { LineChart, Plus, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import { AssetCard } from '../components/AssetCard';
import { SignalBadge } from '../components/SignalBadge';
import { StockSearch } from '../components/StockSearch';
import { SIGNAL_COLORS, formatCurrency } from '../lib/format';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState([]);
  const [discover, setDiscover] = useState([]);
  const [adding, setAdding] = useState('');
  const locale = i18n.language?.slice(0, 2) || 'en';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/watchlist');
      setItems(data || []);
    } catch (e) { /* noop */ } finally { setLoading(false); }
  }, []);

  const loadDiscover = useCallback(async () => {
    try { const { data } = await api.get('/public/top-opportunities', { params: { limit: 12 } }); setDiscover(data.results || []); }
    catch (e) { /* noop */ }
  }, []);

  useEffect(() => { load(); loadDiscover(); }, [load, loadDiscover]);

  const addToWatch = async (ticker) => {
    setAdding(ticker);
    try {
      await api.post('/watchlist', { ticker });
      toast.success(t('asset.addedToast'));
      await load();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(detail?.code === 'watchlist_limit' ? detail.message : (typeof detail === 'string' ? detail : t('auth.genericError')));
    } finally { setAdding(''); }
  };

  const filtered = items.filter((it) => {
    const a = it.asset || {};
    if (filters.includes('buy_zone') && !a?.flags?.buy_zone) return false;
    if (filters.includes('income') && !(a?.dividend_yield >= 0.04)) return false;
    return true;
  });

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('dashboard.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('dashboard.subtitle')}</p>
        </div>
        {items.length > 0 && (
          <ToggleGroup type="multiple" value={filters} onValueChange={setFilters} data-testid="watchlist-filter-chips" className="flex-wrap justify-start">
            <ToggleGroupItem value="buy_zone" data-testid="filter-buy-zone" className="text-xs rounded-full border border-[var(--dz-border)] data-[state=on]:bg-[var(--dz-primary)] data-[state=on]:text-white">{t('dashboard.filterBuyZone')}</ToggleGroupItem>
            <ToggleGroupItem value="income" data-testid="filter-income" className="text-xs rounded-full border border-[var(--dz-border)] data-[state=on]:bg-[var(--dz-primary)] data-[state=on]:text-white">{t('dashboard.filterIncome')}</ToggleGroupItem>
          </ToggleGroup>
        )}
      </div>

      {loading ? (
        <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-44 rounded-[14px]" />)}
        </div>
      ) : items.length === 0 ? (
        <Card className="mt-8 p-10 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-[var(--dz-canvas)] flex items-center justify-center"><LineChart className="text-[var(--dz-muted)]" /></div>
          <h3 className="mt-4 font-heading font-semibold text-lg">{t('dashboard.empty')}</h3>
          <p className="mt-2 text-sm text-[var(--dz-muted)] max-w-sm mx-auto">{t('dashboard.emptyDesc')}</p>
          <div className="mt-5 flex justify-center"><StockSearch /></div>
        </Card>
      ) : filtered.length === 0 ? (
        <Card className="mt-8 p-10 text-center text-[var(--dz-muted)]">{t('dashboard.noMatch')}</Card>
      ) : (
        <>
          <p className="mt-5 text-sm text-[var(--dz-muted)]">{t('dashboard.count', { count: filtered.length })}</p>
          <div className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map((it) => <AssetCard key={it.ticker} item={it} locale={locale} />)}
          </div>
        </>
      )}

      {/* Discover: suggested opportunities to monitor */}
      {(() => {
        const owned = new Set(items.map((it) => it.ticker));
        const suggestions = discover.filter((a) => !owned.has(a.ticker)).slice(0, 6);
        if (suggestions.length === 0) return null;
        return (
          <div className="mt-10" data-testid="dashboard-discover">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-[var(--dz-mint)]" />
              <h2 className="font-heading font-semibold text-xl">{t('dashboard.discoverTitle')}</h2>
            </div>
            <p className="mt-1 text-sm text-[var(--dz-muted)]">{t('dashboard.discoverSubtitle')}</p>
            <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {suggestions.map((a) => (
                <Card key={a.ticker} data-testid="discover-card" className="p-4 flex items-center justify-between gap-3">
                  <Link to={`/app/asset/${a.ticker}`} className="min-w-0 flex items-center gap-3">
                    <div className="h-11 w-11 shrink-0 rounded-full flex items-center justify-center font-heading font-bold tnum" style={{ border: `3px solid ${SIGNAL_COLORS[a.classification] || 'var(--dz-slate)'}` }}>{a.score}</div>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{a.ticker}</p>
                      <p className="text-[11px] text-[var(--dz-muted)] truncate">{formatCurrency(a.price, a.currency, locale)}</p>
                      <div className="mt-1"><SignalBadge classification={a.classification} size="sm" /></div>
                    </div>
                  </Link>
                  <Button size="icon" variant="outline" onClick={() => addToWatch(a.ticker)} disabled={adding === a.ticker} data-testid="discover-add-button" aria-label={t('asset.addToWatchlist')}>
                    {adding === a.ticker ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                  </Button>
                </Card>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
