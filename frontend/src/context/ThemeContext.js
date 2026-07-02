import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const ThemeContext = createContext(null);

const STORAGE_KEY = 'dz_theme';

function systemPrefersDark() {
  return typeof window !== 'undefined' && window.matchMedia
    && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function resolve(theme) {
  if (theme === 'system') return systemPrefersDark() ? 'dark' : 'light';
  return theme;
}

function apply(theme) {
  const effective = resolve(theme);
  const root = document.documentElement;
  root.classList.toggle('dark', effective === 'dark');
  root.style.colorScheme = effective;
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => localStorage.getItem(STORAGE_KEY) || 'light');

  useEffect(() => { apply(theme); }, [theme]);

  useEffect(() => {
    if (theme !== 'system' || !window.matchMedia) return undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => apply('system');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  const setTheme = useCallback((t) => {
    localStorage.setItem(STORAGE_KEY, t);
    setThemeState(t);
  }, []);

  const toggle = useCallback(() => {
    setTheme(resolve(theme) === 'dark' ? 'light' : 'dark');
  }, [theme, setTheme]);

  const effective = resolve(theme);

  return (
    <ThemeContext.Provider value={{ theme, effective, setTheme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
