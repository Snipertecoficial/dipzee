import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const { i18n } = useTranslation();

  const applyUserPrefs = useCallback((u) => {
    if (u?.locale) {
      i18n.changeLanguage(u.locale);
      localStorage.setItem('dz_locale', u.locale);
    }
  }, [i18n]);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem('dz_token');
    if (!token) { setLoading(false); return; }
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
      applyUserPrefs(data);
    } catch (e) {
      localStorage.removeItem('dz_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [applyUserPrefs]);

  useEffect(() => { loadMe(); }, [loadMe]);

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password });
    localStorage.setItem('dz_token', data.access_token);
    setUser(data.user);
    applyUserPrefs(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post('/auth/register', payload);
    localStorage.setItem('dz_token', data.access_token);
    setUser(data.user);
    applyUserPrefs(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('dz_token');
    setUser(null);
  };

  const updateProfile = async (payload) => {
    const { data } = await api.put('/auth/profile', payload);
    setUser(data);
    applyUserPrefs(data);
    return data;
  };

  const can = useCallback(
    (feature) => !!user?.capabilities?.features?.includes(feature),
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateProfile, setUser, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
