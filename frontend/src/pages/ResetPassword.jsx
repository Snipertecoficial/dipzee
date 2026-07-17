import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { CheckCircle2, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { AuthLayout } from '../components/AuthLayout';
import api from '../lib/api';

export default function ResetPassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) { toast.error(t('auth.passwordMismatch')); return; }
    setLoading(true);
    try {
      await api.post('/auth/reset', { token, password });
      setDone(true);
      setTimeout(() => navigate('/login', { replace: true }), 2500);
    } catch (e) {
      toast.error(e?.response?.status === 400 ? t('auth.resetInvalidToken') : t('auth.genericError'));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout>
        <Card className="w-full p-8 text-center" data-testid="reset-password-no-token">
          <XCircle size={36} className="mx-auto text-[var(--dz-sell)]" />
          <h1 className="mt-3 font-heading font-bold text-2xl">{t('auth.resetInvalidToken')}</h1>
          <Link to="/forgot-password" className="mt-6 inline-block text-sm text-[var(--dz-primary)] font-medium">{t('auth.forgotCta')}</Link>
        </Card>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <Card className="w-full p-8">
        {done ? (
          <div className="text-center" data-testid="reset-password-done">
            <CheckCircle2 size={36} className="mx-auto text-[var(--dz-buy)]" />
            <h1 className="mt-3 font-heading font-bold text-2xl">{t('auth.resetSuccessTitle')}</h1>
            <p className="mt-2 text-sm text-[var(--dz-muted)]">{t('auth.resetSuccessBody')}</p>
          </div>
        ) : (
          <>
            <h1 className="font-heading font-bold text-2xl">{t('auth.resetTitle')}</h1>
            <p className="mt-1 text-sm text-[var(--dz-muted)]">{t('auth.resetSubtitle')}</p>
            <form onSubmit={submit} data-testid="reset-password-form" className="mt-6 space-y-4">
              <div className="space-y-1.5">
                <Label>{t('auth.newPassword')}</Label>
                <Input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} data-testid="reset-password-input" />
              </div>
              <div className="space-y-1.5">
                <Label>{t('auth.confirmPassword')}</Label>
                <Input type="password" required minLength={6} value={confirm} onChange={(e) => setConfirm(e.target.value)} data-testid="reset-confirm-input" />
              </div>
              <Button type="submit" disabled={loading} data-testid="reset-submit-button" className="w-full bg-[var(--dz-primary)] text-white">
                {loading ? t('common.loading') : t('auth.resetCta')}
              </Button>
            </form>
          </>
        )}
      </Card>
    </AuthLayout>
  );
}
