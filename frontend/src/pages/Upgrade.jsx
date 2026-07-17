import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Check, Loader2, Sparkles, Crown, Rocket, ShieldCheck } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

const BASE_PRICES = { starter: 4.97, pro: 12.97, investor: 24.99 };

const PLAN_META = {
  starter: { icon: Rocket, features: ['starterF1', 'starterF2', 'starterF3', 'starterF4', 'starterF5'], accent: 'var(--dz-slate)' },
  pro: { icon: Sparkles, features: ['proF1', 'proF2', 'proF3', 'proF4', 'proF5', 'proF6'], accent: 'var(--dz-mint)', popular: true },
  investor: { icon: Crown, features: ['investorF1', 'investorF2', 'investorF3', 'investorF4', 'investorF5', 'investorF6', 'investorF7'], accent: 'var(--dz-primary)', premium: true },
};

export function PricingCards({ onChoose, busyPlan, hasActiveSub }) {
  const { t } = useTranslation();
  const { user } = useAuth() || {};
  const [billing, setBilling] = useState('monthly');

  const order = ['starter', 'pro', 'investor'];

  const priceFor = (id) => {
    const monthly = BASE_PRICES[id];
    if (billing === 'annual') return { amount: (monthly * 12 * 0.8).toFixed(2), suffix: t('plans.perYear') };
    return { amount: monthly.toFixed(2), suffix: t('plans.perMonth') };
  };

  return (
    <div>
      <div className="flex justify-center mb-8">
        <Tabs value={billing} onValueChange={setBilling}>
          <TabsList data-testid="pricing-billing-toggle">
            <TabsTrigger value="monthly" data-testid="pricing-billing-monthly">{t('plans.monthly')}</TabsTrigger>
            <TabsTrigger value="annual" data-testid="pricing-billing-annual">{t('plans.annual')} · {t('plans.annualSave')}</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto items-stretch">
        {order.map((id) => {
          const meta = PLAN_META[id];
          const Icon = meta.icon;
          const price = priceFor(id);
          const isCurrent = (user?.plan || 'free') === id;
          const busy = busyPlan === id;
          const border = meta.popular
            ? 'border-2 border-[var(--dz-mint)] shadow-[var(--dz-elev-2)]'
            : meta.premium
              ? 'border-2 border-[var(--dz-primary)] shadow-[var(--dz-elev-1)]'
              : 'border border-[var(--dz-border)]';
          return (
            <Card
              key={id}
              data-testid={`pricing-plan-${id}`}
              className={`relative p-6 flex flex-col bg-[var(--dz-surface)] rounded-[var(--dz-radius-lg,18px)] ${border} ${meta.popular ? 'md:-mt-2 md:mb-2' : ''}`}
            >
              {meta.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 text-[11px] font-semibold rounded-full px-3 py-1 bg-[var(--dz-mint)] text-[var(--dz-primary)] shadow-[var(--dz-elev-1)]">
                  <Sparkles size={12} /> {t('plans.mostPopular')}
                </span>
              )}
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center justify-center h-9 w-9 rounded-full" style={{ background: 'rgba(26,31,77,0.06)', color: meta.accent }}>
                  <Icon size={18} />
                </span>
                <div>
                  <h3 className="font-heading font-bold text-xl leading-none">{t(`plans.${id}`)}</h3>
                </div>
              </div>
              <p className="text-sm text-[var(--dz-muted)] mt-2">{t(`plans.${id}Desc`)}</p>

              <div className="mt-4 flex items-baseline gap-1">
                <span className="font-heading font-bold text-4xl tnum text-[var(--dz-fg)]">US${price.amount}</span>
                <span className="text-sm text-[var(--dz-muted)]">{price.suffix}</span>
              </div>
              <span className="mt-2 self-start inline-flex items-center gap-1 text-[11px] rounded-full px-2 py-0.5 bg-[rgba(22,224,163,0.16)] text-[var(--dz-buy-deep)] font-medium">
                {t('plans.trialBadge')}
              </span>
              <p className="mt-1 text-[11px] text-[var(--dz-muted)] leading-snug">{t('plans.trialNote')}</p>

              <ul className="mt-5 space-y-2.5 flex-1">
                {meta.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-[var(--dz-fg)]">
                    <Check size={16} className="text-[var(--dz-buy)] mt-0.5 shrink-0" />
                    <span className="leading-snug">{t(`plans.${f}`)}</span>
                  </li>
                ))}
              </ul>

              <Button
                data-testid={`pricing-upgrade-${id}-button`}
                onClick={() => onChoose && onChoose(id, billing)}
                disabled={isCurrent || busy}
                className={`mt-6 h-11 whitespace-normal ${meta.popular
                  ? 'bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-[0.97]'
                  : 'bg-[var(--dz-primary)] text-white hover:brightness-[1.06]'} active:scale-[0.98] transition-[transform,filter]`}
              >
                {busy ? <Loader2 size={16} className="animate-spin" /> : isCurrent ? t('plans.current') : hasActiveSub ? t('plans.changePlan') : t('plans.startTrial')}
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

  // A user who already has a live Stripe subscription must never go through
  // Checkout again — that would start a second, independent subscription and
  // double-bill them. Existing subscribers switch tiers in place instead.
  const hasActiveSub = ['starter', 'pro', 'investor'].includes(user?.plan) && !!user?.stripe_subscription_id;

  const startCheckout = async (plan, billing) => {
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

  const changePlan = async (plan, billing) => {
    setBusyPlan(plan);
    try {
      const { data } = await api.post('/billing/change-plan', { package_id: `${plan}_${billing}` });
      if (setUser && user) setUser({ ...user, plan: data.plan });
      toast.success(t('plans.planChangedToast', { plan: t(`plans.${plan}`) }));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t('auth.genericError'));
    } finally {
      setBusyPlan(null);
    }
  };

  const onChoose = (plan, billing) => (hasActiveSub ? changePlan(plan, billing) : startCheckout(plan, billing));

  const pollStatus = useCallback(async (sessionId, attempts = 0) => {
    if (attempts >= 8) { setVerifying(false); toast.error(t('auth.genericError')); return; }
    try {
      const { data } = await api.get(`/billing/status/${sessionId}`);
      // Trial subscriptions complete without an immediate charge, so success is
      // driven by the subscription being active/trialing (data.active).
      if (data.active) {
        setVerifying(false);
        if (setUser && user) setUser({ ...user, plan: data.plan });
        toast.success(t('plans.trialStartedToast', { plan: t(`plans.${data.plan}`) }));
        setParams({}, { replace: true });
        return;
      }
      if (data.session_status === 'expired') { setVerifying(false); toast.error(t('auth.genericError')); return; }
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
    <div className="max-w-5xl mx-auto">
      {!['starter', 'pro', 'investor'].includes(user?.plan) && (
        <div data-testid="onboarding-notice" className="mb-8 flex items-start gap-3 rounded-[var(--dz-radius-md,14px)] border border-[var(--dz-mint)] bg-[var(--dz-mint-10)] p-4">
          <Sparkles size={18} className="text-[var(--dz-buy-deep)] mt-0.5 shrink-0" />
          <div>
            <p className="font-heading font-semibold text-[var(--dz-fg)]">{t('plans.onboardingTitle')}</p>
            <p className="text-sm text-[var(--dz-muted)] mt-0.5">{t('plans.onboardingNotice')}</p>
          </div>
        </div>
      )}
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl tracking-tight" data-testid="upgrade-title">{t('plans.upgradeTitle')}</h1>
        <p className="mt-2 text-[var(--dz-muted)]">{t('plans.upgradeSubtitle')}</p>
      </div>
      {verifying && (
        <div className="mt-4 flex items-center justify-center gap-2 text-[var(--dz-muted)]">
          <Loader2 size={16} className="animate-spin" /> {t('common.loading')}
        </div>
      )}
      <div className="mt-8"><PricingCards onChoose={onChoose} busyPlan={busyPlan} hasActiveSub={hasActiveSub} /></div>
      <div className="mt-8 flex items-center justify-center gap-2 text-xs text-[var(--dz-muted)]">
        <ShieldCheck size={14} className="text-[var(--dz-buy)]" /> {t('plans.trialNote')}
      </div>
    </div>
  );
}
