import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Logo } from '../components/Logo';
import { LanguageSwitcher } from '../components/Switchers';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      const dest = location.state?.from?.pathname || '/app/dashboard';
      navigate(dest, { replace: true });
    } catch (err) {
      const status = err?.response?.status;
      toast.error(status === 401 ? t('auth.invalidCreds') : t('auth.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--dz-bg)] flex flex-col">
      <div className="h-16 px-4 sm:px-6 lg:px-8 flex items-center justify-between border-b border-[var(--dz-border)] bg-white">
        <Link to="/"><Logo /></Link>
        <LanguageSwitcher />
      </div>
      <div className="flex-1 flex items-center justify-center px-4 py-10">
        <Card className="w-full max-w-md p-8">
          <h1 className="font-heading font-bold text-2xl">{t('auth.loginTitle')}</h1>
          <p className="mt-1 text-sm text-[var(--dz-muted)]">{t('auth.loginSubtitle')}</p>
          <form onSubmit={submit} data-testid="login-form" className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label>{t('auth.email')}</Label>
              <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input" />
            </div>
            <div className="space-y-1.5">
              <Label>{t('auth.password')}</Label>
              <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input" />
            </div>
            <Button type="submit" disabled={loading} data-testid="auth-submit-button" className="w-full bg-[var(--dz-primary)] text-white">
              {loading ? t('common.loading') : t('auth.loginCta')}
            </Button>
          </form>
          <p className="mt-5 text-sm text-center text-[var(--dz-muted)]">
            {t('auth.noAccount')} <Link to="/register" className="text-[var(--dz-primary)] font-medium">{t('auth.signupLink')}</Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
