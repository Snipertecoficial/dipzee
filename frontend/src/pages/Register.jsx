import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AuthLayout } from '../components/AuthLayout';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const { t, i18n } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState(location.state?.email || '');
  const [password, setPassword] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [loading, setLoading] = useState(false);
  const locale = i18n.language?.slice(0, 2) || 'en';

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register({ email, password, locale, currency });
      navigate('/app/dashboard', { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === 'string' && detail.includes('registered') ? t('auth.emailTaken') : t('auth.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card className="w-full p-8">
          <h1 className="font-heading font-bold text-2xl">{t('auth.registerTitle')}</h1>
          <p className="mt-1 text-sm text-[var(--dz-muted)]">{t('auth.registerSubtitle')}</p>
          <form onSubmit={submit} data-testid="register-form" className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label>{t('auth.email')}</Label>
              <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="register-email-input" />
            </div>
            <div className="space-y-1.5">
              <Label>{t('auth.password')}</Label>
              <Input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} data-testid="register-password-input" />
              <p className="text-xs text-[var(--dz-muted)]">{t('auth.passwordHint')}</p>
            </div>
            <div className="space-y-1.5">
              <Label>{t('nav.currency')}</Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger data-testid="register-currency-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['CAD', 'USD', 'BRL'].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={loading} data-testid="auth-submit-button" className="w-full bg-[var(--dz-primary)] text-white">
              {loading ? t('common.loading') : t('auth.registerCta')}
            </Button>
          </form>
          <p className="mt-5 text-sm text-center text-[var(--dz-muted)]">
            {t('auth.haveAccount')} <Link to="/login" className="text-[var(--dz-primary)] font-medium">{t('auth.loginLink')}</Link>
          </p>
        </Card>
    </AuthLayout>
  );
}
