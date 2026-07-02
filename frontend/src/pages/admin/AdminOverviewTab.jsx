import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Users, LineChart, BellRing, CreditCard, Database, Bell, RefreshCw, Loader2, CheckCircle2, XCircle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SignalBadge } from '../../components/SignalBadge';
import { Metric } from './AdminShared';

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

export function AdminOverviewTab({ stats, config, busy, onRefreshUniverse, onRunDaily }) {
  const { t } = useTranslation();
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
      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading font-semibold">{t('admin.integrations')}</h3>
            {config && <span className="text-xs text-[var(--dz-muted)]">{t('admin.provider')}: {config.provider}</span>}
          </div>
          {config && (<>
            <ConfigRow label="Finnhub" ok={config.finnhub} t={t} />
            <ConfigRow label="FMP" ok={config.fmp} t={t} />
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
