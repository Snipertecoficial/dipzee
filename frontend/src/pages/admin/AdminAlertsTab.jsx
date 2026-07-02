import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/card';
import { TH_CLASS, TD_CLASS, fmtDate } from './AdminShared';

export function AdminAlertsTab({ alerts, events }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';
  return (
    <>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[680px]">
          <thead><tr><th className={TH_CLASS}>{t('admin.colUser')}</th><th className={TH_CLASS}>{t('admin.colTicker')}</th><th className={TH_CLASS}>{t('admin.colType')}</th><th className={TH_CLASS}>{t('admin.colActive')}</th><th className={TH_CLASS}>{t('admin.colDate')}</th></tr></thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td className={TD_CLASS}>{a.user_email}</td><td className={TD_CLASS + ' font-medium'}>{a.ticker}</td>
                <td className={TD_CLASS}>{t(`alerts.types.${a.type}`)}</td>
                <td className={TD_CLASS}>{a.active ? t('alerts.active') : t('alerts.inactive')}</td>
                <td className={TD_CLASS}>{fmtDate(a.created_at, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div>
        <h3 className="font-heading font-semibold mb-3">{t('notifications.title')}</h3>
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[680px]">
            <thead><tr><th className={TH_CLASS}>{t('admin.colTicker')}</th><th className={TH_CLASS}>{t('admin.colMessage')}</th><th className={TH_CLASS}>{t('admin.colDate')}</th></tr></thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}><td className={TD_CLASS + ' font-medium'}>{e.ticker}</td><td className={TD_CLASS + ' max-w-[420px] truncate'}>{e.message}</td><td className={TD_CLASS}>{fmtDate(e.created_at, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}
