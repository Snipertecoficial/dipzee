import React, { useEffect, useState, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import {
  Users, LineChart, BellRing, CreditCard, SlidersHorizontal, Shield, Database,
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';
import { AdminOverviewTab } from './admin/AdminOverviewTab';
import { AdminUsersTab } from './admin/AdminUsersTab';
import { AdminAssetsTab } from './admin/AdminAssetsTab';
import { AdminAlertsTab } from './admin/AdminAlertsTab';
import { AdminBillingTab } from './admin/AdminBillingTab';
import { AdminSettingsTab } from './admin/AdminSettingsTab';

// Admin acts as the orchestrator: it owns all state, data loaders and action
// handlers, then delegates presentation to focused per-tab subcomponents.
export default function Admin() {
  const { t } = useTranslation();
  const { user } = useAuth();

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

  if (user && user.role !== 'superadmin') return <Navigate to="/app/dashboard" replace />;

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

        <TabsContent value="overview" className="mt-6 space-y-6">
          <AdminOverviewTab stats={stats} config={config} busy={busy} onRefreshUniverse={refreshUniverse} onRunDaily={runDaily} />
        </TabsContent>

        <TabsContent value="users" className="mt-6">
          <AdminUsersTab users={users} userQ={userQ} setUserQ={setUserQ} onSearch={loadUsers} onUpdateUser={updateUser} onDeleteUser={deleteUser} />
        </TabsContent>

        <TabsContent value="assets" className="mt-6">
          <AdminAssetsTab
            assets={assets} assetQ={assetQ} setAssetQ={setAssetQ}
            refreshTicker={refreshTicker} setRefreshTicker={setRefreshTicker}
            onSearch={loadAssets} onRefreshTicker={doRefreshTicker}
            onRefreshAsset={refreshAsset} onDeleteAsset={deleteAsset} busy={busy}
          />
        </TabsContent>

        <TabsContent value="alerts" className="mt-6 space-y-6">
          <AdminAlertsTab alerts={alerts} events={events} />
        </TabsContent>

        <TabsContent value="billing" className="mt-6">
          <AdminBillingTab stats={stats} txs={txs} />
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <AdminSettingsTab settings={settings} setSettings={setSettings} onSave={saveSettings} busy={busy} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
