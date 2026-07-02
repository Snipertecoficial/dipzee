import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Users, LineChart, BellRing, CreditCard, Database, Bell, RefreshCw, Loader2, CheckCircle2, XCircle, BarChart3, PieChart as PieIcon,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SignalBadge } from '../../components/SignalBadge';
import { Metric } from './AdminShared';
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, PieChart, Pie, Cell,
} from 'recharts';

function ConfigRow({ label, ok, t }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[var(--dz-border)] last:border-0">
      <span className="text-sm">{label}</span>
      <span className={`inline-flex items-center gap-1 text-xs ${ok ? 'text-[var(--dz-buy)]' : 'text-[var(--dz-muted)]'}`}>
        {ok ? <CheckCircle2 size={14} /> : <XCircle size={14} />}{ok ? t('admin.configured') : t('admin.notConfigured')}
      </span>
    </div>
  );
}

export function AdminOverviewTab({ stats, config, chartData, busy, onRefreshUniverse, onRunDaily }) {
  const { t } = useTranslation();

  const planData = stats?.plan_counts ? [
    { name: 'Nenhum / Trial', value: stats.plan_counts.none || 0, color: '#94a3b8' },
    { name: 'Starter', value: stats.plan_counts.starter || 0, color: '#818cf8' },
    { name: 'Pro', value: stats.plan_counts.pro || 0, color: '#16e0a3' },
    { name: 'Investor', value: stats.plan_counts.investor || 0, color: '#1e1b4b' },
  ].filter(p => p.value > 0) : [];

  return (
    <>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Metric label={t('admin.metrics.users')} value={stats.users_total} icon={Users} />
          <Metric label={t('admin.metrics.assets')} value={stats.assets_total} icon={Database} />
          <Metric label={t('admin.metrics.activeAlerts')} value={stats.active_alerts} icon={BellRing} accent="var(--dz-hold)" />
          <Metric label={t('admin.metrics.events')} value={stats.events_total} icon={Bell} />
          <Metric label={t('admin.metrics.watchlist')} value={stats.watchlist_total} icon={LineChart} />
          <Metric label={t('admin.planStarter')} value={stats.plan_counts?.starter ?? 0} icon={Users} />
          <Metric label={t('admin.planPro')} value={stats.plan_counts?.pro ?? 0} icon={Users} accent="var(--dz-mint)" />
          <Metric label={t('admin.metrics.revenue')} value={`US$${(stats.revenue || 0).toFixed(2)}`} icon={CreditCard} accent="var(--dz-buy)" />
        </div>
      )}

      {/* Graphical Analytics section */}
      <div className="grid lg:grid-cols-3 gap-6 mt-6">
        {/* Signups and Revenue growth */}
        <Card className="p-5 lg:col-span-2">
          <h3 className="font-heading font-semibold mb-4 flex items-center gap-1.5">
            <BarChart3 size={18} className="text-[var(--dz-primary)]" />
            Performance e Crescimento (Últimos 15 dias)
          </h3>
          <div className="h-72 w-full text-xs">
            {chartData && chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#16e0a3" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#16e0a3" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorSignups" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#818cf8" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--dz-border)" />
                  <XAxis dataKey="date" stroke="var(--dz-muted)" />
                  <YAxis yAxisId="left" stroke="var(--dz-muted)" />
                  <YAxis yAxisId="right" orientation="right" stroke="var(--dz-muted)" />
                  <RechartsTooltip contentStyle={{ backgroundColor: 'var(--dz-surface)', borderColor: 'var(--dz-border)', borderRadius: '8px' }} />
                  <Legend />
                  <Area yAxisId="left" type="monotone" dataKey="cumulative" name="Receita Acumulada (US$)" stroke="#16e0a3" fillOpacity={1} fill="url(#colorRev)" strokeWidth={2} />
                  <Area yAxisId="right" type="monotone" dataKey="signups" name="Cadastros" stroke="#818cf8" fillOpacity={1} fill="url(#colorSignups)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-[var(--dz-muted)]">Carregando dados do gráfico...</div>
            )}
          </div>
        </Card>

        {/* User distribution by plan */}
        <Card className="p-5 lg:col-span-1 flex flex-col justify-between">
          <div>
            <h3 className="font-heading font-semibold mb-4 flex items-center gap-1.5">
              <PieIcon size={18} className="text-[var(--dz-primary)]" />
              Distribuição de Planos
            </h3>
            <div className="h-56 w-full flex items-center justify-center">
              {planData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={planData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {planData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-[var(--dz-muted)] text-sm">Carregando dados dos planos...</div>
              )}
            </div>
          </div>
          <div className="space-y-1.5 mt-2">
            {planData.map((entry) => (
              <div key={entry.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
                  <span className="text-[var(--dz-muted)] font-medium">{entry.name}</span>
                </div>
                <span className="font-bold text-[var(--dz-fg)] tnum">{entry.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading font-semibold">{t('admin.integrations')}</h3>
            {config && <span className="text-xs text-[var(--dz-muted)]">{t('admin.provider')}: {config.provider}</span>}
          </div>
          {config && (<>
            <ConfigRow label="Finnhub" ok={config.finnhub} t={t} />
            <ConfigRow label="FMP" ok={config.fmp} t={t} />
            <ConfigRow label="Polygon" ok={config.polygon} t={t} />
            <ConfigRow label="Alpha Vantage" ok={config.alphavantage} t={t} />
            <ConfigRow label="Twelve Data" ok={config.twelvedata} t={t} />
            <ConfigRow label="Marketstack" ok={config.marketstack} t={t} />
            <ConfigRow label="Investing.com" ok={config.provider === 'investing'} t={t} />
            <ConfigRow label="Stripe" ok={config.stripe} t={t} />
            <ConfigRow label="Resend" ok={config.resend} t={t} />
          </>)}
          <div className="mt-4 flex gap-2">
            <Button size="sm" variant="outline" onClick={onRefreshUniverse} disabled={busy === 'universe'} data-testid="admin-refresh-universe">
              {busy === 'universe' ? <Loader2 size={14} className="animate-spin mr-1" /> : <RefreshCw size={14} className="mr-1" />}{t('admin.refreshUniverse')}
            </Button>
            <Button size="sm" variant="outline" onClick={onRunDaily} disabled={busy === 'daily'} data-testid="admin-run-daily">
              {busy === 'daily' ? <Loader2 size={14} className="animate-spin mr-1" /> : <RefreshCw size={14} className="mr-1" />}{t('admin.runDaily')}
            </Button>
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="font-heading font-semibold mb-3">{t('admin.topAssets')}</h3>
          <div className="space-y-2">
            {(stats?.top_assets || []).map((a) => (
              <Link to={`/app/asset/${a.ticker}`} key={a.ticker} className="flex items-center justify-between hover:bg-[rgba(15,20,36,0.03)] rounded px-2 py-1">
                <span className="text-sm font-medium">{a.ticker}</span>
                <div className="flex items-center gap-2"><SignalBadge classification={a.classification} size="sm" /><span className="tnum text-sm">{a.score}</span></div>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
