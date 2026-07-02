import React from 'react';
import { useTranslation } from 'react-i18next';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export function ThemeToggle({ className = '' }) {
  const { effective, toggle } = useTheme();
  const { t } = useTranslation();
  const isDark = effective === 'dark';
  return (
    <button
      type="button"
      onClick={toggle}
      data-testid="theme-toggle-button"
      aria-label={isDark ? t('settings.themeLight') : t('settings.themeDark')}
      title={isDark ? t('settings.themeLight') : t('settings.themeDark')}
      className={`inline-flex items-center justify-center h-9 w-9 rounded-full text-[var(--dz-muted)] hover:bg-[var(--dz-primary-8)] hover:text-[var(--dz-fg)] transition-colors ${className}`}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
