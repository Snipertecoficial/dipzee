import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { MailCheck } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { AuthLayout } from '../components/AuthLayout';
import { Seo } from '../components/Seo';
import api from '../lib/api';

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/auth/forgot', { email, origin_url: window.location.origin });
      setSent(true);
    } catch (e) {
      toast.error(t('auth.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Seo title={t('auth.forgotTitle')} path="/forgot-password" noindex />
      <Card className="w-full p-8">
        {sent ? (
          <div className="text-center" data-testid="forgot-password-sent">
            <MailCheck size={36} className="mx-auto text-[var(--dz-buy)]" />
            <h1 className="mt-3 font-heading font-bold text-2xl">{t('auth.forgotSentTitle')}</h1>
            <p className="mt-2 text-sm text-[var(--dz-muted)]">{t('auth.forgotSentBody')}</p>
            <Link to="/login" className="mt-6 inline-block text-sm text-[var(--dz-primary)] font-medium">{t('auth.backToLogin')}</Link>
          </div>
        ) : (
          <>
            <h1 className="font-heading font-bold text-2xl">{t('auth.forgotTitle')}</h1>
            <p className="mt-1 text-sm text-[var(--dz-muted)]">{t('auth.forgotSubtitle')}</p>
            <form onSubmit={submit} data-testid="forgot-password-form" className="mt-6 space-y-4">
              <div className="space-y-1.5">
                <Label>{t('auth.email')}</Label>
                <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="forgot-email-input" />
              </div>
              <Button type="submit" disabled={loading} data-testid="forgot-submit-button" className="w-full bg-[var(--dz-primary)] text-white">
                {loading ? t('common.loading') : t('auth.forgotCta')}
              </Button>
            </form>
            <p className="mt-5 text-sm text-center text-[var(--dz-muted)]">
              <Link to="/login" className="text-[var(--dz-primary)] font-medium">{t('auth.backToLogin')}</Link>
            </p>
          </>
        )}
      </Card>
    </AuthLayout>
  );
}
