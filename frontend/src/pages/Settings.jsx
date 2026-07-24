import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Crown, Camera, Trash2, Check, Sun, Moon, Monitor, Lock, Loader2, ExternalLink, CalendarClock, Download, ShieldAlert, KeyRound, LogOut } from 'lucide-react';
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
import api from '../lib/api';

const LANGS = [{ code: 'en', label: 'English' }, { code: 'fr', label: 'Fran\u00e7ais' }, { code: 'pt', label: 'Portugu\u00eas' }, { code: 'es', label: 'Espa\u00f1ol' }];
const MAX_FILE = 1_100_000; // ~1MB source -> ~1.4MB base64

export default function Settings() {
  const { t } = useTranslation();
  const { user, updateProfile, can, logout, logoutAllDevices, changePassword } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
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
  const [notifConfig, setNotifConfig] = useState({ telegram_configured: true, news_available: true });
  const [tgTestBusy, setTgTestBusy] = useState(false);
  const [sub, setSub] = useState(null);
  const [portalBusy, setPortalBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' });
  const [pwBusy, setPwBusy] = useState(false);
  const [logoutAllBusy, setLogoutAllBusy] = useState(false);

  const isPaid = ['starter', 'pro', 'investor'].includes(user?.plan);

  useEffect(() => {
    let alive = true;
    api.get('/billing/subscription')
      .then(({ data }) => { if (alive) setSub(data); })
      .catch(() => { if (alive) setSub({}); });
    api.get('/notifications/config')
      .then(({ data }) => { if (alive && data) setNotifConfig(data); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const testTelegram = async () => {
    setTgTestBusy(true);
    try {
      await api.post('/notifications/telegram/test');
      toast.success(t('settings.telegramTestOk'));
    } catch (e) {
      toast.error(e?.response?.data?.detail?.message || t('settings.telegramTestFail'));
    } finally {
      setTgTestBusy(false);
    }
  };

  const openPortal = async () => {
    setPortalBusy(true);
    try {
      const { data } = await api.post('/billing/portal', { origin_url: window.location.origin });
      if (data.url) { window.location.href = data.url; }
    } catch (e) {
      toast.error(e?.response?.status === 400 ? t('settings.noBillingAccount') : t('auth.genericError'));
      setPortalBusy(false);
    }
  };

  const doCancel = async () => {
    if (!window.confirm(t('settings.cancelConfirm'))) return;
    setCancelBusy(true);
    try {
      const { data } = await api.post('/billing/cancel');
      setSub(data);
      toast.success(t('settings.cancelSuccessToast'));
    } catch (e) { toast.error(t('auth.genericError')); }
    finally { setCancelBusy(false); }
  };

  const doReactivate = async () => {
    setCancelBusy(true);
    try {
      const { data } = await api.post('/billing/reactivate');
      setSub(data);
      toast.success(t('settings.reactivateSuccessToast'));
    } catch (e) { toast.error(t('auth.genericError')); }
    finally { setCancelBusy(false); }
  };

  const exportMyData = async () => {
    setExportBusy(true);
    try {
      const { data } = await api.get('/auth/me/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'dipzee-meus-dados.json'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(t('auth.genericError')); }
    finally { setExportBusy(false); }
  };

  const deleteAccount = async () => {
    if (!window.confirm(t('settings.deleteAccountConfirm'))) return;
    if (window.prompt(t('settings.deleteAccountPromptType')) !== t('settings.deleteAccountPromptWord')) return;
    setDeleteBusy(true);
    try {
      await api.delete('/auth/me');
      toast.success(t('settings.deleteAccountSuccessToast'));
      logout();
      navigate('/', { replace: true });
    } catch (e) {
      toast.error(e?.response?.data?.detail || t('auth.genericError'));
      setDeleteBusy(false);
    }
  };

  const doChangePassword = async (e) => {
    e.preventDefault();
    if (pwForm.next !== pwForm.confirm) { toast.error(t('auth.passwordMismatch')); return; }
    setPwBusy(true);
    try {
      await changePassword(pwForm.current, pwForm.next);
      setPwForm({ current: '', next: '', confirm: '' });
      toast.success(t('settings.passwordChangedToast'));
    } catch (e) {
      toast.error(e?.response?.status === 400 ? t('settings.currentPasswordWrong') : t('auth.genericError'));
    } finally { setPwBusy(false); }
  };

  const doLogoutAll = async () => {
    if (!window.confirm(t('settings.logoutAllConfirm'))) return;
    setLogoutAllBusy(true);
    try {
      await logoutAllDevices();
      navigate('/login', { replace: true });
    } catch (e) {
      toast.error(t('auth.genericError'));
      setLogoutAllBusy(false);
    }
  };

  const fmtDate = (iso) => {
    if (!iso) return '\u2014';
    try { return new Date(iso).toLocaleDateString(user?.locale || 'en', { year: 'numeric', month: 'short', day: 'numeric' }); }
    catch { return '\u2014'; }
  };

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

          <Card className="mt-6 p-6 border-[var(--dz-border)]" data-testid="settings-security-card">
            <div className="flex items-center gap-2">
              <KeyRound size={17} className="text-[var(--dz-primary)]" />
              <p className="font-heading font-semibold">{t('settings.security')}</p>
            </div>
            <form onSubmit={doChangePassword} className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl">
              <div className="space-y-1.5">
                <Label htmlFor="pw-current">{t('settings.currentPassword')}</Label>
                <Input id="pw-current" type="password" required value={pwForm.current} onChange={(e) => setPwForm({ ...pwForm, current: e.target.value })} data-testid="settings-current-password-input" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pw-next">{t('auth.newPassword')}</Label>
                <Input id="pw-next" type="password" required minLength={6} value={pwForm.next} onChange={(e) => setPwForm({ ...pwForm, next: e.target.value })} data-testid="settings-new-password-input" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pw-confirm">{t('auth.confirmPassword')}</Label>
                <Input id="pw-confirm" type="password" required minLength={6} value={pwForm.confirm} onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })} data-testid="settings-confirm-password-input" />
              </div>
              <div className="sm:col-span-3">
                <Button type="submit" disabled={pwBusy} data-testid="settings-change-password-button" className="bg-[var(--dz-primary)] text-white">
                  {pwBusy ? <Loader2 size={16} className="mr-2 animate-spin" /> : <KeyRound size={16} className="mr-2" />}
                  {t('settings.changePassword')}
                </Button>
              </div>
            </form>
            <div className="mt-5 border-t border-[var(--dz-border)] pt-4">
              <p className="text-sm text-[var(--dz-muted)]">{t('settings.logoutAllDesc')}</p>
              <Button variant="outline" size="sm" onClick={doLogoutAll} disabled={logoutAllBusy} data-testid="settings-logout-all-button" className="mt-2 border-[var(--dz-border)]">
                {logoutAllBusy ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <LogOut size={14} className="mr-1.5" />}
                {t('settings.logoutAll')}
              </Button>
            </div>
          </Card>

          <Card className="mt-6 p-6 border-[var(--dz-border)]" data-testid="settings-my-data-card">
            <p className="font-heading font-semibold">{t('settings.myData')}</p>
            <p className="text-sm text-[var(--dz-muted)] mt-1">{t('settings.myDataDesc')}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button variant="outline" onClick={exportMyData} disabled={exportBusy} data-testid="settings-export-data-button" className="border-[var(--dz-border)]">
                {exportBusy ? <Loader2 size={15} className="mr-2 animate-spin" /> : <Download size={15} className="mr-2" />}
                {t('settings.exportData')}
              </Button>
            </div>

            {user?.role !== 'superadmin' && (
              <div className="mt-6 border-t border-[var(--dz-border)] pt-5">
                <div className="flex items-center gap-2 text-[var(--dz-sell)]">
                  <ShieldAlert size={16} />
                  <p className="font-medium text-sm">{t('settings.dangerZone')}</p>
                </div>
                <p className="text-xs text-[var(--dz-muted)] mt-1 max-w-lg">{t('settings.deleteAccountDesc')}</p>
                <Button variant="ghost" size="sm" onClick={deleteAccount} disabled={deleteBusy} data-testid="settings-delete-account-button" className="mt-3 text-[var(--dz-sell)] hover:text-[var(--dz-sell)] hover:bg-[rgba(229,72,77,0.08)]">
                  {deleteBusy ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <Trash2 size={14} className="mr-1.5" />}
                  {t('settings.deleteAccount')}
                </Button>
              </div>
            )}
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
                  <Switch checked={!!prefs.telegram} onCheckedChange={(v) => setPrefs({ ...prefs, telegram: v })} data-testid="settings-telegram-switch" disabled={!canMsg || !notifConfig.telegram_configured} />
                </div>
                {canMsg && !notifConfig.telegram_configured && (
                  <p className="text-xs text-[var(--dz-hold)] flex items-center gap-1.5"><ShieldAlert size={13} /> {t('settings.telegramUnavailable')}</p>
                )}
                <Input value={channels.telegram_chat_id} onChange={(e) => setChannels({ ...channels, telegram_chat_id: e.target.value })} placeholder={t('settings.telegramPh')} data-testid="settings-telegram-input" disabled={!canMsg || !notifConfig.telegram_configured} />
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <a href="https://t.me/userinfobot" target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--dz-primary)] inline-flex items-center gap-1 hover:underline">
                    {t('settings.telegramHelp')} <ExternalLink size={11} />
                  </a>
                  <Button
                    type="button" variant="outline" size="sm"
                    onClick={testTelegram}
                    disabled={!canMsg || !notifConfig.telegram_configured || !channels.telegram_chat_id || tgTestBusy}
                    data-testid="settings-telegram-test-button"
                    className="h-8 text-xs border-[var(--dz-border)]"
                  >
                    {tgTestBusy ? <Loader2 size={13} className="animate-spin mr-1.5" /> : null}{t('settings.telegramTest')}
                  </Button>
                </div>
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
            <div className="mt-3 flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="text-sm text-[var(--dz-muted)]">{t('settings.currentPlan')}</p>
                <div className="flex items-center gap-2">
                  <p className="font-heading font-bold text-xl" data-testid="settings-current-plan">{t(`plans.${user?.plan || 'none'}`)}</p>
                  {sub?.subscription_status && (
                    <span
                      data-testid="settings-subscription-status"
                      className="inline-flex items-center gap-1 text-[11px] rounded-full px-2 py-0.5 font-medium bg-[var(--dz-mint-16)] text-[var(--dz-buy-deep)]"
                    >
                      {t(`settings.subStatus.${sub.subscription_status}`, sub.subscription_status)}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {isPaid && sub?.has_subscription ? (
                  <>
                    <Link to="/app/upgrade"><Button variant="outline" data-testid="settings-change-plan-button" className="border-[var(--dz-border)]"><Crown size={16} className="mr-2" />{t('settings.changePlan')}</Button></Link>
                    <Button onClick={openPortal} disabled={portalBusy} variant="outline" data-testid="settings-manage-subscription-button" className="border-[var(--dz-border)]">
                      {portalBusy ? <Loader2 size={16} className="mr-2 animate-spin" /> : <ExternalLink size={16} className="mr-2" />}
                      {t('settings.manageSubscription')}
                    </Button>
                  </>
                ) : (
                  <Link to="/app/upgrade"><Button variant="outline" data-testid="settings-upgrade-button" className="border-[var(--dz-border)]"><Crown size={16} className="mr-2" />{t('nav.upgrade')}</Button></Link>
                )}
              </div>
            </div>

            {sub && (sub.trial_ends_at || sub.current_period_end) && (
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {sub.subscription_status === 'trialing' && sub.trial_ends_at && (
                  <div className="flex items-center gap-2 rounded-lg border border-[var(--dz-border)] bg-[var(--dz-surface)] p-3" data-testid="settings-trial-ends">
                    <CalendarClock size={16} className="text-[var(--dz-buy-deep)]" />
                    <div>
                      <p className="text-xs text-[var(--dz-muted)]">{t('settings.trialEndsOn')}</p>
                      <p className="font-medium tnum">{fmtDate(sub.trial_ends_at)}</p>
                    </div>
                  </div>
                )}
                {sub.current_period_end && (
                  <div className="flex items-center gap-2 rounded-lg border border-[var(--dz-border)] bg-[var(--dz-surface)] p-3" data-testid="settings-renews-on">
                    <CalendarClock size={16} className="text-[var(--dz-muted)]" />
                    <div>
                      <p className="text-xs text-[var(--dz-muted)]">{sub.cancel_at_period_end ? t('settings.endsOn') : t('settings.renewsOn')}</p>
                      <p className="font-medium tnum">{fmtDate(sub.current_period_end)}</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {isPaid && sub?.has_subscription && (
              <div className="mt-5 border-t border-[var(--dz-border)] pt-5">
                {sub.cancel_at_period_end ? (
                  <div className="flex items-center justify-between gap-4 flex-wrap rounded-lg border border-[var(--dz-sell)]/30 bg-[rgba(229,72,77,0.06)] p-4">
                    <p className="text-sm text-[var(--dz-fg)]">
                      {t('settings.willCancelOn', { date: fmtDate(sub.current_period_end) })}
                    </p>
                    <Button size="sm" onClick={doReactivate} disabled={cancelBusy} data-testid="settings-reactivate-button" className="bg-[var(--dz-primary)] text-white">
                      {cancelBusy ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : null}
                      {t('settings.reactivateSubscription')}
                    </Button>
                  </div>
                ) : (
                  <Button variant="ghost" size="sm" onClick={doCancel} disabled={cancelBusy} data-testid="settings-cancel-subscription-button" className="text-[var(--dz-sell)] hover:text-[var(--dz-sell)] hover:bg-[rgba(229,72,77,0.08)]">
                    {cancelBusy ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : null}
                    {t('settings.cancelSubscription')}
                  </Button>
                )}
              </div>
            )}

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
