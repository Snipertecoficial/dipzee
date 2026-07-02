import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function AdminSettingsTab({ settings, setSettings, onSave, busy }) {
  const { t } = useTranslation();
  return (
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
          <Button onClick={onSave} disabled={busy === 'settings'} data-testid="admin-settings-save" className="bg-[var(--dz-primary)] text-white">
            {busy === 'settings' ? t('common.saving') : t('admin.save')}
          </Button>
        </div>
      )}
    </Card>
  );
}
