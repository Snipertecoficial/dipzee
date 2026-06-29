import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { RefreshCw, SlidersHorizontal } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AssetCard } from '../components/AssetCard';
import api from '../lib/api';

const SIGNALS = ['strong_buy', 'buy', 'hold', 'reduce', 'sell'];

export default function Screener() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';
  const [results, setResults] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [f, setF] = useState({ sector: 'all', classification: 'any', min_dividend: '', max_range_position: '', min_upside: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (f.sector !== 'all') params.sector = f.sector;
      if (f.classification !== 'any') params.classification = f.classification;
      if (f.min_dividend !== '') params.min_dividend = Number(f.min_dividend) / 100;
      if (f.max_range_position !== '') params.max_range_position = Number(f.max_range_position) / 100;
      if (f.min_upside !== '') params.min_upside = Number(f.min_upside) / 100;
      const { data } = await api.get('/screener', { params });
      setResults(data.results || []);
    } catch (e) { /* noop */ } finally { setLoading(false); }
  }, [f]);

  const loadSectors = useCallback(async () => {
    try { const { data } = await api.get('/screener/sectors'); setSectors(data.sectors || []); } catch (e) { /* noop */ }
  }, []);

  useEffect(() => { load(); loadSectors(); }, [load, loadSectors]);

  const refreshUniverse = async () => {
    setRefreshing(true);
    try { await api.post('/screener/refresh'); await load(); await loadSectors(); }
    catch (e) { toast.error(t('auth.genericError')); }
    finally { setRefreshing(false); }
  };

  const reset = () => setF({ sector: 'all', classification: 'any', min_dividend: '', max_range_position: '', min_upside: '' });

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('screener.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('screener.subtitle')}</p>
        </div>
        <Button variant="outline" onClick={refreshUniverse} disabled={refreshing} data-testid="screener-refresh-button">
          <RefreshCw size={16} className={`mr-2 ${refreshing ? 'animate-spin' : ''}`} />{refreshing ? t('screener.refreshing') : t('screener.refresh')}
        </Button>
      </div>

      <Card className="mt-6 p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-3 text-sm font-medium text-[var(--dz-fg)]"><SlidersHorizontal size={16} />{t('screener.filters')}</div>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="space-y-1">
            <Label className="text-xs">{t('screener.sector')}</Label>
            <Select value={f.sector} onValueChange={(v) => setF({ ...f, sector: v })}>
              <SelectTrigger data-testid="screener-sector-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('screener.allSectors')}</SelectItem>
                {sectors.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t('screener.classification')}</Label>
            <Select value={f.classification} onValueChange={(v) => setF({ ...f, classification: v })}>
              <SelectTrigger data-testid="screener-signal-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="any">{t('screener.anySignal')}</SelectItem>
                {SIGNALS.map((s) => <SelectItem key={s} value={s}>{t(`signals.${s}`)}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t('screener.minDividend')}</Label>
            <Input type="number" value={f.min_dividend} onChange={(e) => setF({ ...f, min_dividend: e.target.value })} />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t('screener.maxRange')}</Label>
            <Input type="number" value={f.max_range_position} onChange={(e) => setF({ ...f, max_range_position: e.target.value })} />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t('screener.minUpside')}</Label>
            <Input type="number" value={f.min_upside} onChange={(e) => setF({ ...f, min_upside: e.target.value })} />
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <Button onClick={load} className="bg-[var(--dz-primary)] text-white" data-testid="screener-apply-button">{t('common.search')}</Button>
          <Button variant="ghost" onClick={reset}>{t('screener.reset')}</Button>
        </div>
      </Card>

      {loading ? null : results.length === 0 ? (
        <Card className="mt-6 p-10 text-center text-[var(--dz-muted)]">{t('screener.empty')}</Card>
      ) : (
        <>
          <p className="mt-5 text-sm text-[var(--dz-muted)]">{t('dashboard.count', { count: results.length })}</p>
          <div className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {results.map((a) => <AssetCard key={a.ticker} item={{ ticker: a.ticker, asset: a }} locale={locale} />)}
          </div>
        </>
      )}
    </div>
  );
}
