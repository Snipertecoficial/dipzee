import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../lib/api';

const AuthContext = createContext(null);

function storeTokens(data) {
  localStorage.setItem('dz_token', data.access_token);
  localStorage.setItem('dz_refresh_token', data.refresh_token);
}

function clearTokens() {
  localStorage.removeItem('dz_token');
  localStorage.removeItem('dz_refresh_token');
}

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
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [applyUserPrefs]);

  useEffect(() => { loadMe(); }, [loadMe]);

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password });
    storeTokens(data);
    setUser(data.user);
    applyUserPrefs(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post('/auth/register', payload);
    storeTokens(data);
    setUser(data.user);
    applyUserPrefs(data.user);
    return data.user;
  };

  const logout = () => {
    const refreshToken = localStorage.getItem('dz_refresh_token');
    if (refreshToken) {
      // Best-effort — the session must clear locally either way.
      api.post('/auth/logout', { refresh_token: refreshToken }).catch(() => {});
    }
    clearTokens();
    setUser(null);
  };

  const logoutAllDevices = async () => {
    await api.post('/auth/logout-all');
    clearTokens();
    setUser(null);
  };

  const changePassword = async (currentPassword, newPassword) => {
    const { data } = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    storeTokens(data);
    return data;
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
    <AuthContext.Provider value={{ user, loading, login, register, logout, logoutAllDevices, changePassword, updateProfile, setUser, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
