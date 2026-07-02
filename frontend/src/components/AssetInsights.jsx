import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Loader2, Play } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { FeatureGate } from './FeatureGate';
import api from '../lib/api';

const PERIODS = ['1mo', '3mo', '6mo', '1y', '5y'];

function Spin() { return <div className="flex justify-center py-10"><Loader2 className="animate-spin text-[var(--dz-muted)]" /></div>; }

function ChartTab({ ticker }) {
  const { t } = useTranslation();
  const [period, setPeriod] = useState('6mo');
  const [rows, setRows] = useState(null);
  useEffect(() => {
    let alive = true;
    setRows(null);
    api.get(`/market/history/${ticker}`, { params: { period, interval: '1d' } })
      .then(({ data }) => { if (alive) setRows((data.data || []).map((b) => ({ date: (b.date || '').slice(0, 10), close: b.close }))); })
      .catch(() => alive && setRows([]));
    return () => { alive = false; };
  }, [ticker, period]);
  return (
    <div>
      <div className="flex justify-end mb-3">
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-28" data-testid="asset-chart-period"><SelectValue /></SelectTrigger>
          <SelectContent>{PERIODS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      {rows === null ? <Spin /> : rows.length === 0 ? <p className="text-sm text-[var(--dz-muted)] py-8 text-center">{t('asset.noData')}</p> : (
        <div style={{ width: '100%', height: 320 }} data-testid="asset-history-chart">
          <ResponsiveContainer>
            <AreaChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="clr" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--dz-mint)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--dz-mint)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--dz-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--dz-muted)' }} minTickGap={40} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--dz-muted)' }} domain={['auto', 'auto']} width={52} />
              <Tooltip contentStyle={{ background: 'var(--dz-surface)', border: '1px solid var(--dz-border)', borderRadius: 10, color: 'var(--dz-fg)' }} />
              <Area type="monotone" dataKey="close" stroke="var(--dz-buy-deep)" strokeWidth={2} fill="url(#clr)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function FundamentalsTab({ ticker }) {
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  useEffect(() => {
    let alive = true; setData(null);
    api.get(`/market/fundamentals/${ticker}`).then(({ data }) => alive && setData(data.data)).catch(() => alive && setData({}));
    return () => { alive = false; };
  }, [ticker]);
  if (data === null) return <Spin />;
  const apt = data.analyst_price_targets || {};
  const income = (data.income_stmt || []).slice(0, 6);
  const periods = income.length ? Object.keys(income[0]).filter((k) => k !== 'item').slice(0, 4) : [];
  return (
    <div className="space-y-6">
      {(apt.low || apt.mean || apt.high) && (
        <div>
          <p className="font-heading font-semibold mb-3">{t('asset.analystTargets')}</p>
          <div className="grid grid-cols-3 gap-3">
            {[['tLow', apt.low], ['tMean', apt.mean], ['tHigh', apt.high]].map(([k, v]) => (
              <Card key={k} className="p-3 text-center border-[var(--dz-border)]">
                <p className="text-xs text-[var(--dz-muted)]">{t(`asset.${k}`)}</p>
                <p className="font-heading font-bold text-lg tnum">{v != null ? Number(v).toFixed(2) : '\u2014'}</p>
              </Card>
            ))}
          </div>
        </div>
      )}
      {income.length > 0 ? (
        <div>
          <p className="font-heading font-semibold mb-3">{t('asset.incomeStatement')}</p>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader><TableRow className="hover:bg-transparent"><TableHead>Item</TableHead>{periods.map((p) => <TableHead key={p} className="text-right">{p}</TableHead>)}</TableRow></TableHeader>
              <TableBody>
                {income.map((row) => (
                  <TableRow key={row.item}>
                    <TableCell className="font-medium">{row.item}</TableCell>
                    {periods.map((p) => <TableCell key={p} className="text-right tnum text-sm">{row[p] != null ? Number(row[p]).toLocaleString() : '\u2014'}</TableCell>)}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : (apt.low || apt.mean || apt.high) ? null : <p className="text-sm text-[var(--dz-muted)] py-8 text-center">{t('asset.noData')}</p>}
    </div>
  );
}

function OptionsTab({ ticker }) {
  const { t } = useTranslation();
  const [dates, setDates] = useState(null);
  const [exp, setExp] = useState('');
  const [chain, setChain] = useState(null);
  useEffect(() => {
    let alive = true; setDates(null);
    api.get(`/market/options/${ticker}`).then(({ data }) => {
      if (!alive) return;
      const ds = data.data?.expirations || [];
      setDates(ds); setExp(ds[0] || '');
    }).catch(() => alive && setDates([]));
    return () => { alive = false; };
  }, [ticker]);
  useEffect(() => {
    if (!exp) return;
    let alive = true; setChain(null);
    api.get(`/market/options/${ticker}`, { params: { expiration: exp } }).then(({ data }) => alive && setChain(data.data)).catch(() => alive && setChain({}));
    return () => { alive = false; };
  }, [ticker, exp]);
  if (dates === null) return <Spin />;
  if (dates.length === 0) return <p className="text-sm text-[var(--dz-muted)] py-8 text-center">{t('asset.noData')}</p>;
  const ChainTable = ({ list, label }) => (
    <div>
      <p className="font-heading font-semibold mb-2">{label}</p>
      <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-lg border border-[var(--dz-border)]">
        <Table>
          <TableHeader><TableRow className="hover:bg-transparent"><TableHead>{t('asset.strike')}</TableHead><TableHead className="text-right">{t('asset.last')}</TableHead></TableRow></TableHeader>
          <TableBody>
            {(list || []).slice(0, 40).map((o) => (
              <TableRow key={o.contractSymbol || o.strike}><TableCell className="tnum">{o.strike}</TableCell><TableCell className="text-right tnum">{o.lastPrice}</TableCell></TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
  return (
    <div>
      <div className="flex justify-end mb-3">
        <Select value={exp} onValueChange={setExp}>
          <SelectTrigger className="w-40" data-testid="asset-options-expiration"><SelectValue /></SelectTrigger>
          <SelectContent>{dates.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      {chain === null ? <Spin /> : (
        <div className="grid md:grid-cols-2 gap-4" data-testid="asset-options-chain">
          <ChainTable list={chain.calls} label={t('asset.calls')} />
          <ChainTable list={chain.puts} label={t('asset.puts')} />
        </div>
      )}
    </div>
  );
}

function BacktestTab({ ticker }) {
  const { t } = useTranslation();
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);
  const run = useCallback(() => {
    setLoading(true);
    api.get('/backtest', { params: { ticker, period: '2y', hold_days: 10 } })
      .then(({ data }) => setRes(data)).catch(() => setRes({ ok: false }))
      .finally(() => setLoading(false));
  }, [ticker]);
  return (
    <div>
      {!res && (
        <div className="text-center py-8">
          <Button onClick={run} disabled={loading} data-testid="asset-run-backtest-button" className="bg-[var(--dz-primary)] text-white">
            {loading ? <Loader2 size={16} className="animate-spin mr-2" /> : <Play size={16} className="mr-2" />}{t('asset.runBacktest')}
          </Button>
        </div>
      )}
      {res && res.ok && (
        <div className="space-y-4" data-testid="asset-backtest-result">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[['btTrades', res.num_trades], ['btWin', `${res.win_rate}%`], ['btAvg', `${res.avg_return_pct}%`], ['btStrategy', `${res.strategy_return_pct}%`], ['btBuyHold', `${res.buy_hold_return_pct}%`]].map(([k, v]) => (
              <Card key={k} className="p-3 text-center border-[var(--dz-border)]">
                <p className="text-[11px] text-[var(--dz-muted)]">{t(`asset.${k}`)}</p>
                <p className="font-heading font-bold text-lg tnum">{v}</p>
              </Card>
            ))}
          </div>
          <Button onClick={run} variant="outline" size="sm" disabled={loading} className="border-[var(--dz-border)]">{loading ? <Loader2 size={14} className="animate-spin" /> : t('asset.runBacktest')}</Button>
        </div>
      )}
      {res && !res.ok && <p className="text-sm text-[var(--dz-muted)] py-8 text-center">{t('asset.noData')}</p>}
    </div>
  );
}

export function AssetInsights({ ticker }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState('chart');
  return (
    <Card className="p-6" data-testid="asset-insights">
      <h2 className="font-heading font-semibold mb-4">{t('asset.insights')}</h2>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap h-auto" data-testid="asset-insights-tabs">
          <TabsTrigger value="chart" data-testid="asset-tab-chart">{t('asset.chart')}</TabsTrigger>
          <TabsTrigger value="fundamentals" data-testid="asset-tab-fundamentals">{t('asset.fundamentals')}</TabsTrigger>
          <TabsTrigger value="options" data-testid="asset-tab-options">{t('asset.options')}</TabsTrigger>
          <TabsTrigger value="backtest" data-testid="asset-tab-backtest">{t('asset.backtest')}</TabsTrigger>
        </TabsList>
        <div className="mt-5">
          <TabsContent value="chart"><FeatureGate feature="charts">{tab === 'chart' && <ChartTab ticker={ticker} />}</FeatureGate></TabsContent>
          <TabsContent value="fundamentals"><FeatureGate feature="fundamentals">{tab === 'fundamentals' && <FundamentalsTab ticker={ticker} />}</FeatureGate></TabsContent>
          <TabsContent value="options"><FeatureGate feature="options">{tab === 'options' && <OptionsTab ticker={ticker} />}</FeatureGate></TabsContent>
          <TabsContent value="backtest"><FeatureGate feature="backtest">{tab === 'backtest' && <BacktestTab ticker={ticker} />}</FeatureGate></TabsContent>
        </div>
      </Tabs>
    </Card>
  );
}
