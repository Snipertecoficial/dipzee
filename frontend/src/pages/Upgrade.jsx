import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '../context/AuthContext';

const BASE_PRICES = { free: 0, pro: 12.99, investor: 24.99 };

export function PricingCards({ onChoose }) {
  const { t } = useTranslation();
  const { user } = useAuth() || {};
  const [billing, setBilling] = useState('monthly');

  const plans = [
    { id: 'free', features: ['freeF1', 'freeF2', 'freeF3', 'freeF4'], popular: false },
    { id: 'pro', features: ['proF1', 'proF2', 'proF3', 'proF4', 'proF5'], popular: true },
    { id: 'investor', features: ['investorF1', 'investorF2', 'investorF3', 'investorF4', 'investorF5'], popular: false },
  ];

  const priceFor = (id) => {
    if (id === 'free') return { amount: 0, suffix: '' };
    const monthly = BASE_PRICES[id];
    if (billing === 'annual') {
      const yearly = monthly * 12 * 0.8;
      return { amount: yearly.toFixed(2), suffix: t('plans.perYear') };
    }
    return { amount: monthly.toFixed(2), suffix: t('plans.perMonth') };
  };

  const choose = (id) => {
    if (onChoose) return onChoose(id);
    toast.info(t('plans.comingSoon'));
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
          return (
            <Card key={p.id} data-testid="pricing-plan-card" className={`p-6 flex flex-col ${p.popular ? 'border-[var(--dz-mint)] border-2 shadow-[var(--dz-elev-2)]' : ''}`}>
              {p.popular && <span className="self-start text-[11px] rounded-full px-2 py-0.5 bg-[rgba(22,224,163,0.18)] text-[var(--dz-buy-deep)] mb-2">{t('plans.mostPopular')}</span>}
              <h3 className="font-heading font-bold text-xl">{t(`plans.${p.id}`)}</h3>
              <p className="text-sm text-[var(--dz-muted)] mt-1">{t(`plans.${p.id}Desc`)}</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="font-heading font-bold text-3xl tnum">CAD ${price.amount}</span>
                <span className="text-sm text-[var(--dz-muted)]">{price.suffix}</span>
              </div>
              <ul className="mt-5 space-y-2 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm"><Check size={16} className="text-[var(--dz-buy)] mt-0.5 shrink-0" />{t(`plans.${f}`)}</li>
                ))}
              </ul>
              <Button data-testid="pricing-upgrade-button" onClick={() => choose(p.id)} disabled={isCurrent}
                className={`mt-6 ${p.popular ? 'bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95' : 'bg-[var(--dz-primary)] text-white'}`}>
                {isCurrent ? t('plans.current') : t('plans.choose', { plan: t(`plans.${p.id}`) })}
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
  return (
    <div>
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="font-heading font-bold text-2xl sm:text-3xl">{t('plans.upgradeTitle')}</h1>
        <p className="mt-2 text-[var(--dz-muted)]">{t('plans.upgradeSubtitle')}</p>
      </div>
      <div className="mt-8"><PricingCards /></div>
    </div>
  );
}
