import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Search, Bell, ListChecks, Coins, Globe, Wallet, Check, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Logo } from '../components/Logo';
import { LanguageSwitcher } from '../components/Switchers';
import { ScoreDial } from '../components/ScoreDial';
import { RangeGauge52w } from '../components/RangeGauge';
import { SignalBadge } from '../components/SignalBadge';
import { PricingCards } from './Upgrade';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, formatPercent, SIGNAL_COLORS } from '../lib/format';
import api from '../lib/api';

// TELUS reference example
const TELUS = { price: 11.10, low_52w: 11.04, high_52w: 16.74, target_mean: 17.33, dividend_yield: 0.108, currency: 'CAD', score: 96 };

export default function Landing() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth() || {};
  const [email, setEmail] = useState('');
  const [topOps, setTopOps] = useState([]);
  const locale = i18n.language?.slice(0, 2) || 'en';

  useEffect(() => {
    api.get('/public/top-opportunities', { params: { limit: 8 } })
      .then(({ data }) => setTopOps(data.results || []))
      .catch(() => {});
  }, []);

  const startFree = (e) => {
    e?.preventDefault?.();
    navigate('/register', { state: { email } });
  };

  const steps = [
    { icon: Search, title: t('landing.howStep1Title'), desc: t('landing.howStep1Desc') },
    { icon: ListChecks, title: t('landing.howStep2Title'), desc: t('landing.howStep2Desc') },
    { icon: Bell, title: t('landing.howStep3Title'), desc: t('landing.howStep3Desc') },
  ];
  const features = [
    { icon: ListChecks, title: t('landing.feature1Title'), desc: t('landing.feature1Desc') },
    { icon: Bell, title: t('landing.feature2Title'), desc: t('landing.feature2Desc') },
    { icon: Wallet, title: t('landing.feature3Title'), desc: t('landing.feature3Desc') },
    { icon: Coins, title: t('landing.feature4Title'), desc: t('landing.feature4Desc') },
    { icon: Globe, title: t('landing.feature5Title'), desc: t('landing.feature5Desc') },
    { icon: Coins, title: t('landing.feature6Title'), desc: t('landing.feature6Desc') },
  ];
  const faqs = [1, 2, 3, 4].map((n) => ({ q: t(`landing.faq${n}Q`), a: t(`landing.faq${n}A`) }));

  return (
    <div className="min-h-screen bg-[var(--dz-bg)]">
      {/* Nav */}
      <header className="sticky top-0 z-40 h-16 border-b border-[var(--dz-border)] bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-7xl h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <Logo />
          <nav className="hidden md:flex items-center gap-6 text-sm text-[var(--dz-fg)]">
            <a href="#features" className="hover:text-[var(--dz-primary)]">{t('landing.navFeatures')}</a>
            <a href="#pricing" className="hover:text-[var(--dz-primary)]">{t('landing.navPricing')}</a>
            <a href="#faq" className="hover:text-[var(--dz-primary)]">{t('landing.navFaq')}</a>
          </nav>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            {user ? (
              <Button onClick={() => navigate('/app/dashboard')} className="bg-[var(--dz-primary)] text-white">{t('nav.dashboard')}</Button>
            ) : (
              <>
                <Button variant="ghost" onClick={() => navigate('/login')} className="hidden sm:inline-flex">{t('nav.login')}</Button>
                <Button onClick={() => navigate('/register')} className="bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95">{t('nav.signup')}</Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-20 grid lg:grid-cols-2 gap-10 items-center">
        <div>
          <h1 className="font-heading font-bold text-[var(--dz-fg)]" style={{ fontSize: 'clamp(32px,5vw,52px)', lineHeight: 1.1 }}>{t('landing.heroTitle')}</h1>
          <p className="mt-5 text-lg text-[var(--dz-muted)] max-w-xl">{t('landing.heroSubtitle')}</p>
          <form onSubmit={startFree} className="mt-7 flex flex-col sm:flex-row gap-3 max-w-md">
            <Input data-testid="landing-email-capture-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t('landing.emailPlaceholder')} className="h-12 bg-white" />
            <Button data-testid="landing-email-capture-submit" type="submit" className="h-12 px-6 bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95 whitespace-nowrap">{t('landing.emailCta')}</Button>
          </form>
          <p className="mt-2 text-xs text-[var(--dz-muted)]">{t('landing.emailPrivacy')}</p>
        </div>
        <div className="flex justify-center">
          <Card className="p-6 sm:p-8 w-full max-w-md shadow-[var(--dz-elev-3)]">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="font-heading font-semibold">TELUS Corporation</p>
                <p className="text-xs text-[var(--dz-muted)]">T.TO · {t('landing.exampleLabel')}</p>
              </div>
              <span className="text-[10px] uppercase rounded px-1.5 py-0.5 bg-[var(--dz-canvas)] text-[var(--dz-muted)] border border-[var(--dz-border)]">CAD</span>
            </div>
            <div className="flex justify-center"><ScoreDial score={96} classification="strong_buy" size="card" /></div>
            <div className="mt-5"><RangeGauge52w low={TELUS.low_52w} high={TELUS.high_52w} current={TELUS.price} target={TELUS.target_mean} currency="CAD" locale={locale} /></div>
          </Card>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <h2 className="font-heading font-bold text-2xl sm:text-3xl text-center">{t('landing.howTitle')}</h2>
        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {steps.map((s, i) => (
            <Card key={i} className="p-6">
              <div className="h-11 w-11 rounded-xl bg-[var(--dz-primary)] text-white flex items-center justify-center"><s.icon size={20} /></div>
              <h3 className="mt-4 font-heading font-semibold text-lg">{s.title}</h3>
              <p className="mt-2 text-sm text-[var(--dz-muted)]">{s.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Score explainer */}
      <section className="bg-white border-y border-[var(--dz-border)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14 grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <h2 className="font-heading font-bold text-2xl sm:text-3xl">{t('landing.scoreExplainerTitle')}</h2>
            <p className="mt-4 text-[var(--dz-muted)]">{t('landing.scoreExplainerDesc')}</p>
            <div className="mt-6 grid grid-cols-2 gap-3 max-w-sm">
              {[['Price', 'CAD $11.10'], ['52w low', 'CAD $11.04'], ['Target', 'CAD $17.33'], ['Dividend', '10.8%']].map(([k, v]) => (
                <div key={k} className="rounded-lg border border-[var(--dz-border)] p-3">
                  <p className="text-[11px] text-[var(--dz-muted)]">{k}</p>
                  <p className="font-medium tnum">{v}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-center">
            <Card className="p-8"><ScoreDial score={96} classification="strong_buy" size="hero" /></Card>
          </div>
        </div>
      </section>

      {/* Live Top Opportunities */}
      {topOps.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
          <div className="text-center">
            <h2 className="font-heading font-bold text-2xl sm:text-3xl">{t('landing.topTitle')}</h2>
            <p className="mt-2 text-[var(--dz-muted)] max-w-2xl mx-auto">{t('landing.topSubtitle')}</p>
          </div>
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
            {topOps.map((a) => {
              const color = SIGNAL_COLORS[a.classification] || 'var(--dz-slate)';
              const upside = (a.target_mean && a.price) ? (a.target_mean - a.price) / a.price : null;
              return (
                <Card key={a.ticker} data-testid="landing-top-opportunity-card" className="p-4 hover:shadow-[var(--dz-elev-2)] transition-shadow">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-heading font-semibold truncate">{a.ticker}</p>
                      <p className="text-[11px] text-[var(--dz-muted)] truncate">{a.name}</p>
                    </div>
                    <div className="h-11 w-11 shrink-0 rounded-full flex items-center justify-center font-heading font-bold tnum" style={{ border: `3px solid ${color}`, color: 'var(--dz-fg)' }}>{a.score}</div>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <SignalBadge classification={a.classification} size="sm" />
                    <span className="text-xs tnum text-[var(--dz-muted)]">{formatCurrency(a.price, a.currency, locale)}</span>
                  </div>
                  {upside != null && (
                    <p className="mt-2 text-[11px] text-[var(--dz-muted)]">{t('asset.subUpside')}: <span className="tnum" style={{ color: upside > 0 ? 'var(--dz-buy)' : 'var(--dz-muted)' }}>{formatPercent(upside, locale, 0)}</span></p>
                  )}
                </Card>
              );
            })}
          </div>
          <div className="mt-8 text-center">
            <Button onClick={() => navigate('/register')} className="bg-[var(--dz-primary)] text-white h-11 px-6">{t('landing.heroCta')} <ArrowRight size={16} className="ml-2" /></Button>
          </div>
        </section>
      )}

      {/* Features */}
      <section id="features" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
        <h2 className="font-heading font-bold text-2xl sm:text-3xl text-center">{t('landing.featuresTitle')}</h2>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f, i) => (
            <Card key={i} className="p-6">
              <div className="h-10 w-10 rounded-lg bg-[rgba(22,224,163,0.15)] text-[var(--dz-buy-deep)] flex items-center justify-center"><f.icon size={18} /></div>
              <h3 className="mt-4 font-heading font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-[var(--dz-muted)]">{f.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-white border-y border-[var(--dz-border)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
          <h2 className="font-heading font-bold text-2xl sm:text-3xl text-center">{t('plans.upgradeTitle')}</h2>
          <div className="mt-8"><PricingCards onChoose={() => navigate('/register')} /></div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-14">
        <h2 className="font-heading font-bold text-2xl sm:text-3xl text-center">{t('landing.faqTitle')}</h2>
        <Accordion type="single" collapsible className="mt-6">
          {faqs.map((f, i) => (
            <AccordionItem key={i} value={`faq-${i}`}>
              <AccordionTrigger className="text-left">{f.q}</AccordionTrigger>
              <AccordionContent className="text-[var(--dz-muted)]">{f.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-14">
        <Card className="p-10 text-center bg-[var(--dz-primary)]">
          <h2 className="font-heading font-bold text-2xl sm:text-3xl text-white">{t('landing.ctaTitle')}</h2>
          <p className="mt-3 text-[rgba(255,255,255,0.8)]">{t('landing.ctaSubtitle')}</p>
          <Button onClick={() => navigate('/register')} className="mt-6 h-12 px-8 bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95">
            {t('landing.heroCta')} <ArrowRight size={18} className="ml-2" />
          </Button>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--dz-border)] bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          <Logo />
          <p className="mt-4 text-xs text-[var(--dz-muted)] max-w-3xl">{t('landing.disclaimer')}</p>
          <p className="mt-4 text-xs text-[var(--dz-muted)]">© {new Date().getFullYear()} Dipzee</p>
        </div>
      </footer>
    </div>
  );
}
