import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Star, BellPlus, RefreshCw, Loader2, Newspaper, ExternalLink, Landmark } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScoreDial } from '../components/ScoreDial';
import { RangeGauge52w } from '../components/RangeGauge';
import { CreateAlertDialog } from '../components/CreateAlertDialog';
import { AssetInsights } from '../components/AssetInsights';
import { formatCurrency, formatPercent } from '../lib/format';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

export default function AssetDetail() {
  const { ticker } = useParams();
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [asset, setAsset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [inWatch, setInWatch] = useState(false);
  const [error, setError] = useState(false);
  const [news, setNews] = useState([]);
  const [ads, setAds] = useState([]);
  const locale = i18n.language?.slice(0, 2) || 'en';
  const cur = asset?.currency || user?.currency || 'USD';

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError(false);
    try {
      const { data } = await api.post(`/assets/refresh/${encodeURIComponent(ticker)}`);
      setAsset(data);
    } catch (e) {
      setError(true);
    } finally { setLoading(false); setRefreshing(false); }
  }, [ticker]);

  const loadWatch = useCallback(async () => {
    try {
      const { data } = await api.get('/watchlist');
      setInWatch((data || []).some((it) => it.ticker === ticker.toUpperCase()));
    } catch (e) { /* noop */ }
  }, [ticker]);

  const loadNews = useCallback(async () => {
    try {
      const { data } = await api.get(`/assets/${encodeURIComponent(ticker)}/news`);
      setNews(data.news || []);
    } catch (e) { /* noop */ }
  }, [ticker]);

  const loadAds = useCallback(async () => {
    try {
      const { data } = await api.get('/partner-ads/active');
      setAds(data.ads || []);
    } catch (e) { /* noop */ }
  }, []);

  const handleAdClick = async (ad) => {
    try {
      await api.post(`/partner-ads/click/${ad.id}`);
    } catch (e) { /* noop */ }
    window.open(ad.target_url, '_blank', 'noopener,noreferrer');
  };

  useEffect(() => { load(); loadWatch(); loadNews(); loadAds(); }, [load, loadWatch, loadNews, loadAds]);

  // Real-time: poll the quote every 20s while the page is open.
  useEffect(() => {
    const id = setInterval(() => load(true), 20000);
    return () => clearInterval(id);
  }, [load]);

  const toggleWatch = async () => {
    try {
      if (inWatch) {
        await api.delete(`/watchlist/${encodeURIComponent(ticker)}`);
        setInWatch(false);
        toast.success(t('asset.removedToast'));
      } else {
        await api.post('/watchlist', { ticker: ticker.toUpperCase() });
        setInWatch(true);
        toast.success(t('asset.addedToast'));
      }
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (detail?.code === 'watchlist_limit') toast.error(detail.message);
      else toast.error(t('auth.genericError'));
    }
  };

  if (loading) {
    return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-[var(--dz-muted)]" /></div>;
  }
  if (error || !asset) {
    return <Card className="p-10 text-center text-[var(--dz-muted)]">{t('asset.notFound')}</Card>;
  }

  const upside = (asset.target_mean && asset.price) ? (asset.target_mean - asset.price) / asset.price : null;
  const sub = asset.sub_scores || {};
  const stats = [
    { label: t('asset.price'), value: formatCurrency(asset.price, cur, locale) },
    { label: t('asset.low52'), value: formatCurrency(asset.low_52w, cur, locale) },
    { label: t('asset.high52'), value: formatCurrency(asset.high_52w, cur, locale) },
    { label: t('asset.target'), value: formatCurrency(asset.target_mean, cur, locale) },
    { label: t('asset.dividendYield'), value: formatPercent(asset.dividend_yield, locale, 2) },
    { label: t('asset.sector'), value: asset.sector || '\u2014' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            {asset.logo && <img src={asset.logo} alt="" className="h-8 w-8 rounded-md object-contain bg-white border border-[var(--dz-border)]" onError={(e) => { e.target.style.display = 'none'; }} />}
            <h1 className="font-heading font-bold text-2xl sm:text-3xl">{asset.ticker}</h1>
            <span className="text-xs uppercase rounded px-1.5 py-0.5 bg-white text-[var(--dz-muted)] border border-[var(--dz-border)]">{asset.exchange}</span>
            {asset.source === 'finnhub' && (
              <span className="inline-flex items-center gap-1 text-[10px] rounded-full px-2 py-0.5 bg-[rgba(22,224,163,0.15)] text-[var(--dz-buy-deep)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--dz-buy)] animate-pulse" />{t('asset.live')}
              </span>
            )}
          </div>
          <p className="text-[var(--dz-muted)]">{asset.name}</p>
          <div className="mt-1 flex items-center gap-2">
            <span className="font-heading font-semibold tnum">{formatCurrency(asset.price, cur, locale)}</span>
            {asset.change_pct != null && (
              <span className="text-sm tnum" style={{ color: asset.change_pct >= 0 ? 'var(--dz-buy)' : 'var(--dz-sell)' }}>
                {asset.change_pct >= 0 ? '+' : ''}{asset.change_pct.toFixed(2)}% · {t('asset.change')}
              </span>
            )}
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={() => load(true)} disabled={refreshing} aria-label={t('asset.refresh')}>
          <RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />
        </Button>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Dial + actions */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="p-6 flex flex-col items-center">
            <ScoreDial score={asset.score} classification={asset.classification} size="hero" />
            <div className="mt-6 w-full flex flex-col gap-2">
              <Button onClick={toggleWatch} data-testid="asset-add-to-watchlist-button" className={inWatch ? 'bg-white border border-[var(--dz-border)] text-[var(--dz-primary)]' : 'bg-[var(--dz-primary)] text-white'}>
                <Star size={16} className="mr-2" fill={inWatch ? 'currentColor' : 'none'} />
                {inWatch ? t('asset.removeFromWatchlist') : t('asset.addToWatchlist')}
              </Button>
              <CreateAlertDialog defaultTicker={asset.ticker} currency={cur} onCreated={() => {}}
                trigger={<Button data-testid="asset-create-alert-button" variant="outline"><BellPlus size={16} className="mr-2" />{t('asset.createAlert')}</Button>} />
            </div>
          </Card>

          {/* Contextual partner ad */}
          {ads.filter((a) => a.placement === 'asset_detail').slice(0, 1).map((ad) => (
            <Card key={ad.id} onClick={() => handleAdClick(ad)} className="p-4 border border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10 cursor-pointer select-none transition-all flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-[var(--dz-canvas)] border border-[var(--dz-border)] flex items-center justify-center shrink-0">
                {ad.image_url ? (
                  <img src={ad.image_url} alt="" className="w-5 h-5 object-contain" />
                ) : (
                  <Landmark size={14} className="text-amber-500" />
                )}
              </div>
              <div className="min-w-0">
                <span className="text-[9px] font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1">
                  Patrocinado <ExternalLink size={8} />
                </span>
                <h4 className="font-heading font-semibold text-xs text-[var(--dz-fg)] mt-0.5">{ad.partner_name}</h4>
                <p className="text-[11px] text-[var(--dz-muted)] mt-0.5 leading-tight">{ad.description.replace('{ticker}', asset.ticker)}</p>
              </div>
            </Card>
          ))}
        </div>

        {/* Gauge + explanation */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6">
            <h2 className="font-heading font-semibold mb-4">{t('asset.rangeTitle')}</h2>
            <RangeGauge52w low={asset.low_52w} high={asset.high_52w} current={asset.price} target={asset.target_mean} currency={cur} locale={locale} />
          </Card>
          {asset.explanation && (
            <Card className="p-6">
              <h2 className="font-heading font-semibold mb-2">{t('asset.explanation')}</h2>
              <p className="text-[var(--dz-fg)] leading-relaxed">{asset.explanation}</p>
            </Card>
          )}
        </div>
      </div>

      {/* Key stats */}
      <Card className="p-6">
        <h2 className="font-heading font-semibold mb-4">{t('asset.keyStats')}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {stats.map((s) => (
            <div key={s.label}>
              <p className="text-[11px] text-[var(--dz-muted)]">{s.label}</p>
              <p className="font-medium tnum mt-0.5">{s.value}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Breakdown */}
      {asset.sub_scores && (
        <Card className="p-6">
          <h2 className="font-heading font-semibold mb-4">{t('asset.breakdown')}</h2>
          <div className="space-y-4">
            {[['subBuy', sub.buy], ['subUpside', sub.upside], ['subIncome', sub.income]].map(([k, v]) => (
              <div key={k}>
                <div className="flex justify-between text-sm mb-1"><span className="text-[var(--dz-muted)]">{t(`asset.${k}`)}</span><span className="font-medium tnum">{Math.round(v)}</span></div>
                <Progress value={v} className="h-2" />
              </div>
            ))}
          </div>
        </Card>
      )}
      {/* Insights: chart, fundamentals, options, backtest (plan-gated) */}
      <AssetInsights ticker={asset.ticker} />

      {/* News */}
      <Card className="p-6" data-testid="asset-news-section">
        <h2 className="font-heading font-semibold mb-4 flex items-center gap-2"><Newspaper size={18} />{t('asset.news')}</h2>
        {news.length === 0 ? (
          <p className="text-sm text-[var(--dz-muted)]">{t('asset.noNews')}</p>
        ) : (
          <div className="space-y-3">
            {news.slice(0, 8).map((n, i) => (
              <a key={n.id || i} href={n.url} target="_blank" rel="noopener noreferrer" data-testid="asset-news-item"
                className="flex items-start gap-3 rounded-lg p-2 -mx-2 hover:bg-[rgba(15,20,36,0.03)] transition-colors">
                {n.image ? <img src={n.image} alt="" className="h-14 w-20 rounded-md object-cover shrink-0" onError={(e) => { e.target.style.display = 'none'; }} /> : null}
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--dz-fg)] leading-snug">{n.headline}</p>
                  <p className="text-xs text-[var(--dz-muted)] mt-1 flex items-center gap-1">{n.source} <ExternalLink size={11} /></p>
                </div>
              </a>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
