import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bell, Menu, User, LogOut, Settings as SettingsIcon, Crown, LayoutDashboard, BellRing, Filter } from 'lucide-react';
import { Logo } from './Logo';
import { StockSearch } from './StockSearch';
import { LanguageSwitcher, CurrencySwitcher } from './Switchers';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

export function TopBar() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

  const loadUnread = useCallback(async () => {
    try {
      const { data } = await api.get('/notifications');
      setUnread(data.unread || 0);
    } catch (e) { /* noop */ }
  }, []);

  useEffect(() => {
    loadUnread();
    const id = setInterval(loadUnread, 60000);
    return () => clearInterval(id);
  }, [loadUnread]);

  const navLinks = [
    { to: '/app/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/app/screener', label: t('screener.title'), icon: Filter },
    { to: '/app/alerts', label: t('nav.alerts'), icon: BellRing },
    { to: '/app/notifications', label: t('nav.notifications'), icon: Bell },
    { to: '/app/settings', label: t('nav.settings'), icon: SettingsIcon },
  ];

  const onLogout = () => { logout(); navigate('/'); };

  return (
    <header className="sticky top-0 z-40 h-14 border-b border-[var(--dz-border)] bg-white/95 backdrop-blur">
      <div className="mx-auto max-w-7xl h-full px-4 sm:px-6 lg:px-8 flex items-center gap-3">
        {/* Mobile menu */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <button className="lg:hidden inline-flex items-center justify-center h-9 w-9 rounded-md hover:bg-[rgba(15,20,36,0.04)]" aria-label={t('nav.menu')}>
              <Menu size={20} />
            </button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72">
            <SheetHeader><SheetTitle><Logo /></SheetTitle></SheetHeader>
            <nav className="mt-6 flex flex-col gap-1">
              {navLinks.map((l) => (
                <Link key={l.to} to={l.to} onClick={() => setMobileOpen(false)} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm hover:bg-[rgba(15,20,36,0.04)]">
                  <l.icon size={18} /> {l.label}
                </Link>
              ))}
              <Link to="/app/upgrade" onClick={() => setMobileOpen(false)} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-[var(--dz-primary)] font-medium">
                <Crown size={18} /> {t('nav.upgrade')}
              </Link>
            </nav>
            <div className="mt-6"><StockSearch onNavigate={() => setMobileOpen(false)} /></div>
          </SheetContent>
        </Sheet>

        <Link to="/app/dashboard" className="shrink-0"><Logo /></Link>

        <div className="hidden md:flex flex-1 justify-center px-4">
          <StockSearch />
        </div>

        <nav className="hidden lg:flex items-center gap-1 ml-auto">
          {navLinks.slice(0, 2).map((l) => (
            <Link key={l.to} to={l.to} className="rounded-full px-3 h-9 inline-flex items-center text-sm text-[var(--dz-fg)] hover:bg-[rgba(15,20,36,0.04)] transition-colors">{l.label}</Link>
          ))}
        </nav>

        <div className="flex items-center gap-1 ml-auto lg:ml-2">
          <LanguageSwitcher />
          <CurrencySwitcher />
          <button data-testid="topbar-notifications-button" onClick={() => navigate('/app/notifications')} className="relative inline-flex items-center justify-center h-9 w-9 rounded-full hover:bg-[rgba(15,20,36,0.04)] transition-colors" aria-label={t('nav.notifications')}>
            <Bell size={18} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[var(--dz-sell)] text-white text-[10px] font-semibold flex items-center justify-center">{unread > 9 ? '9+' : unread}</span>
            )}
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button data-testid="topbar-user-menu-button" className="inline-flex items-center justify-center h-9 w-9 rounded-full bg-[var(--dz-primary)] text-white">
                <User size={16} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="truncate">{user?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/app/settings')}><SettingsIcon size={15} className="mr-2" />{t('nav.settings')}</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/upgrade')}><Crown size={15} className="mr-2" />{t('nav.upgrade')}</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onLogout}><LogOut size={15} className="mr-2" />{t('nav.logout')}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}

export function AppShell({ children }) {
  return (
    <div className="min-h-screen bg-[var(--dz-bg)]">
      <TopBar />
      <main className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8">{children}</main>
    </div>
  );
}
