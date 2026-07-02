import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Lock, Crown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '../context/AuthContext';

export function FeatureGate({ feature, title, children }) {
  const { can } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  if (can(feature)) return children;
  return (
    <Card data-testid={`feature-gate-${feature}`} className="p-10 text-center border-dashed border-[var(--dz-border)] bg-[var(--dz-surface)]">
      <div className="mx-auto h-12 w-12 rounded-full bg-[var(--dz-mint-16)] text-[var(--dz-buy-deep)] flex items-center justify-center">
        <Lock size={22} />
      </div>
      <h3 className="mt-4 font-heading font-semibold text-lg">{title || t('gate.lockedTitle')}</h3>
      <p className="mt-2 text-sm text-[var(--dz-muted)] max-w-md mx-auto">{t('gate.lockedDesc')}</p>
      <Button onClick={() => navigate('/app/upgrade')} data-testid="feature-gate-upgrade-button" className="mt-5 bg-[var(--dz-primary)] text-white">
        <Crown size={16} className="mr-2" /> {t('gate.cta')}
      </Button>
    </Card>
  );
}
