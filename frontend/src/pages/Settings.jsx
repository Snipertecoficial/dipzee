import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Crown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const LANGS = [{ code: 'en', label: 'English' }, { code: 'fr', label: 'Fran\u00e7ais' }, { code: 'pt', label: 'Portugu\u00eas' }, { code: 'es', label: 'Espa\u00f1ol' }];

export default function Settings() {
  const { t } = useTranslation();
  const { user, updateProfile } = useAuth();
  const [language, setLanguage] = useState(user?.locale || 'en');
  const [currency, setCurrency] = useState(user?.currency || 'CAD');
  const [prefs, setPrefs] = useState(user?.default_alert_prefs || { email: true, in_app: true });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await updateProfile({ locale: language, currency, default_alert_prefs: prefs });
      toast.success(t('settings.saved'));
    } catch (e) { toast.error(t('auth.genericError')); }
    finally { setSaving(false); }
  };

  return (
    <div data-testid="settings-page" className="max-w-2xl">
      <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('settings.title')}</h1>
      <p className="mt-1 text-[var(--dz-muted)]">{t('settings.subtitle')}</p>

      <Card className="mt-6 p-6 space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div><p className="font-medium">{t('settings.language')}</p><p className="text-sm text-[var(--dz-muted)]">{t('settings.languageDesc')}</p></div>
          <Select value={language} onValueChange={setLanguage}>
            <SelectTrigger className="w-40" data-testid="settings-language-select"><SelectValue /></SelectTrigger>
            <SelectContent>{LANGS.map((l) => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="flex items-center justify-between gap-4 border-t border-[var(--dz-border)] pt-5">
          <div><p className="font-medium">{t('settings.currency')}</p><p className="text-sm text-[var(--dz-muted)]">{t('settings.currencyDesc')}</p></div>
          <Select value={currency} onValueChange={setCurrency}>
            <SelectTrigger className="w-40" data-testid="settings-currency-select"><SelectValue /></SelectTrigger>
            <SelectContent>{['CAD', 'USD', 'BRL'].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </Card>

      <Card className="mt-5 p-6 space-y-5">
        <p className="font-heading font-semibold">{t('settings.alertPrefs')}</p>
        <div className="flex items-center justify-between gap-4">
          <div><p className="font-medium">{t('settings.alertEmail')}</p><p className="text-sm text-[var(--dz-muted)]">{t('settings.alertEmailDesc')}</p></div>
          <Switch checked={!!prefs.email} onCheckedChange={(v) => setPrefs({ ...prefs, email: v })} data-testid="settings-email-switch" />
        </div>
        <div className="flex items-center justify-between gap-4 border-t border-[var(--dz-border)] pt-5">
          <div><p className="font-medium">{t('settings.alertInApp')}</p><p className="text-sm text-[var(--dz-muted)]">{t('settings.alertInAppDesc')}</p></div>
          <Switch checked={!!prefs.in_app} onCheckedChange={(v) => setPrefs({ ...prefs, in_app: v })} data-testid="settings-inapp-switch" />
        </div>
      </Card>

      <Card className="mt-5 p-6">
        <p className="font-heading font-semibold">{t('settings.subscription')}</p>
        <div className="mt-3 flex items-center justify-between gap-4">
          <div><p className="text-sm text-[var(--dz-muted)]">{t('settings.currentPlan')}</p><p className="font-medium capitalize">{t(`plans.${user?.plan || 'free'}`)}</p></div>
          <Link to="/app/upgrade"><Button variant="outline"><Crown size={16} className="mr-2" />{t('nav.upgrade')}</Button></Link>
        </div>
      </Card>

      <div className="mt-6">
        <Button onClick={save} disabled={saving} data-testid="settings-save-button" className="bg-[var(--dz-primary)] text-white">{saving ? t('common.saving') : t('common.save')}</Button>
      </div>
    </div>
  );
}
