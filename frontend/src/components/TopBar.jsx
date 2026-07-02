import React, { useEffect, useState, useCallback } from 'react';
import { NavLink, Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Bell, Menu, User, LogOut, Settings as SettingsIcon, Crown, LayoutDashboard,
  BellRing, SlidersHorizontal, Newspaper, Shield, PanelLeftClose, PanelLeftOpen, Sparkles,
  BarChart3, Wallet,
} from 'lucide-react';
import { Logo, LogoMark } from './Logo';
import { StockSearch } from './StockSearch';
import { LanguageSwitcher, CurrencySwitcher } from './Switchers';
import { ThemeToggle } from './ThemeToggle';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

const PLAN_LABEL_KEY = { none: 'plans.none', free: 'plans.none', starter: 'plans.starter', pro: 'plans.pro', investor: 'plans.investor' };

function useNavSections() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const core = [
    { to: '/app/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/app/markets', label: t('nav.markets'), icon: BarChart3 },
    { to: '/app/screener', label: t('screener.title'), icon: SlidersHorizontal },
    { to: '/app/news', label: t('news.title'), icon: Newspaper },
    { to: '/app/alerts', label: t('nav.alerts'), icon: BellRing },
    { to: '/app/notifications', label: t('nav.notifications'), icon: Bell },
  ];
  if (user?.capabilities?.features?.includes('portfolio')) {
    core.splice(2, 0, { to: '/app/portfolio', label: t('nav.portfolio'), icon: Wallet });
  }
  const account = [
    { to: '/app/settings', label: t('nav.settings'), icon: SettingsIcon },
    { to: '/app/upgrade', label: t('nav.upgrade'), icon: Crown },
  ];
  const admin = user?.role === 'superadmin'
    ? [{ to: '/app/admin', label: t('admin.title'), icon: Shield }]
    : [];
  return { core, account, admin };
}

const ALL_ROUTES = [
  { to: '/app/dashboard', key: 'nav.dashboard' },
  { to: '/app/markets', key: 'nav.markets' },
  { to: '/app/portfolio', key: 'nav.portfolio' },
  { to: '/app/screener', key: 'screener.title' },
  { to: '/app/news', key: 'news.title' },
  { to: '/app/alerts', key: 'nav.alerts' },
  { to: '/app/notifications', key: 'nav.notifications' },
  { to: '/app/settings', key: 'nav.settings' },
  { to: '/app/upgrade', key: 'nav.upgrade' },
  { to: '/app/admin', key: 'admin.title' },
  { to: '/app/asset', key: 'asset.detailTitle' },
];

function usePageTitle() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const match = ALL_ROUTES.find((r) => pathname.startsWith(r.to));
  if (!match) return t('nav.dashboard');
  // asset.detailTitle may not exist; fallback gracefully
  const label = t(match.key);
  return label && !label.includes('.') ? label : t('nav.dashboard');
}

function NavItem({ item, collapsed, onClick }) {
  const content = (
    <NavLink
      to={item.to}
      onClick={onClick}
      data-testid={`sidebar-link-${item.to.split('/').pop()}`}
      className={({ isActive }) => `group relative flex items-center rounded-[10px] h-10 text-sm transition-colors
        ${collapsed ? 'justify-center px-0 w-10 mx-auto' : 'gap-3 px-3'}
        ${isActive
          ? 'bg-[rgba(26,31,77,0.06)] text-[var(--dz-primary)] font-medium'
          : 'text-[var(--dz-muted)] hover:bg-[rgba(15,20,36,0.04)] hover:text-[var(--dz-fg)]'}`}
    >
      {({ isActive }) => (
        <>
          <span className={`absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-full bg-[var(--dz-mint)] transition-opacity ${isActive ? 'opacity-100' : 'opacity-0'}`} />
          <item.icon size={18} className="shrink-0" />
          {!collapsed && <span className="truncate">{item.label}</span>}
        </>
      )}
    </NavLink>
  );
  if (collapsed) {
    return (
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right">{item.label}</TooltipContent>
      </Tooltip>
    );
  }
  return content;
}

function SidebarBody({ collapsed, onNavigate }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { core, account, admin } = useNavSections();
  const planKey = PLAN_LABEL_KEY[user?.plan || 'free'] || 'plans.free';
  const isTopTier = user?.plan === 'investor';

  const Section = ({ label, items }) => (
    <div className="px-2">
      {!collapsed && label && (
        <p className="px-3 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--dz-muted)]">{label}</p>
      )}
      <div className="flex flex-col gap-0.5">
        {items.map((it) => <NavItem key={it.to} item={it} collapsed={collapsed} onClick={onNavigate} />)}
      </div>
    </div>
  );

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <Section label={t('nav.sectionCore')} items={core} />
        <Section label={t('nav.sectionAccount')} items={account} />
        {admin.length > 0 && <Section label={t('nav.sectionAdmin')} items={admin} />}
      </ScrollArea>

      {/* Plan footer */}
      {!collapsed ? (
        <div className="m-3 rounded-[14px] border border-[var(--dz-border)] bg-[var(--dz-canvas)] p-3">
          <p className="text-[10px] uppercase tracking-wider text-[var(--dz-muted)]">{t('nav.currentPlan')}</p>
          <p className="mt-0.5 font-heading font-semibold text-sm text-[var(--dz-fg)]">{t(planKey)}</p>
          {!isTopTier && (
            <Link
              to="/app/upgrade"
              onClick={onNavigate}
              data-testid="sidebar-upgrade-cta"
              className="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded-[10px] h-9 text-sm font-medium bg-[var(--dz-mint)] text-[var(--dz-primary)] hover:brightness-[0.97] active:scale-[0.98] transition-[transform,filter]"
            >
              <Sparkles size={15} /> {t('nav.upgrade')}
            </Link>
          )}
        </div>
      ) : (
        !isTopTier && (
          <Tooltip delayDuration={200}>
            <TooltipTrigger asChild>
              <Link to="/app/upgrade" onClick={onNavigate} data-testid="sidebar-upgrade-cta" className="mx-auto mb-3 inline-flex h-10 w-10 items-center justify-center rounded-[10px] bg-[var(--dz-mint)] text-[var(--dz-primary)]">
                <Sparkles size={18} />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">{t('nav.upgrade')}</TooltipContent>
          </Tooltip>
        )
      )}
    </div>
  );
}

export function TopBar({ collapsed, setCollapsed, setMobileOpen }) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const pageTitle = usePageTitle();

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

  const onLogout = () => { logout(); navigate('/'); };

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-[var(--dz-border)] bg-[var(--dz-surface)]/85 backdrop-blur">
      <div className="h-full px-3 sm:px-5 lg:px-6 flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(true)}
          className="lg:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg hover:bg-[rgba(15,20,36,0.04)] transition-colors"
          aria-label={t('nav.menu')}
          data-testid="app-shell-mobile-menu-button"
        >
          <Menu size={20} />
        </button>

        {/* Desktop collapse toggle */}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="hidden lg:inline-flex items-center justify-center h-9 w-9 rounded-lg text-[var(--dz-muted)] hover:bg-[rgba(15,20,36,0.04)] hover:text-[var(--dz-fg)] transition-colors"
          aria-label="Toggle sidebar"
          data-testid="app-shell-sidebar-toggle"
        >
          {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
        </button>

        <h1 className="font-heading font-semibold text-base sm:text-lg text-[var(--dz-fg)] shrink-0 hidden sm:block" data-testid="app-shell-page-title">{pageTitle}</h1>

        <div className="flex-1 flex justify-center px-2 md:px-4">
          <div className="w-full max-w-md" data-testid="app-shell-global-search">
            <StockSearch />
          </div>
        </div>

        <div className="flex items-center gap-1">
          <div className="hidden sm:flex items-center gap-1">
            <LanguageSwitcher />
            <CurrencySwitcher />
          </div>
          <ThemeToggle />
          <button
            data-testid="topbar-notifications-button"
            onClick={() => navigate('/app/notifications')}
            className="relative inline-flex items-center justify-center h-9 w-9 rounded-full hover:bg-[rgba(15,20,36,0.04)] transition-colors"
            aria-label={t('nav.notifications')}
          >
            <Bell size={18} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[var(--dz-sell)] text-white text-[10px] font-semibold flex items-center justify-center">{unread > 9 ? '9+' : unread}</span>
            )}
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button data-testid="topbar-user-menu-button" className="inline-flex items-center justify-center h-9 w-9 rounded-full bg-[var(--dz-primary)] text-white hover:brightness-110 transition-[filter]">
                <User size={16} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="truncate">{user?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <div className="sm:hidden">
                <div className="px-2 py-1.5 flex items-center gap-2"><LanguageSwitcher /><CurrencySwitcher /></div>
                <DropdownMenuSeparator />
              </div>
              <DropdownMenuItem onClick={() => navigate('/app/settings')}><SettingsIcon size={15} className="mr-2" />{t('nav.settings')}</DropdownMenuItem>
              {user?.role === 'superadmin' && (
                <DropdownMenuItem onClick={() => navigate('/app/admin')} data-testid="user-menu-admin-link"><Shield size={15} className="mr-2" />{t('admin.title')}</DropdownMenuItem>
              )}
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
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('dz_sidebar_collapsed') === '1');
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem('dz_sidebar_collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[var(--dz-bg)]">
        {/* Desktop sidebar */}
        <aside
          data-testid="app-shell-sidebar"
          className={`hidden lg:flex fixed inset-y-0 left-0 z-40 flex-col border-r border-[var(--dz-border)] bg-[var(--dz-surface)] transition-[width] duration-200 ${collapsed ? 'w-[72px]' : 'w-64'}`}
        >
          <div className={`h-16 flex items-center border-b border-[var(--dz-border)] ${collapsed ? 'justify-center px-0' : 'px-4'}`}>
            <Link to="/app/dashboard" aria-label="Dipzee">
              {collapsed ? <LogoMark size={30} /> : <Logo />}
            </Link>
          </div>
          <div className="flex-1 min-h-0">
            <SidebarBody collapsed={collapsed} />
          </div>
        </aside>

        {/* Mobile sidebar (Sheet) */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <SheetHeader className="h-16 flex items-center justify-start px-4 border-b border-[var(--dz-border)]">
              <SheetTitle asChild><Logo /></SheetTitle>
            </SheetHeader>
            <div className="h-[calc(100vh-4rem)]">
              <SidebarBody collapsed={false} onNavigate={() => setMobileOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>

        {/* Main column */}
        <div className={`transition-[padding] duration-200 ${collapsed ? 'lg:pl-[72px]' : 'lg:pl-64'}`}>
          <TopBar collapsed={collapsed} setCollapsed={setCollapsed} setMobileOpen={setMobileOpen} />
          <main className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8 py-5 sm:py-7">{children}</main>
        </div>
      </div>
    </TooltipProvider>
  );
}
