import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bell, CheckCheck } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LOCALE_MAP } from '../lib/format';
import api from '../lib/api';

export default function Notifications() {
  const { t, i18n } = useTranslation();
  const [events, setEvents] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const locale = i18n.language?.slice(0, 2) || 'en';

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get('/notifications'); setEvents(data.events || []); setUnread(data.unread || 0); }
    catch (e) { /* noop */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const markAll = async () => { await api.post('/notifications/read-all'); load(); };
  const markOne = async (id) => { await api.post(`/notifications/${id}/read`); load(); };

  const fmtDate = (iso) => {
    try { return new Date(iso).toLocaleString(LOCALE_MAP[locale] || 'en-CA', { dateStyle: 'medium', timeStyle: 'short' }); }
    catch (e) { return iso; }
  };

  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('notifications.title')}</h1>
          <p className="mt-1 text-[var(--dz-muted)]">{t('notifications.subtitle')}</p>
        </div>
        {unread > 0 && <Button variant="outline" onClick={markAll}><CheckCheck size={16} className="mr-2" />{t('notifications.markAllRead')}</Button>}
      </div>

      {loading ? null : events.length === 0 ? (
        <Card className="mt-8 p-10 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-[var(--dz-canvas)] flex items-center justify-center"><Bell className="text-[var(--dz-muted)]" /></div>
          <p className="mt-4 text-[var(--dz-muted)]">{t('notifications.empty')}</p>
        </Card>
      ) : (
        <div className="mt-6 space-y-3" data-testid="notifications-inbox">
          {events.map((e) => (
            <Card key={e.id} data-testid="notification-list-item" onClick={() => !e.read && markOne(e.id)}
              className={`p-4 cursor-pointer transition-colors ${e.read ? '' : 'border-l-4 border-l-[var(--dz-mint)]'}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Link to={`/app/asset/${encodeURIComponent(e.ticker)}`} onClick={(ev) => ev.stopPropagation()} className="font-heading font-semibold hover:underline">{e.ticker}</Link>
                    {!e.read && <span className="text-[10px] rounded-full px-1.5 py-0.5 bg-[rgba(22,224,163,0.18)] text-[var(--dz-buy-deep)]">{t('notifications.new')}</span>}
                  </div>
                  <p className="text-sm text-[var(--dz-fg)] mt-1">{e.message}</p>
                </div>
                <span className="text-[11px] text-[var(--dz-muted)] whitespace-nowrap">{fmtDate(e.created_at)}</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
