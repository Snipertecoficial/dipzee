import React from 'react';
import { useTranslation } from 'react-i18next';
import { CreditCard, CheckCircle2, Users } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Metric, TH_CLASS, TD_CLASS, fmtDate } from './AdminShared';

export function AdminBillingTab({ stats, txs }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';
  return (
    <>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <Metric label={t('admin.metrics.revenue')} value={`US$${(stats.revenue || 0).toFixed(2)}`} icon={CreditCard} accent="var(--dz-buy)" />
          <Metric label={t('admin.metrics.paid')} value={stats.paid_transactions} icon={CheckCircle2} />
          <Metric label={t('admin.planInvestor')} value={stats.plan_counts?.investor ?? 0} icon={Users} accent="var(--dz-primary)" />
        </div>
      )}
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[680px]">
          <thead><tr><th className={TH_CLASS}>{t('admin.colEmail')}</th><th className={TH_CLASS}>{t('admin.colPlan')}</th><th className={TH_CLASS}>{t('admin.colAmount')}</th><th className={TH_CLASS}>{t('admin.colStatus')}</th><th className={TH_CLASS}>{t('admin.colDate')}</th></tr></thead>
          <tbody>
            {txs.length === 0 ? (
              <tr><td className={TD_CLASS + ' text-[var(--dz-muted)]'} colSpan={5}>{t('admin.noData')}</td></tr>
            ) : txs.map((tx) => (
              <tr key={tx.session_id}><td className={TD_CLASS}>{tx.email}</td><td className={TD_CLASS}>{tx.plan} ({tx.billing})</td><td className={TD_CLASS + ' tnum'}>US${(tx.amount || 0).toFixed(2)}</td><td className={TD_CLASS}>{tx.payment_status}</td><td className={TD_CLASS}>{fmtDate(tx.created_at, locale)}</td></tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
