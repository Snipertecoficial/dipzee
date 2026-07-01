import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  Search, Bell, ListChecks, Coins, Globe, Wallet, ArrowRight, ShieldCheck, Lock,
  Eye, KeyRound, Activity, Menu, TrendingUp, RefreshCw, CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { Logo } from '../components/Logo';
import { LanguageSwitcher } from '../components/Switchers';
import { ScoreDial } from '../components/ScoreDial';
import { RangeGauge52w } from '../components/RangeGauge';
import { SignalBadge } from '../components/SignalBadge';
import { PricingCards } from './Upgrade';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, formatPercent, SIGNAL_COLORS } from '../lib/format';
import api from '../lib/api';

const TELUS = { price: 11.10, low_52w: 11.04, high_52w: 16.74, target_mean: 17.33, dividend_yield: 0.108, currency: 'CAD', score: 96 };

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
};

function Reveal({ children, className = '' }) {
  return (
    <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: '-80px' }} className={className}>
      {children}
    </motion.div>
  );
}

export default function Landing() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth() || {};
  const [topOps, setTopOps] = useState([]);
  const [loadingOps, setLoadingOps] = useState(true);
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const locale = i18n.language?.slice(0, 2) || 'en';

  const loadOps = useCallback(() => {
    setLoadingOps(true);
    api.get('/public/top-opportunities', { params: { limit: 8 } })
      .then(({ data }) => setTopOps(data.results || []))
      .catch(() => setTopOps([]))
      .finally(() => setLoadingOps(false));
  }, []);

  useEffect(() => { loadOps(); }, [loadOps]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const goRegister = () => navigate('/register');

  const navItems = [
    { href: '#how', label: t('landing.navHow') },
    { href: '#opportunities', label: t('landing.navOpportunities') },
    { href: '#security', label: t('landing.navSecurity') },
    { href: '#pricing', label: t('landing.navPricing') },
    { href: '#faq', label: t('landing.navFaq') },
  ];
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
  const proofItems = [
    { icon: Activity, label: t('landing.proof1') },
    { icon: Globe, label: t('landing.proof2') },
    { icon: TrendingUp, label: t('landing.proof3') },
    { icon: ShieldCheck, label: t('landing.proof4') },
  ];
  const security = [
    { icon: Lock, label: t('landing.sec1') },
    { icon: KeyRound, label: t('landing.sec2') },
    { icon: Eye, label: t('landing.sec3') },
    { icon: ShieldCheck, label: t('landing.sec4') },
    { icon: Wallet, label: t('landing.sec5') },
  ];
  const faqs = [1, 2, 3, 4].map((n) => ({ q: t(`landing.faq${n}Q`), a: t(`landing.faq${n}A`) }));

  return (
    <div className="min-h-screen bg-[var(--dz-bg)] text-[var(--dz-fg)]">
      {/* Topbar */}
      <header className={`sticky top-0 z-40 h-16 bg-[var(--dz-surface)]/90 backdrop-blur transition-shadow duration-200 ${scrolled ? 'shadow-[var(--dz-elev-1)] border-b border-[var(--dz-border)]' : 'border-b border-transparent'}`} data-testid="public-topbar">
        <div className="mx-auto max-w-6xl h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
          <Link to="/" aria-label="Dipzee"><Logo /></Link>
          <nav className="hidden md:flex items-center gap-1 text-sm">
            {navItems.map((n) => (
              <a key={n.href} href={n.href} className="px-3 py-2 rounded-lg text-[var(--dz-muted)] hover:text-[var(--dz-primary)] hover:bg-[var(--dz-primary-8)] transition-colors">{n.label}</a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <div className="hidden sm:block"><LanguageSwitcher /></div>
            {user ? (
              <Button onClick={() => navigate('/app/dashboard')} className="bg-[var(--dz-primary)] text-white">{t('nav.dashboard')}</Button>
            ) : (
              <>
                <Button variant="ghost" onClick={() => navigate('/login')} data-testid="public-topbar-login-link" className="hidden sm:inline-flex text-[var(--dz-primary)]">{t('nav.login')}</Button>
                <Button onClick={goRegister} data-testid="public-topbar-primary-cta-button" className="hidden sm:inline-flex bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95">{t('nav.signup')}</Button>
              </>
            )}
            {/* Mobile menu */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <button className="md:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg hover:bg-[var(--dz-primary-8)]" aria-label="Menu" data-testid="public-topbar-mobile-menu-button"><Menu size={20} /></button>
              </SheetTrigger>
              <SheetContent side="right" className="w-72">
                <SheetHeader><SheetTitle asChild><Logo /></SheetTitle></SheetHeader>
                <nav className="mt-6 flex flex-col gap-1">
                  {navItems.map((n) => (
                    <a key={n.href} href={n.href} onClick={() => setMobileOpen(false)} className="px-3 py-2.5 rounded-lg text-sm hover:bg-[var(--dz-primary-8)]">{n.label}</a>
                  ))}
                </nav>
                <div className="mt-4"><LanguageSwitcher /></div>
                <div className="mt-4 flex flex-col gap-2">
                  <Button variant="outline" onClick={() => { setMobileOpen(false); navigate('/login'); }}>{t('nav.login')}</Button>
                  <Button onClick={() => { setMobileOpen(false); goRegister(); }} className="bg-[var(--dz-mint)] text-[var(--dz-primary)]">{t('nav.signup')}</Button>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section
        id="home"
        data-testid="home-hero"
        className="relative overflow-hidden"
        style={{
          backgroundImage:
            'radial-gradient(900px 420px at 12% 8%, rgba(22,224,163,0.12) 0%, rgba(22,224,163,0) 60%), radial-gradient(900px 420px at 88% 0%, rgba(26,31,77,0.10) 0%, rgba(26,31,77,0) 55%)',
        }}
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 pt-12 lg:pt-16 pb-14 grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          <div className="lg:col-span-6">
            <span className="inline-flex items-center gap-2 rounded-full border border-[var(--dz-border)] bg-[var(--dz-surface)] px-3 py-1 text-xs text-[var(--dz-muted)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--dz-mint)]" /> {t('landing.trustedBy')}
            </span>
            <h1 className="mt-4 font-heading font-bold tracking-tight text-[var(--dz-fg)]" style={{ fontSize: 'clamp(34px,5vw,56px)', lineHeight: 1.08 }}>
              {t('landing.heroTitle')}
            </h1>
            <p className="mt-5 text-base sm:text-lg text-[var(--dz-muted)] max-w-[58ch] leading-relaxed">{t('landing.heroSubtitle')}</p>
            <div className="mt-7 flex flex-col sm:flex-row gap-3">
              <Button onClick={goRegister} data-testid="home-hero-primary-cta-button" className="h-12 px-6 bg-[var(--dz-primary)] text-white hover:brightness-110 active:scale-[0.98] transition-[transform,filter] shadow-[var(--dz-elev-1)]">
                {t('landing.heroCta')} <ArrowRight size={18} className="ml-2" />
              </Button>
              <Button onClick={() => { document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' }); }} data-testid="home-hero-secondary-cta-button" variant="outline" className="h-12 px-6 bg-[var(--dz-surface)] text-[var(--dz-primary)] border-[var(--dz-border)]">
                {t('landing.secondaryCta')}
              </Button>
            </div>
            <p className="mt-3 flex items-center gap-2 text-xs text-[var(--dz-muted)]"><Lock size={13} className="text-[var(--dz-buy)]" /> {t('landing.microTrial')}</p>

            <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2" data-testid="home-hero-credibility-band">
              {security.slice(0, 3).map((s) => (
                <span key={s.label} className="inline-flex items-center gap-1.5 text-xs text-[var(--dz-muted)]"><s.icon size={14} className="text-[var(--dz-primary)]" /> {s.label}</span>
              ))}
            </div>
          </div>

          {/* Product proof */}
          <div className="lg:col-span-6">
            <div className="grid grid-cols-2 gap-4">
              <Card className="col-span-2 p-6 bg-[var(--dz-surface)] border border-[var(--dz-border)] shadow-[var(--dz-shadow-card)] rounded-[var(--dz-radius-lg,20px)]">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-heading font-semibold">TELUS Corporation</p>
                    <p className="text-xs text-[var(--dz-muted)]">T.TO · {t('landing.exampleLabel')}</p>
                  </div>
                  <span className="text-[10px] uppercase rounded px-1.5 py-0.5 bg-[var(--dz-canvas)] text-[var(--dz-muted)] border border-[var(--dz-border)]">CAD</span>
                </div>
                <div className="flex justify-center" data-testid="home-hero-score-dial"><ScoreDial score={96} classification="strong_buy" size="card" /></div>
                <div className="mt-4" data-testid="home-hero-range-gauge"><RangeGauge52w low={TELUS.low_52w} high={TELUS.high_52w} current={TELUS.price} target={TELUS.target_mean} currency="CAD" locale={locale} /></div>
              </Card>
              <Card className="col-span-2 p-4 bg-[var(--dz-surface)] border border-[var(--dz-border)] shadow-[var(--dz-shadow-card)]" data-testid="home-hero-top-opportunities-preview">
                <p className="text-[11px] uppercase tracking-wider text-[var(--dz-muted)] mb-2">{t('landing.topTitle')}</p>
                {loadingOps ? (
                  <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 rounded-md" />)}</div>
                ) : (
                  <div className="divide-y divide-[var(--dz-border)]">
                    {topOps.slice(0, 3).map((a) => (
                      <div key={a.ticker} className="flex items-center justify-between py-2">
                        <span className="font-medium text-sm">{a.ticker}</span>
                        <div className="flex items-center gap-3">
                          <SignalBadge classification={a.classification} size="sm" />
                          <span className="tnum text-sm font-semibold" style={{ color: SIGNAL_COLORS[a.classification] || 'var(--dz-fg)' }}>{a.score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Proof of scale strip */}
      <section className="border-y border-[var(--dz-border)] bg-[var(--dz-surface)]">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-6 grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="home-proof-strip">
          {proofItems.map((p) => (
            <div key={p.label} className="flex items-center gap-2.5">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--dz-mint-10)] text-[var(--dz-buy-deep)] shrink-0"><p.icon size={17} /></span>
              <span className="text-xs sm:text-sm text-[var(--dz-fg)] leading-snug">{p.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20">
        <Reveal><h2 className="font-heading font-semibold text-2xl sm:text-3xl">{t('landing.howTitle')}</h2></Reveal>
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="home-how-it-works">
          {steps.map((s, i) => (
            <Reveal key={i}>
              <Card className="p-6 h-full bg-[var(--dz-surface)] border border-[var(--dz-border)] shadow-[var(--dz-shadow-card)]">
                <div className="flex items-center justify-between">
                  <div className="h-11 w-11 rounded-xl bg-[var(--dz-primary)] text-white flex items-center justify-center"><s.icon size={20} /></div>
                  <span className="font-heading font-bold text-2xl text-[var(--dz-border)] tnum">{`0${i + 1}`}</span>
                </div>
                <h3 className="mt-4 font-heading font-semibold text-lg">{s.title}</h3>
                <p className="mt-2 text-sm text-[var(--dz-muted)] leading-relaxed">{s.desc}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Live top opportunities table */}
      <section id="opportunities" className="bg-[var(--dz-surface)] border-y border-[var(--dz-border)]">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20" data-testid="home-top-opportunities-section">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <h2 className="font-heading font-semibold text-2xl sm:text-3xl">{t('landing.topTitle')}</h2>
              <p className="mt-2 text-[var(--dz-muted)] max-w-[60ch]">{t('landing.topSubtitle')}</p>
            </div>
            <Button variant="outline" onClick={loadOps} data-testid="home-top-opportunities-refresh-button" className="self-start bg-[var(--dz-surface)] border-[var(--dz-border)] text-[var(--dz-primary)]">
              <RefreshCw size={15} className={`mr-2 ${loadingOps ? 'animate-spin' : ''}`} /> {t('landing.refresh')}
            </Button>
          </div>

          <div className="mt-6 rounded-[var(--dz-radius-md,14px)] border border-[var(--dz-border)] overflow-hidden bg-[var(--dz-surface)]">
            <Table data-testid="home-top-opportunities-table">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>{t('landing.colTicker')}</TableHead>
                  <TableHead className="text-center">{t('landing.colScore')}</TableHead>
                  <TableHead>{t('landing.colSignal')}</TableHead>
                  <TableHead className="text-right">{t('landing.colYield')}</TableHead>
                  <TableHead className="text-right">{t('landing.colPrice')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingOps ? (
                  [1, 2, 3, 4, 5].map((i) => (
                    <TableRow key={i}><TableCell colSpan={5}><Skeleton className="h-6 w-full rounded" /></TableCell></TableRow>
                  ))
                ) : topOps.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="text-center text-[var(--dz-muted)] py-8">{t('dashboard.noMatch')}</TableCell></TableRow>
                ) : (
                  topOps.map((a) => (
                    <TableRow key={a.ticker} className="hover:bg-[var(--dz-primary-8)] cursor-pointer" onClick={goRegister} data-testid="home-top-opportunity-row">
                      <TableCell>
                        <div className="font-medium">{a.ticker}</div>
                        <div className="text-xs text-[var(--dz-muted)] truncate max-w-[220px]">{a.name}</div>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="inline-flex h-9 w-9 items-center justify-center rounded-full font-heading font-bold tnum text-sm" style={{ border: `2.5px solid ${SIGNAL_COLORS[a.classification] || 'var(--dz-slate)'}` }}>{a.score}</span>
                      </TableCell>
                      <TableCell><SignalBadge classification={a.classification} size="sm" /></TableCell>
                      <TableCell className="text-right tnum">{a.dividend_yield ? formatPercent(a.dividend_yield, locale, 1) : '\u2014'}</TableCell>
                      <TableCell className="text-right tnum">{formatCurrency(a.price, a.currency, locale)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </section>

      {/* Features bento */}
      <section id="features" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20">
        <Reveal><h2 className="font-heading font-semibold text-2xl sm:text-3xl">{t('landing.featuresTitle')}</h2></Reveal>
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="home-feature-grid">
          {features.map((f, i) => (
            <Reveal key={i}>
              <Card className="p-6 h-full bg-[var(--dz-surface)] border border-[var(--dz-border)] shadow-[var(--dz-shadow-card)]">
                <div className="h-10 w-10 rounded-lg bg-[var(--dz-mint-16)] text-[var(--dz-buy-deep)] flex items-center justify-center"><f.icon size={18} /></div>
                <h3 className="mt-4 font-heading font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-[var(--dz-muted)] leading-relaxed">{f.desc}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Security & trust */}
      <section id="security" className="bg-[var(--dz-surface)] border-y border-[var(--dz-border)]">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center" data-testid="home-security-trust">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-[var(--dz-mint-10)] text-[var(--dz-buy-deep)] px-3 py-1 text-xs font-medium"><ShieldCheck size={14} /> {t('landing.navSecurity')}</span>
            <h2 className="mt-4 font-heading font-semibold text-2xl sm:text-3xl">{t('landing.secTitle')}</h2>
            <p className="mt-3 text-[var(--dz-muted)] max-w-[58ch] leading-relaxed">{t('landing.secSubtitle')}</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {security.map((s) => (
              <div key={s.label} className="flex items-start gap-3 rounded-[var(--dz-radius-md,14px)] border border-[var(--dz-border)] bg-[var(--dz-bg)] p-4">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--dz-primary-8)] text-[var(--dz-primary)] shrink-0"><s.icon size={17} /></span>
                <span className="text-sm leading-snug">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20" data-testid="home-pricing">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="font-heading font-semibold text-2xl sm:text-3xl">{t('plans.upgradeTitle')}</h2>
          <p className="mt-2 text-[var(--dz-muted)]">{t('plans.upgradeSubtitle')}</p>
        </div>
        <div className="mt-10"><PricingCards onChoose={goRegister} /></div>
        <p className="mt-6 flex items-center justify-center gap-2 text-xs text-[var(--dz-muted)]"><Lock size={13} className="text-[var(--dz-buy)]" /> {t('landing.microTrial')}</p>
      </section>

      {/* FAQ */}
      <section id="faq" className="bg-[var(--dz-surface)] border-y border-[var(--dz-border)]">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20" data-testid="home-faq">
          <h2 className="font-heading font-semibold text-2xl sm:text-3xl text-center">{t('landing.faqTitle')}</h2>
          <Accordion type="single" collapsible className="mt-6">
            {faqs.map((f, i) => (
              <AccordionItem key={i} value={`faq-${i}`}>
                <AccordionTrigger className="text-left">{f.q}</AccordionTrigger>
                <AccordionContent className="text-[var(--dz-muted)]">{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14 sm:py-20" data-testid="home-final-cta">
        <Card
          className="relative overflow-hidden p-10 sm:p-14 text-center bg-[var(--dz-primary)] border-0"
          style={{ backgroundImage: 'radial-gradient(700px 320px at 50% 0%, rgba(22,224,163,0.16) 0%, rgba(22,224,163,0) 60%)' }}
        >
          <h2 className="font-heading font-bold text-2xl sm:text-3xl text-white max-w-[24ch] mx-auto">{t('landing.ctaTitle')}</h2>
          <p className="mt-3 text-[rgba(255,255,255,0.82)] max-w-[52ch] mx-auto">{t('landing.ctaSubtitle')}</p>
          <Button onClick={goRegister} className="mt-7 h-12 px-8 bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-95 active:scale-[0.98] transition-[transform,filter]">
            {t('landing.heroCta')} <ArrowRight size={18} className="ml-2" />
          </Button>
          <p className="mt-3 text-xs text-[rgba(255,255,255,0.7)]">{t('landing.microTrial')}</p>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--dz-border)] bg-[var(--dz-surface)]" data-testid="public-footer">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="col-span-2 md:col-span-1">
              <Logo />
              <p className="mt-3 text-xs text-[var(--dz-muted)] max-w-[28ch]">{t('landing.heroSubtitle')}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--dz-muted)]">{t('landing.footerProduct')}</p>
              <ul className="mt-3 space-y-2 text-sm">
                <li><a href="#how" className="text-[var(--dz-fg)] hover:text-[var(--dz-primary)] hover:underline">{t('landing.navHow')}</a></li>
                <li><a href="#pricing" className="text-[var(--dz-fg)] hover:text-[var(--dz-primary)] hover:underline">{t('landing.navPricing')}</a></li>
                <li><a href="#faq" className="text-[var(--dz-fg)] hover:text-[var(--dz-primary)] hover:underline">{t('landing.navFaq')}</a></li>
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--dz-muted)]">{t('landing.footerCompany')}</p>
              <ul className="mt-3 space-y-2 text-sm">
                <li><a href="#security" className="text-[var(--dz-fg)] hover:text-[var(--dz-primary)] hover:underline" data-testid="footer-security-link">{t('landing.navSecurity')}</a></li>
                <li><span className="text-[var(--dz-fg)]" data-testid="footer-privacy-policy-link">{t('landing.footerPrivacy')}</span></li>
                <li><span className="text-[var(--dz-fg)]">{t('landing.footerTerms')}</span></li>
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--dz-muted)]">{t('nav.language')}</p>
              <div className="mt-3" data-testid="public-footer-language-links"><LanguageSwitcher /></div>
            </div>
          </div>
          <div className="mt-10 pt-6 border-t border-[var(--dz-border)]">
            <p className="text-xs text-[var(--dz-muted)] max-w-3xl" data-testid="public-footer-disclaimer">{t('landing.disclaimer')}</p>
            <p className="mt-4 text-xs text-[var(--dz-muted)]">© {new Date().getFullYear()} Dipzee</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
