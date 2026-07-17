import React from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Trash2, ShieldOff, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TH_CLASS, TD_CLASS, fmtDate } from './AdminShared';

export function AdminUsersTab({ users, userQ, setUserQ, onSearch, onUpdateUser, onDeleteUser, onRevokeSessions, busy }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language?.slice(0, 2) || 'en';
  return (
    <>
      <div className="flex gap-2 mb-4 max-w-sm">
        <Input value={userQ} onChange={(e) => setUserQ(e.target.value)} placeholder={t('admin.search')} data-testid="admin-user-search" />
        <Button variant="outline" onClick={onSearch}><Search size={16} /></Button>
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[720px]">
          <thead><tr>
            <th className={TH_CLASS}>{t('admin.colEmail')}</th><th className={TH_CLASS}>{t('admin.colPlan')}</th><th className={TH_CLASS}>{t('admin.colRole')}</th>
            <th className={TH_CLASS}>{t('admin.colWatch')}</th><th className={TH_CLASS}>{t('admin.colAlerts')}</th><th className={TH_CLASS}>{t('admin.colCreated')}</th><th className={TH_CLASS}>{t('admin.colActions')}</th>
          </tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} data-testid="admin-user-row">
                <td className={TD_CLASS}>{u.email}</td>
                <td className={TD_CLASS}>
                  <Select value={u.plan} onValueChange={(v) => onUpdateUser(u.id, { plan: v })}>
                    <SelectTrigger className="h-8 w-32" data-testid="admin-user-plan-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{t('admin.planNone')}</SelectItem>
                      <SelectItem value="starter">{t('admin.planStarter')}</SelectItem>
                      <SelectItem value="pro">{t('admin.planPro')}</SelectItem>
                      <SelectItem value="investor">{t('admin.planInvestor')}</SelectItem>
                    </SelectContent>
                  </Select>
                </td>
                <td className={TD_CLASS}>
                  <Select value={u.role || 'user'} onValueChange={(v) => onUpdateUser(u.id, { role: v })}>
                    <SelectTrigger className="h-8 w-32"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">{t('admin.role_user')}</SelectItem>
                      <SelectItem value="superadmin">{t('admin.role_superadmin')}</SelectItem>
                    </SelectContent>
                  </Select>
                </td>
                <td className={TD_CLASS + ' tnum'}>{u.watchlist_count}</td>
                <td className={TD_CLASS + ' tnum'}>{u.alerts_count}</td>
                <td className={TD_CLASS}>{fmtDate(u.created_at, locale)}</td>
                <td className={TD_CLASS}>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" onClick={() => onRevokeSessions(u.id)} disabled={busy === `revoke-${u.id}`} title={t('admin.revokeSessions')} data-testid="admin-user-revoke-sessions">
                      {busy === `revoke-${u.id}` ? <Loader2 size={15} className="animate-spin" /> : <ShieldOff size={15} className="text-[var(--dz-muted)]" />}
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => onDeleteUser(u.id)} disabled={u.role === 'superadmin'} data-testid="admin-user-delete">
                      <Trash2 size={15} className="text-[var(--dz-sell)]" />
                    </Button>
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
