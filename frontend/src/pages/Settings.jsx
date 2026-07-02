import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Crown, Camera, Trash2, Check, Sun, Moon, Monitor, Lock } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

const LANGS = [{ code: 'en', label: 'English' }, { code: 'fr', label: 'Fran\u00e7ais' }, { code: 'pt', label: 'Portugu\u00eas' }, { code: 'es', label: 'Espa\u00f1ol' }];
const MAX_FILE = 1_100_000; // ~1MB source -> ~1.4MB base64

export default function Settings() {
  const { t } = useTranslation();
  const { user, updateProfile, can } = useAuth();
  const { theme, setTheme } = useTheme();
  const fileRef = useRef(null);

  const [profile, setProfile] = useState({
    display_name: user?.display_name || '', bio: user?.bio || '',
    phone: user?.phone || '', country: user?.country || '',
  });
  const [avatar, setAvatar] = useState(user?.avatar || null);
  const [language, setLanguage] = useState(user?.locale || 'en');
  const [currency, setCurrency] = useState(user?.currency || 'USD');
  const [prefs, setPrefs] = useState(user?.default_alert_prefs || { email: true, in_app: true, telegram: false, webhook: false });
  const [channels, setChannels] = useState({ telegram_chat_id: user?.telegram_chat_id || '', webhook_url: user?.webhook_url || '' });
  const [saving, setSaving] = useState(false);
  const canMsg = can('messaging_alerts');

  const initials = (user?.display_name || user?.email || 'U').slice(0, 2).toUpperCase();

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_FILE) { toast.error(t('settings.photoHint')); return; }
    const reader = new FileReader();
    reader.onload = () => setAvatar(reader.result);
    reader.readAsDataURL(file);
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      await updateProfile({ ...profile, avatar: avatar || '' });
      toast.success(t('settings.profileSaved'));
    } catch (e) { toast.error(e?.response?.data?.detail?.message || t('auth.genericError')); }
    finally { setSaving(false); }
  };

  const saveAppearance = async () => {
    setSaving(true);
    try { await updateProfile({ locale: language, currency }); toast.success(t('settings.saved')); }
    catch (e) { toast.error(t('auth.genericError')); }
    finally { setSaving(false); }
  };

  const saveAlerts = async () => {
    setSaving(true);
    try {
      await updateProfile({ default_alert_prefs: prefs, telegram_chat_id: channels.telegram_chat_id, webhook_url: channels.webhook_url });
      toast.success(t('settings.saved'));
    } catch (e) { toast.error(t('auth.genericError')); }
    finally { setSaving(false); }
  };

  const themeOptions = [
    { key: 'light', label: t('settings.themeLight'), icon: Sun },
    { key: 'dark', label: t('settings.themeDark'), icon: Moon },
    { key: 'system', label: t('settings.themeSystem'), icon: Monitor },
  ];

  return (
    <div data-testid="settings-page" className="max-w-3xl">
      <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('settings.title')}</h1>
      <p className="mt-1 text-[var(--dz-muted)]">{t('settings.subtitle')}</p>

      <Tabs defaultValue="profile" className="mt-6">
        <TabsList data-testid="settings-tabs" className="flex-wrap h-auto">
          <TabsTrigger value="profile" data-testid="settings-tab-profile">{t('settings.tabProfile')}</TabsTrigger>
          <TabsTrigger value="appearance" data-testid="settings-tab-appearance">{t('settings.tabAppearance')}</TabsTrigger>
          <TabsTrigger value="alerts" data-testid="settings-tab-alerts">{t('settings.tabPrefs')}</TabsTrigger>
          <TabsTrigger value="subscription" data-testid="settings-tab-subscription">{t('settings.tabSubscription')}</TabsTrigger>
        </TabsList>

        {/* PROFILE */}
        <TabsContent value="profile">
          <Card className="p-6 border-[var(--dz-border)]">
            <div className="flex items-center gap-5">
              <Avatar className="h-20 w-20">
                {avatar ? <AvatarImage src={avatar} alt="avatar" data-testid="settings-avatar-image" /> : null}
                <AvatarFallback className="bg-[var(--dz-primary)] text-white text-xl">{initials}</AvatarFallback>
              </Avatar>
              <div>
                <p className="font-medium">{t('settings.photo')}</p>
                <p className="text-xs text-[var(--dz-muted)]">{t('settings.photoHint')}</p>
                <div className="mt-2 flex gap-2">
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} data-testid="settings-avatar-input" />
                  <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} data-testid="settings-avatar-upload-button" className="border-[var(--dz-border)]">
                    <Camera size={14} className="mr-1.5" /> {t('settings.uploadPhoto')}
                  </Button>
                  {avatar && (
                    <Button size="sm" variant="ghost" onClick={() => setAvatar(null)} data-testid="settings-avatar-remove-button" className="text-[var(--dz-muted)]">
                      <Trash2 size={14} className="mr-1.5" /> {t('settings.removePhoto')}
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="dn">{t('settings.displayName')}</Label>
                <Input id="dn" value={profile.display_name} maxLength={80} onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} data-testid="settings-displayname-input" className="mt-1.5" />
              </div>
              <div>
                <Label htmlFor="country">{t('settings.country')}</Label>
                <Input id="country" value={profile.country} maxLength={60} onChange={(e) => setProfile({ ...profile, country: e.target.value })} data-testid="settings-country-input" className="mt-1.5" />
              </div>
              <div>
                <Label htmlFor="phone">{t('settings.phone')}</Label>
                <Input id="phone" value={profile.phone} maxLength={30} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} data-testid="settings-phone-input" className="mt-1.5" />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="bio">{t('settings.bio')}</Label>
                <Textarea id="bio" value={profile.bio} maxLength={280} onChange={(e) => setProfile({ ...profile, bio: e.target.value })} data-testid="settings-bio-input" className="mt-1.5" rows={3} />
              </div>
            </div>
            <div className="mt-5">
              <Button onClick={saveProfile} disabled={saving} data-testid="settings-save-profile-button" className="bg-[var(--dz-primary)] text-white">
                <Check size={16} className="mr-1.5" /> {saving ? t('common.saving') : t('common.save')}
              </Button>
            </div>
          </Card>
        </TabsContent>

        {/* APPEARANCE */}
        <TabsContent value="appearance">
          <Card className="p-6 border-[var(--dz-border)] space-y-6">
            <div>
              <p className="font-medium">{t('settings.theme')}</p>
              <p className="text-sm text-[var(--dz-muted)]">{t('settings.themeDesc')}</p>
              <div className="mt-3 grid grid-cols-3 gap-3 max-w-md">
                {themeOptions.map((o) => (
                  <button key={o.key} onClick={() => setTheme(o.key)} data-testid={`settings-theme-${o.key}`}
                    className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition-colors ${theme === o.key ? 'border-[var(--dz-mint)] bg-[var(--dz-mint-10)]' : 'border-[var(--dz-border)] hover:bg-[var(--dz-primary-8)]'}`}>
                    <o.icon size={20} className={theme === o.key ? 'text-[var(--dz-buy-deep)]' : 'text-[var(--dz-muted)]'} />
                    <span className="text-sm">{o.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-[var(--dz-border)] pt-6">
              <div>
                <Label>{t('settings.language')}</Label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger className="mt-1.5" data-testid="settings-language-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{LANGS.map((l) => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label>{t('settings.currency')}</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="mt-1.5" data-testid="settings-currency-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{['USD', 'CAD', 'BRL', 'EUR'].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Button onClick={saveAppearance} disabled={saving} data-testid="settings-save-appearance-button" className="bg-[var(--dz-primary)] text-white">{saving ? t('common.saving') : t('common.save')}</Button>
            </div>
          </Card>
        </TabsContent>

        {/* ALERTS */}
        <TabsContent value="alerts">
          <Card className="p-6 border-[var(--dz-border)] space-y-5">
            <p className="font-heading font-semibold">{t('settings.alertPrefs')}</p>
            <div className="flex items-center justify-between gap-4">
              <div><p className="font-medium">{t('settings.alertEmail')}</p><p className="text-sm text-[var(--dz-muted)]">{t('settings.alertEmailDesc')}</p></div>
              <Switch checked={!!prefs.email} onCheckedChange={(v) => setPrefs({ ...prefs, email: v })} data-testid="settings-email-switch" />
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-[var(--dz-border)] pt-5">
              <div><p className="font-medium">{t('settings.alertInApp')}</p><p className="text-sm text-[var(--dz-muted)]">{t('settings.alertInAppDesc')}</p></div>
              <Switch checked={!!prefs.in_app} onCheckedChange={(v) => setPrefs({ ...prefs, in_app: v })} data-testid="settings-inapp-switch" />
            </div>

            <div className="border-t border-[var(--dz-border)] pt-5">
              <div className="flex items-center gap-2">
                <p className="font-heading font-semibold">{t('settings.channels')}</p>
                {!canMsg && <span className="inline-flex items-center gap-1 text-xs text-[var(--dz-muted)] rounded-full bg-[var(--dz-primary-8)] px-2 py-0.5"><Lock size={11} /> {t('settings.lockedInvestor')}</span>}
              </div>
              <div className={`mt-4 space-y-4 ${!canMsg ? 'opacity-60 pointer-events-none' : ''}`}>
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1"><Label>{t('settings.telegram')}</Label><p className="text-sm text-[var(--dz-muted)]">{t('settings.telegramDesc')}</p></div>
                  <Switch checked={!!prefs.telegram} onCheckedChange={(v) => setPrefs({ ...prefs, telegram: v })} data-testid="settings-telegram-switch" disabled={!canMsg} />
                </div>
                <Input value={channels.telegram_chat_id} onChange={(e) => setChannels({ ...channels, telegram_chat_id: e.target.value })} placeholder={t('settings.telegramPh')} data-testid="settings-telegram-input" disabled={!canMsg} />
                <div className="flex items-center justify-between gap-4 border-t border-[var(--dz-border)] pt-4">
                  <div className="flex-1"><Label>{t('settings.webhook')}</Label><p className="text-sm text-[var(--dz-muted)]">{t('settings.webhookDesc')}</p></div>
                  <Switch checked={!!prefs.webhook} onCheckedChange={(v) => setPrefs({ ...prefs, webhook: v })} data-testid="settings-webhook-switch" disabled={!canMsg} />
                </div>
                <Input value={channels.webhook_url} onChange={(e) => setChannels({ ...channels, webhook_url: e.target.value })} placeholder={t('settings.webhookPh')} data-testid="settings-webhook-input" disabled={!canMsg} />
              </div>
            </div>
            <div>
              <Button onClick={saveAlerts} disabled={saving} data-testid="settings-save-alerts-button" className="bg-[var(--dz-primary)] text-white">{saving ? t('common.saving') : t('common.save')}</Button>
            </div>
          </Card>
        </TabsContent>

        {/* SUBSCRIPTION */}
        <TabsContent value="subscription">
          <Card className="p-6 border-[var(--dz-border)]">
            <p className="font-heading font-semibold">{t('settings.subscription')}</p>
            <div className="mt-3 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-[var(--dz-muted)]">{t('settings.currentPlan')}</p>
                <p className="font-heading font-bold text-xl">{t(`plans.${user?.plan || 'none'}`)}</p>
              </div>
              <Link to="/app/upgrade"><Button variant="outline" data-testid="settings-upgrade-button" className="border-[var(--dz-border)]"><Crown size={16} className="mr-2" />{t('nav.upgrade')}</Button></Link>
            </div>
            {user?.capabilities?.features?.length > 0 && (
              <ul className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-2">
                {user.capabilities.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-[var(--dz-muted)]"><Check size={14} className="text-[var(--dz-buy)]" /> {f}</li>
                ))}
              </ul>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
