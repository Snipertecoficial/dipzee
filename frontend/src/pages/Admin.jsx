import React, { useEffect, useState, useCallback } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import {
  Users, LineChart, BellRing, CreditCard, SlidersHorizontal, Trash2, RefreshCw,
  Shield, Database, Bell, Search, Loader2, CheckCircle2, XCircle, ExternalLink,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SignalBadge } from '../components/SignalBadge';
import { formatCurrency, LOCALE_MAP } from '../lib/format';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

function Metric({ label, value, icon: Icon, accent }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-[var(--dz-muted)]">{label}</p>
        <Icon size={16} style={{ color: accent || 'var(--dz-primary)' }} />
      </div>
      <p className="mt-2 font-heading font-bold text-2xl tnum">{value}</p>
    </Card>
  );
}

export default function Admin() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const locale = i18n.language?.slice(0, 2) || 'en';

  const [stats, setStats] = useState(null);
  const [config, setConfig] = useState(null);
  const [users, setUsers] = useState([]);
  const [userQ, setUserQ] = useState('');
  const [assets, setAssets] = useState([]);
  const [assetQ, setAssetQ] = useState('');
  const [refreshTicker, setRefreshTicker] = useState('');
  const [alerts, setAlerts] = useState([]);
  const [events, setEvents] = useState([]);
  const [txs, setTxs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [busy, setBusy] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([api.get('/admin/stats'), api.get('/admin/config')]);
      setStats(s.data); setConfig(c.data);
    } catch (e) { /* noop */ }
  }, []);
  const loadUsers = useCallback(async () => {
    try { const { data } = await api.get('/admin/users', { params: userQ ? { q: userQ } : {} }); setUsers(data.users || []); } catch (e) { /* noop */ }
  }, [userQ]);
  const loadAssets = useCallback(async () => {
    try { const { data } = await api.get('/admin/assets', { params: assetQ ? { q: assetQ } : {} }); setAssets(data.assets || []); } catch (e) { /* noop */ }
  }, [assetQ]);
  const loadAlerts = useCallback(async () => {
    try { const [a, e] = await Promise.all([api.get('/admin/alerts'), api.get('/admin/events')]); setAlerts(a.data.alerts || []); setEvents(e.data.events || []); } catch (er) { /* noop */ }
  }, []);
  const loadTxs = useCallback(async () => {
    try { const { data } = await api.get('/admin/transactions'); setTxs(data.transactions || []); } catch (e) { /* noop */ }
  }, []);
  const loadSettings = useCallback(async () => {
    try { const { data } = await api.get('/admin/settings'); setSettings(data); } catch (e) { /* noop */ }
  }, []);

  useEffect(() => { loadStats(); loadUsers(); loadAssets(); loadAlerts(); loadTxs(); loadSettings(); }, [loadStats, loadUsers, loadAssets, loadAlerts, loadTxs, loadSettings]);

  if (user && user.role !== 'superadmin') return <Navigate to="/app/dashboard" replace />;

  const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString(LOCALE_MAP[locale] || 'en-CA', { dateStyle: 'medium' }); } catch (e) { return iso; } };

  const updateUser = async (id, payload) => {
    try { await api.put(`/admin/users/${id}`, payload); toast.success(t('admin.userUpdated')); loadUsers(); loadStats(); }
    catch (e) { toast.error(e?.response?.data?.detail || t('auth.genericError')); }
  };
  const deleteUser = async (id) => {
    if (!window.confirm(t('admin.confirmDeleteUser'))) return;
    try { await api.delete(`/admin/users/${id}`); toast.success(t('admin.userDeleted')); loadUsers(); loadStats(); }
    catch (e) { toast.error(e?.response?.data?.detail || t('auth.genericError')); }
  };
  const refreshAsset = async (ticker) => {
    setBusy('asset-' + ticker);
    try { await api.post(`/admin/assets/refresh/${encodeURIComponent(ticker)}`); toast.success(t('asset.addedToast')); loadAssets(); }
    catch (e) { toast.error(t('auth.genericError')); } finally { setBusy(''); }
  };
  const deleteAsset = async (ticker) => {
    if (!window.confirm(t('admin.confirmDeleteAsset'))) return;
    try { await api.delete(`/admin/assets/${encodeURIComponent(ticker)}`); toast.success(t('admin.assetDeleted')); loadAssets(); loadStats(); }
    catch (e) { toast.error(t('auth.genericError')); }
  };
  const refreshUniverse = async () => {
    setBusy('universe');
    try { const { data } = await api.post('/admin/universe/refresh'); toast.success(`${t('admin.jobDone')} (${data.refreshed})`); loadAssets(); loadStats(); }
    catch (e) { toast.error(t('auth.genericError')); } finally { setBusy(''); }
  };
  const runDaily = async () => {
    setBusy('daily');
    try { await api.post('/admin/run-daily-refresh'); toast.success(t('admin.jobDone')); loadStats(); loadAssets(); }
    catch (e) { toast.error(t('auth.genericError')); } finally { setBusy(''); }
  };
  const doRefreshTicker = async () => { if (refreshTicker.trim()) { await refreshAsset(refreshTicker.trim().toUpperCase()); setRefreshTicker(''); } };

  const saveSettings = async () => {
    setBusy('settings');
    try {
      await api.put('/admin/settings', {
        weights: settings.weights, upside: settings.upside, income: settings.income, flags: settings.flags,
      });
      toast.success(t('admin.settingsSaved'));
    } catch (e) { toast.error(t('auth.genericError')); } finally { setBusy(''); }
  };

  const ConfigRow = ({ label, ok }) => (
    <div className="flex items-center justify-between py-2 border-b border-[var(--dz-border)] last:border-0">
      <span className="text-sm">{label}</span>
      <span className={`inline-flex items-center gap-1 text-xs ${ok ? 'text-[var(--dz-buy)]' : 'text-[var(--dz-muted)]'}`}>
        {ok ? <CheckCircle2 size={14} /> : <XCircle size={14} />}{ok ? t('admin.configured') : t('admin.notConfigured')}
      </span>
    </div>
  );

  const th = "text-left text-[11px] uppercase tracking-wide text-[var(--dz-muted)] font-medium px-3 py-2";
  const td = "px-3 py-2 text-sm border-t border-[var(--dz-border)] align-middle";

  return (
    <div>
      <div className="flex items-center gap-2">
        <Shield size={22} className="text-[var(--dz-primary)]" />
        <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('admin.title')}</h1>
      </div>
      <p className="mt-1 text-[var(--dz-muted)]">{t('admin.subtitle')}</p>

      <Tabs defaultValue="overview" className="mt-6">
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="overview" data-testid="admin-tab-overview"><LineChart size={15} className="mr-1.5" />{t('admin.tabs.overview')}</TabsTrigger>
          <TabsTrigger value="users" data-testid="admin-tab-users"><Users size={15} className="mr-1.5" />{t('admin.tabs.users')}</TabsTrigger>
          <TabsTrigger value="assets" data-testid="admin-tab-assets"><Database size={15} className="mr-1.5" />{t('admin.tabs.assets')}</TabsTrigger>
          <TabsTrigger value="alerts" data-testid="admin-tab-alerts"><BellRing size={15} className="mr-1.5" />{t('admin.tabs.alerts')}</TabsTrigger>
          <TabsTrigger value="billing" data-testid="admin-tab-billing"><CreditCard size={15} className="mr-1.5" />{t('admin.tabs.billing')}</TabsTrigger>
          <TabsTrigger value="settings" data-testid="admin-tab-settings"><SlidersHorizontal size={15} className="mr-1.5" />{t('admin.tabs.settings')}</TabsTrigger>
        </TabsList>

        {/* OVERVIEW */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Metric label={t('admin.metrics.users')} value={stats.users_total} icon={Users} />
              <Metric label={t('admin.metrics.assets')} value={stats.assets_total} icon={Database} />
              <Metric label={t('admin.metrics.activeAlerts')} value={stats.active_alerts} icon={BellRing} accent="var(--dz-hold)" />
              <Metric label={t('admin.metrics.events')} value={stats.events_total} icon={Bell} />
              <Metric label={t('admin.metrics.watchlist')} value={stats.watchlist_total} icon={LineChart} />
              <Metric label={t('admin.planFree')} value={stats.plan_counts?.free ?? 0} icon={Users} />
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
                <ConfigRow label="Finnhub" ok={config.finnhub} />
                <ConfigRow label="FMP" ok={config.fmp} />
                <ConfigRow label="Stripe" ok={config.stripe} />
                <ConfigRow label="Resend" ok={config.resend} />
              </>)}
              <div className="mt-4 flex gap-2">
                <Button size="sm" variant="outline" onClick={refreshUniverse} disabled={busy === 'universe'} data-testid="admin-refresh-universe">
                  {busy === 'universe' ? <Loader2 size={14} className="animate-spin mr-1" /> : <RefreshCw size={14} className="mr-1" />}{t('admin.refreshUniverse')}
                </Button>
                <Button size="sm" variant="outline" onClick={runDaily} disabled={busy === 'daily'} data-testid="admin-run-daily">
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
        </TabsContent>

        {/* USERS */}
        <TabsContent value="users" className="mt-6">
          <div className="flex gap-2 mb-4 max-w-sm">
            <Input value={userQ} onChange={(e) => setUserQ(e.target.value)} placeholder={t('admin.search')} data-testid="admin-user-search" />
            <Button variant="outline" onClick={loadUsers}><Search size={16} /></Button>
          </div>
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead><tr>
                <th className={th}>{t('admin.colEmail')}</th><th className={th}>{t('admin.colPlan')}</th><th className={th}>{t('admin.colRole')}</th>
                <th className={th}>{t('admin.colWatch')}</th><th className={th}>{t('admin.colAlerts')}</th><th className={th}>{t('admin.colCreated')}</th><th className={th}>{t('admin.colActions')}</th>
              </tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} data-testid="admin-user-row">
                    <td className={td}>{u.email}</td>
                    <td className={td}>
                      <Select value={u.plan} onValueChange={(v) => updateUser(u.id, { plan: v })}>
                        <SelectTrigger className="h-8 w-32" data-testid="admin-user-plan-select"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="free">{t('admin.planFree')}</SelectItem>
                          <SelectItem value="pro">{t('admin.planPro')}</SelectItem>
                          <SelectItem value="investor">{t('admin.planInvestor')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className={td}>
                      <Select value={u.role || 'user'} onValueChange={(v) => updateUser(u.id, { role: v })}>
                        <SelectTrigger className="h-8 w-32"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="user">{t('admin.role_user')}</SelectItem>
                          <SelectItem value="superadmin">{t('admin.role_superadmin')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className={td + ' tnum'}>{u.watchlist_count}</td>
                    <td className={td + ' tnum'}>{u.alerts_count}</td>
                    <td className={td}>{fmtDate(u.created_at)}</td>
                    <td className={td}>
                      <Button variant="ghost" size="icon" onClick={() => deleteUser(u.id)} disabled={u.role === 'superadmin'} data-testid="admin-user-delete">
                        <Trash2 size={15} className="text-[var(--dz-sell)]" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </TabsContent>

        {/* ASSETS */}
        <TabsContent value="assets" className="mt-6">
          <div className="flex flex-wrap gap-2 mb-4">
            <div className="flex gap-2 max-w-xs"><Input value={assetQ} onChange={(e) => setAssetQ(e.target.value)} placeholder={t('admin.search')} data-testid="admin-asset-search" /><Button variant="outline" onClick={loadAssets}><Search size={16} /></Button></div>
            <div className="flex gap-2 max-w-xs ml-auto"><Input value={refreshTicker} onChange={(e) => setRefreshTicker(e.target.value)} placeholder="AAPL" data-testid="admin-refresh-ticker-input" /><Button onClick={doRefreshTicker} className="bg-[var(--dz-primary)] text-white"><RefreshCw size={16} className="mr-1" />{t('admin.refresh')}</Button></div>
          </div>
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead><tr>
                <th className={th}>{t('admin.colTicker')}</th><th className={th}>{t('admin.colName')}</th><th className={th}>{t('admin.colPrice')}</th><th className={th}>{t('admin.colScore')}</th><th className={th}>{t('admin.colSignal')}</th><th className={th}>{t('admin.colActions')}</th>
              </tr></thead>
              <tbody>
                {assets.map((a) => (
                  <tr key={a.ticker} data-testid="admin-asset-row">
                    <td className={td + ' font-medium'}>{a.ticker}</td>
                    <td className={td + ' max-w-[220px] truncate'}>{a.name}</td>
                    <td className={td + ' tnum'}>{formatCurrency(a.price, a.currency, locale)}</td>
                    <td className={td + ' tnum'}>{a.score ?? '—'}</td>
                    <td className={td}><SignalBadge classification={a.classification} size="sm" /></td>
                    <td className={td}>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => refreshAsset(a.ticker)} disabled={busy === 'asset-' + a.ticker}><RefreshCw size={14} className={busy === 'asset-' + a.ticker ? 'animate-spin' : ''} /></Button>
                        <Button variant="ghost" size="icon" onClick={() => deleteAsset(a.ticker)}><Trash2 size={14} className="text-[var(--dz-sell)]" /></Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </TabsContent>

        {/* ALERTS */}
        <TabsContent value="alerts" className="mt-6 space-y-6">
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[680px]">
              <thead><tr><th className={th}>{t('admin.colUser')}</th><th className={th}>{t('admin.colTicker')}</th><th className={th}>{t('admin.colType')}</th><th className={th}>{t('admin.colActive')}</th><th className={th}>{t('admin.colDate')}</th></tr></thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id}>
                    <td className={td}>{a.user_email}</td><td className={td + ' font-medium'}>{a.ticker}</td>
                    <td className={td}>{t(`alerts.types.${a.type}`)}</td>
                    <td className={td}>{a.active ? t('alerts.active') : t('alerts.inactive')}</td>
                    <td className={td}>{fmtDate(a.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div>
            <h3 className="font-heading font-semibold mb-3">{t('notifications.title')}</h3>
            <Card className="overflow-x-auto">
              <table className="w-full min-w-[680px]">
                <thead><tr><th className={th}>{t('admin.colTicker')}</th><th className={th}>{t('admin.colMessage')}</th><th className={th}>{t('admin.colDate')}</th></tr></thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id}><td className={td + ' font-medium'}>{e.ticker}</td><td className={td + ' max-w-[420px] truncate'}>{e.message}</td><td className={td}>{fmtDate(e.created_at)}</td></tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        </TabsContent>

        {/* BILLING */}
        <TabsContent value="billing" className="mt-6">
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <Metric label={t('admin.metrics.revenue')} value={`US$${(stats.revenue || 0).toFixed(2)}`} icon={CreditCard} accent="var(--dz-buy)" />
              <Metric label={t('admin.metrics.paid')} value={stats.paid_transactions} icon={CheckCircle2} />
              <Metric label={t('admin.planInvestor')} value={stats.plan_counts?.investor ?? 0} icon={Users} accent="var(--dz-primary)" />
            </div>
          )}
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[680px]">
              <thead><tr><th className={th}>{t('admin.colEmail')}</th><th className={th}>{t('admin.colPlan')}</th><th className={th}>{t('admin.colAmount')}</th><th className={th}>{t('admin.colStatus')}</th><th className={th}>{t('admin.colDate')}</th></tr></thead>
              <tbody>
                {txs.length === 0 ? (
                  <tr><td className={td + ' text-[var(--dz-muted)]'} colSpan={5}>{t('admin.noData')}</td></tr>
                ) : txs.map((tx) => (
                  <tr key={tx.session_id}><td className={td}>{tx.email}</td><td className={td}>{tx.plan} ({tx.billing})</td><td className={td + ' tnum'}>US${(tx.amount || 0).toFixed(2)}</td><td className={td}>{tx.payment_status}</td><td className={td}>{fmtDate(tx.created_at)}</td></tr>
                ))}
              </tbody>
            </table>
          </Card>
        </TabsContent>

        {/* SETTINGS */}
        <TabsContent value="settings" className="mt-6">
          <Card className="p-6 max-w-2xl">
            <h3 className="font-heading font-semibold">{t('admin.scoringTitle')}</h3>
            <p className="text-sm text-[var(--dz-muted)] mt-1">{t('admin.scoringHelp')}</p>
            {settings && (
              <div className="mt-5 space-y-6">
                <div>
                  <p className="text-sm font-medium mb-2">{t('admin.weights')}</p>
                  <div className="grid grid-cols-3 gap-3">
                    {[['buy', 'wBuy'], ['upside', 'wUpside'], ['income', 'wIncome']].map(([k, lbl]) => (
                      <div key={k} className="space-y-1">
                        <Label className="text-xs">{t(`admin.${lbl}`)}</Label>
                        <Input type="number" step="0.05" value={settings.weights[k]} data-testid={`admin-weight-${k}`}
                          onChange={(e) => setSettings({ ...settings, weights: { ...settings.weights, [k]: Number(e.target.value) } })} />
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">{t('admin.thresholds')}</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="space-y-1"><Label className="text-xs">{t('admin.buyZone')}</Label><Input type="number" step="0.01" value={settings.flags.buy_zone_r} onChange={(e) => setSettings({ ...settings, flags: { ...settings.flags, buy_zone_r: Number(e.target.value) } })} /></div>
                    <div className="space-y-1"><Label className="text-xs">{t('admin.sellZone')}</Label><Input type="number" step="0.01" value={settings.flags.sell_zone_r} onChange={(e) => setSettings({ ...settings, flags: { ...settings.flags, sell_zone_r: Number(e.target.value) } })} /></div>
                    <div className="space-y-1"><Label className="text-xs">{t('admin.incomeFlag')}</Label><Input type="number" step="0.005" value={settings.flags.income_d} onChange={(e) => setSettings({ ...settings, flags: { ...settings.flags, income_d: Number(e.target.value) } })} /></div>
                    <div className="space-y-1"><Label className="text-xs">{t('admin.upsideCap')}</Label><Input type="number" step="0.05" value={settings.upside.cap} onChange={(e) => setSettings({ ...settings, upside: { ...settings.upside, cap: Number(e.target.value) } })} /></div>
                    <div className="space-y-1"><Label className="text-xs">{t('admin.incomeCap')}</Label><Input type="number" step="0.01" value={settings.income.cap} onChange={(e) => setSettings({ ...settings, income: { ...settings.income, cap: Number(e.target.value) } })} /></div>
                  </div>
                </div>
                <Button onClick={saveSettings} disabled={busy === 'settings'} data-testid="admin-settings-save" className="bg-[var(--dz-primary)] text-white">
                  {busy === 'settings' ? t('common.saving') : t('admin.save')}
                </Button>
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
