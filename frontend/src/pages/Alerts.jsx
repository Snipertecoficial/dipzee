import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Trash2, BellRing } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { CreateAlertDialog } from '../components/CreateAlertDialog';
import api from '../lib/api';

export default function Alerts() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get('/alerts'); setAlerts(data || []); }
    catch (e) { /* noop */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = async (a) => {
    try {
      await api.put(`/alerts/${a.id}`, { active: !a.active });
      load();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(detail?.code === 'alert_limit' ? t('alerts.limitReached') : t('auth.genericError'));
    }
  };
  const remove = async (id) => {
    try { await api.delete(`/alerts/${id}`); toast.success(t('alerts.deleted')); load(); }
    catch (e) { toast.error(t('auth.genericError')); }
  };

  const describe = (a) => {
    const base = t(`alerts.types.${a.type}`);
    const v = a.params?.value;
    return v !== undefined && v !== null ? `${base} ${v}` : base;
  };

  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('alerts.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('alerts.subtitle')}</p>
        </div>
        <CreateAlertDialog onCreated={load} />
      </div>

      {loading ? null : alerts.length === 0 ? (
        <Card className="mt-8 p-10 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-[var(--dz-canvas)] flex items-center justify-center"><BellRing className="text-[var(--dz-muted)]" /></div>
          <h3 className="mt-4 font-heading font-semibold text-lg">{t('alerts.none')}</h3>
          <p className="mt-2 text-sm text-[var(--dz-muted)]">{t('alerts.noneDesc')}</p>
        </Card>
      ) : (
        <div className="mt-6 space-y-3">
          {alerts.map((a) => (
            <Card key={a.id} className="p-4 flex items-center justify-between gap-4" data-testid="alert-row">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Link to={`/app/asset/${encodeURIComponent(a.ticker)}`} className="font-heading font-semibold hover:underline">{a.ticker}</Link>
                </div>
                <p className="text-sm text-[var(--dz-muted)] mt-0.5">{describe(a)}</p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <div className="flex items-center gap-2">
                  <Switch checked={a.active} onCheckedChange={() => toggle(a)} data-testid="alert-active-switch" />
                  <span className="text-xs text-[var(--dz-muted)] hidden sm:inline">{a.active ? t('alerts.active') : t('alerts.inactive')}</span>
                </div>
                <Button variant="ghost" size="icon" onClick={() => remove(a.id)} aria-label={t('alerts.delete')} data-testid="alert-delete-button">
                  <Trash2 size={16} className="text-[var(--dz-sell)]" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
