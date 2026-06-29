import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Coins, Check } from 'lucide-react';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '../context/AuthContext';

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Fran\u00e7ais' },
  { code: 'pt', label: 'Portugu\u00eas' },
  { code: 'es', label: 'Espa\u00f1ol' },
];
const CURRENCIES = ['CAD', 'USD', 'BRL'];

export function LanguageSwitcher({ compact = false }) {
  const { i18n } = useTranslation();
  const { user, updateProfile } = useAuth() || {};
  const current = i18n.language?.slice(0, 2) || 'en';

  const change = async (code) => {
    i18n.changeLanguage(code);
    localStorage.setItem('dz_locale', code);
    if (user && updateProfile) {
      try { await updateProfile({ locale: code }); } catch (e) { /* noop */ }
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button data-testid="topbar-language-switcher" className="inline-flex items-center gap-1.5 rounded-full px-2.5 h-9 text-sm text-[var(--dz-fg)] hover:bg-[rgba(15,20,36,0.04)] transition-colors">
          <Globe size={16} /> <span className="uppercase">{current}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {LANGS.map((l) => (
          <DropdownMenuItem key={l.code} onClick={() => change(l.code)} className="flex items-center justify-between gap-4">
            {l.label} {current === l.code && <Check size={14} />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function CurrencySwitcher() {
  const { user, updateProfile } = useAuth() || {};
  const current = user?.currency || 'USD';

  const change = async (cur) => {
    if (user && updateProfile) {
      try { await updateProfile({ currency: cur }); } catch (e) { /* noop */ }
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button data-testid="topbar-currency-switcher" className="inline-flex items-center gap-1.5 rounded-full px-2.5 h-9 text-sm text-[var(--dz-fg)] hover:bg-[rgba(15,20,36,0.04)] transition-colors">
          <Coins size={16} /> <span>{current}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {CURRENCIES.map((c) => (
          <DropdownMenuItem key={c} onClick={() => change(c)} className="flex items-center justify-between gap-4">
            {c} {current === c && <Check size={14} />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
