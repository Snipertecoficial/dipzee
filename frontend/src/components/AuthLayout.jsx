import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TrendingUp, Bell, Wallet, ShieldCheck } from 'lucide-react';
import { Logo } from './Logo';
import { LanguageSwitcher } from './Switchers';
import { SIGNAL_COLORS } from '../lib/format';
import api from '../lib/api';

export function AuthLayout({ children }) {
  const { t } = useTranslation();
  const [ops, setOps] = useState([]);

  useEffect(() => {
    api.get('/public/top-opportunities', { params: { limit: 4 } })
      .then(({ data }) => setOps(data.results || []))
      .catch(() => {});
  }, []);

  const perks = [
    { icon: TrendingUp, text: t('landing.feature1Title') },
    { icon: Bell, text: t('landing.feature2Title') },
    { icon: Wallet, text: t('landing.feature4Title') },
  ];

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[var(--dz-bg)]">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-10 xl:p-14 bg-[var(--dz-primary)] text-white relative overflow-hidden">
        <div className="relative z-10">
          <Logo dark />
          <h2 className="mt-12 font-heading font-bold text-3xl xl:text-4xl leading-tight max-w-md">{t('landing.heroTitle')}</h2>
          <p className="mt-4 text-[rgba(255,255,255,0.75)] max-w-md">{t('landing.heroSubtitle')}</p>
          <ul className="mt-8 space-y-3">
            {perks.map((p, i) => (
              <li key={i} className="flex items-center gap-3 text-sm">
                <span className="h-8 w-8 rounded-lg bg-[rgba(22,224,163,0.18)] text-[var(--dz-mint)] flex items-center justify-center"><p.icon size={16} /></span>
                {p.text}
              </li>
            ))}
          </ul>
        </div>

        {/* Live opportunities preview */}
        {ops.length > 0 && (
          <div className="relative z-10 mt-10">
            <p className="text-xs uppercase tracking-wide text-[rgba(255,255,255,0.6)] mb-3">{t('landing.topTitle')}</p>
            <div className="grid grid-cols-2 gap-3 max-w-md">
              {ops.map((a) => (
                <div key={a.ticker} className="rounded-xl bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.12)] p-3 flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="font-semibold text-sm truncate">{a.ticker}</p>
                    <p className="text-[10px] text-[rgba(255,255,255,0.6)] truncate">{a.name}</p>
                  </div>
                  <div className="h-9 w-9 shrink-0 rounded-full flex items-center justify-center text-sm font-bold tnum" style={{ border: `2px solid ${SIGNAL_COLORS[a.classification] || '#fff'}` }}>{a.score}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="relative z-10 flex items-center gap-2 text-xs text-[rgba(255,255,255,0.6)] mt-8">
          <ShieldCheck size={14} /> {t('landing.emailPrivacy')}
        </div>
        <div className="absolute -right-24 -bottom-24 h-80 w-80 rounded-full bg-[var(--dz-mint)] opacity-10 blur-2xl" />
      </div>

      {/* Right form area */}
      <div className="flex flex-col">
        <div className="h-16 px-4 sm:px-6 flex items-center justify-between border-b border-[var(--dz-border)] bg-white lg:bg-transparent lg:border-0">
          <Link to="/" className="lg:hidden"><Logo /></Link>
          <div className="ml-auto"><LanguageSwitcher /></div>
        </div>
        <div className="flex-1 flex items-center justify-center px-4 py-8">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </div>
    </div>
  );
}
