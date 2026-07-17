import React from 'react';
import { useTranslation } from 'react-i18next';
import { CreditCard, CheckCircle2, Users, RefreshCw, Undo2, Download, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Metric, TH_CLASS, TD_CLASS, fmtDate } from './AdminShared';

const STATUS_STYLES = {
  paid: 'bg-[rgba(22,163,74,0.12)] text-[var(--dz-buy-deep)] border border-[rgba(22,163,74,0.25)]',
  active: 'bg-[rgba(22,163,74,0.12)] text-[var(--dz-buy-deep)] border border-[rgba(22,163,74,0.25)]',
  trialing: 'bg-[rgba(22,224,163,0.14)] text-[var(--dz-buy-deep)] border border-[rgba(22,224,163,0.28)]',
  initiated: 'bg-[rgba(245,158,11,0.14)] text-[rgba(146,64,14,1)] border border-[rgba(245,158,11,0.28)]',
  pending: 'bg-[rgba(245,158,11,0.14)] text-[rgba(146,64,14,1)] border border-[rgba(245,158,11,0.28)]',
  open: 'bg-[rgba(245,158,11,0.14)] text-[rgba(146,64,14,1)] border border-[rgba(245,158,11,0.28)]',
  past_due: 'bg-[rgba(249,115,22,0.14)] text-[rgba(154,52,18,1)] border border-[rgba(249,115,22,0.28)]',
  expired: 'bg-[rgba(91,100,120,0.12)] text-[var(--dz-slate)] border border-[rgba(91,100,120,0.22)]',
  canceled: 'bg-[rgba(229,72,77,0.12)] text-[var(--dz-sell)] border border-[rgba(229,72,77,0.26)]',
  unpaid: 'bg-[rgba(229,72,77,0.12)] text-[var(--dz-sell)] border border-[rgba(229,72,77,0.26)]',
  incomplete_expired: 'bg-[rgba(229,72,77,0.12)] text-[var(--dz-sell)] border border-[rgba(229,72,77,0.26)]',
};

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'bg-[rgba(91,100,120,0.12)] text-[var(--dz-slate)] border border-[rgba(91,100,120,0.22)]';
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${cls}`}>{status || '—'}</span>;
}

export function AdminBillingTab({ stats, txs, busy, onSync, onRefund }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';
  const syncing = busy === 'billing-sync';

  const exportCsv = () => {
    const rows = [['email', 'plan', 'interval', 'amount', 'currency', 'payment_status', 'status', 'refunded', 'created_at', 'session_id']];
    txs.forEach((tx) => rows.push([
      tx.email, tx.plan, tx.interval, tx.amount, tx.currency, tx.payment_status, tx.status, tx.refunded ? 'yes' : 'no', tx.created_at, tx.session_id,
    ]));
    const csv = rows.map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a'); a.href = url; a.download = 'dipzee-transactions.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <Metric label={t('admin.metrics.revenue')} value={`US$${(stats.revenue || 0).toFixed(2)}`} icon={CreditCard} accent="var(--dz-buy)" />
          <Metric label={t('admin.metrics.paid')} value={stats.paid_transactions} icon={CheckCircle2} />
          <Metric label={t('admin.planInvestor')} value={stats.plan_counts?.investor ?? 0} icon={Users} accent="var(--dz-primary)" />
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <p className="text-xs text-[var(--dz-muted)] max-w-md">{t('admin.billingSyncDesc')}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onSync} disabled={syncing} data-testid="admin-billing-sync-button" className="border-[var(--dz-border)]">
            {syncing ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <RefreshCw size={14} className="mr-1.5" />}
            {t('admin.billingSync')}
          </Button>
          <Button variant="outline" size="sm" onClick={exportCsv} data-testid="admin-billing-export-button" className="border-[var(--dz-border)]">
            <Download size={14} className="mr-1.5" /> CSV
          </Button>
        </div>
      </div>

      <Card className="overflow-x-auto">
        <table className="w-full min-w-[820px]">
          <thead>
            <tr>
              <th className={TH_CLASS}>{t('admin.colEmail')}</th>
              <th className={TH_CLASS}>{t('admin.colPlan')}</th>
              <th className={TH_CLASS}>{t('admin.colAmount')}</th>
              <th className={TH_CLASS}>{t('admin.colStatus')}</th>
              <th className={TH_CLASS}>{t('admin.colDate')}</th>
              <th className={TH_CLASS}></th>
            </tr>
          </thead>
          <tbody>
            {txs.length === 0 ? (
              <tr><td className={TD_CLASS + ' text-[var(--dz-muted)]'} colSpan={6}>{t('admin.noData')}</td></tr>
            ) : txs.map((tx) => {
              const refunding = busy === `refund-${tx.id}`;
              const canRefund = tx.payment_status === 'paid' && !tx.refunded;
              return (
                <tr key={tx.id || tx.session_id}>
                  <td className={TD_CLASS}>{tx.email}</td>
                  <td className={TD_CLASS}>{tx.plan} {tx.interval ? `(${tx.interval})` : ''}</td>
                  <td className={TD_CLASS + ' tnum'}>US${(tx.amount || 0).toFixed(2)}</td>
                  <td className={TD_CLASS}>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <StatusBadge status={tx.payment_status} />
                      {tx.refunded && <StatusBadge status="refunded" />}
                    </div>
                  </td>
                  <td className={TD_CLASS}>{fmtDate(tx.created_at, locale)}</td>
                  <td className={TD_CLASS}>
                    {canRefund && (
                      <Button variant="ghost" size="sm" onClick={() => onRefund(tx.id)} disabled={refunding} data-testid={`admin-refund-${tx.id}`} className="text-[var(--dz-sell)] hover:text-[var(--dz-sell)] hover:bg-[rgba(229,72,77,0.08)]">
                        {refunding ? <Loader2 size={13} className="mr-1 animate-spin" /> : <Undo2 size={13} className="mr-1" />}
                        {t('admin.refund')}
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </>
  );
}
