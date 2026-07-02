import React from 'react';
import { useTranslation } from 'react-i18next';
import { Search, RefreshCw, Trash2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SignalBadge } from '../../components/SignalBadge';
import { formatCurrency } from '../../lib/format';
import { TH_CLASS, TD_CLASS } from './AdminShared';

export function AdminAssetsTab({
  assets, assetQ, setAssetQ, refreshTicker, setRefreshTicker,
  onSearch, onRefreshTicker, onRefreshAsset, onDeleteAsset, busy,
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';
  return (
    <>
      <div className="flex flex-wrap gap-2 mb-4">
        <div className="flex gap-2 max-w-xs"><Input value={assetQ} onChange={(e) => setAssetQ(e.target.value)} placeholder={t('admin.search')} data-testid="admin-asset-search" /><Button variant="outline" onClick={onSearch}><Search size={16} /></Button></div>
        <div className="flex gap-2 max-w-xs ml-auto"><Input value={refreshTicker} onChange={(e) => setRefreshTicker(e.target.value)} placeholder="AAPL" data-testid="admin-refresh-ticker-input" /><Button onClick={onRefreshTicker} className="bg-[var(--dz-primary)] text-white"><RefreshCw size={16} className="mr-1" />{t('admin.refresh')}</Button></div>
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[720px]">
          <thead><tr>
            <th className={TH_CLASS}>{t('admin.colTicker')}</th><th className={TH_CLASS}>{t('admin.colName')}</th><th className={TH_CLASS}>{t('admin.colPrice')}</th><th className={TH_CLASS}>{t('admin.colScore')}</th><th className={TH_CLASS}>{t('admin.colSignal')}</th><th className={TH_CLASS}>{t('admin.colActions')}</th>
          </tr></thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.ticker} data-testid="admin-asset-row">
                <td className={TD_CLASS + ' font-medium'}>{a.ticker}</td>
                <td className={TD_CLASS + ' max-w-[220px] truncate'}>{a.name}</td>
                <td className={TD_CLASS + ' tnum'}>{formatCurrency(a.price, a.currency, locale)}</td>
                <td className={TD_CLASS + ' tnum'}>{a.score ?? '\u2014'}</td>
                <td className={TD_CLASS}><SignalBadge classification={a.classification} size="sm" /></td>
                <td className={TD_CLASS}>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" onClick={() => onRefreshAsset(a.ticker)} disabled={busy === 'asset-' + a.ticker}><RefreshCw size={14} className={busy === 'asset-' + a.ticker ? 'animate-spin' : ''} /></Button>
                    <Button variant="ghost" size="icon" onClick={() => onDeleteAsset(a.ticker)}><Trash2 size={14} className="text-[var(--dz-sell)]" /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
