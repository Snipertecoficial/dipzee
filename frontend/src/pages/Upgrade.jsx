import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Check, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

const BASE_PRICES = { free: 0, pro: 12.99, investor: 24.99 };

export function PricingCards({ onChoose, busyPlan }) {
  const { t } = useTranslation();
  const { user } = useAuth() || {};
  const [billing, setBilling] = useState('monthly');

  const plans = [
    { id: 'free', features: ['freeF1', 'freeF2', 'freeF3', 'freeF4'], popular: false },
    { id: 'pro', features: ['proF1', 'proF2', 'proF3', 'proF4', 'proF5'], popular: true },
    { id: 'investor', features: ['investorF1', 'investorF2', 'investorF3', 'investorF4', 'investorF5'], popular: false },
  ];

  const priceFor = (id) => {
    if (id === 'free') return { amount: '0.00', suffix: '' };
    const monthly = BASE_PRICES[id];
    if (billing === 'annual') return { amount: (monthly * 12 * 0.8).toFixed(2), suffix: t('plans.perYear') };
    return { amount: monthly.toFixed(2), suffix: t('plans.perMonth') };
  };

  return (
    <div>
      <div className="flex justify-center mb-8">
        <Tabs value={billing} onValueChange={setBilling}>
          <TabsList data-testid="pricing-billing-toggle">
            <TabsTrigger value="monthly">{t('plans.monthly')}</TabsTrigger>
            <TabsTrigger value="annual">{t('plans.annual')} · {t('plans.annualSave')}</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {plans.map((p) => {
          const price = priceFor(p.id);
          const isCurrent = (user?.plan || 'free') === p.id;
          const busy = busyPlan === p.id;
          return (
            <Card key={p.id} data-testid="pricing-plan-card" className={`p-6 flex flex-col ${p.popular ? 'border-[var(--dz-mint)] border-2 shadow-[var(--dz-elev-2)]' : ''}`}>
              {p.popular && <span className="self-start text-[11px] rounded-full px-2 py-0.5 bg-[rgba(22,224,163,0.18)] text-[var(--dz-buy-deep)] mb-2">{t('plans.mostPopular')}</span>}
              <h3 className="font-heading font-bold text-xl">{t(`plans.${p.id}`)}</h3>
              <p className="text-sm text-[var(--dz-muted)] mt-1">{t(`plans.${p.id}Desc`)}</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="font-heading font-bold text-3xl tnum">US${price.amount}</span>
                <span className="text-sm text-[var(--dz-muted)]">{price.suffix}</span>
              </div>
              <ul className="mt-5 space-y-2 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm"><Check size={16} className="text-[var(--dz-buy)] mt-0.5 shrink-0" />{t(`plans.${f}`)}</li>
                ))}
              </ul>
              <Button data-testid="pricing-upgrade-button" onClick={() => onChoose && onChoose(p.id, billing)} disabled={isCurrent || p.id === 'free' || busy}
                className={`mt-6 ${p.popular ? 'bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95' : 'bg-[var(--dz-primary)] text-white'}`}>
                {busy ? <Loader2 size={16} className="animate-spin" /> : isCurrent ? t('plans.current') : t('plans.choose', { plan: t(`plans.${p.id}`) })}
              </Button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default function Upgrade() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const [params, setParams] = useSearchParams();
  const [busyPlan, setBusyPlan] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const startCheckout = async (plan, billing) => {
    if (plan === 'free') return;
    setBusyPlan(plan);
    try {
      const { data } = await api.post('/billing/checkout', {
        package_id: `${plan}_${billing}`,
        origin_url: window.location.origin,
      });
      if (data.url) { window.location.href = data.url; }
    } catch (e) {
      const status = e?.response?.status;
      toast.error(status === 503 ? t('plans.comingSoon') : t('auth.genericError'));
      setBusyPlan(null);
    }
  };

  const pollStatus = useCallback(async (sessionId, attempts = 0) => {
    if (attempts >= 6) { setVerifying(false); toast.error(t('auth.genericError')); return; }
    try {
      const { data } = await api.get(`/billing/status/${sessionId}`);
      if (data.payment_status === 'paid') {
        setVerifying(false);
        if (setUser && user) setUser({ ...user, plan: data.plan });
        toast.success('Upgrade complete \u2014 ' + t(`plans.${data.plan}`));
        setParams({}, { replace: true });
        return;
      }
      if (data.status === 'expired') { setVerifying(false); toast.error(t('auth.genericError')); return; }
      setTimeout(() => pollStatus(sessionId, attempts + 1), 2000);
    } catch (e) {
      setVerifying(false);
    }
  }, [setParams, setUser, user, t]);

  useEffect(() => {
    const sessionId = params.get('session_id');
    if (sessionId) { setVerifying(true); pollStatus(sessionId); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('plans.upgradeTitle')}</h1>
        <p className="mt-2 text-[var(--dz-muted)]">{t('plans.upgradeSubtitle')}</p>
      </div>
      {verifying && (
        <div className="mt-4 flex items-center justify-center gap-2 text-[var(--dz-muted)]">
          <Loader2 size={16} className="animate-spin" /> {t('common.loading')}
        </div>
      )}
      <div className="mt-8"><PricingCards onChoose={startCheckout} busyPlan={busyPlan} /></div>
    </div>
  );
}
