import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import api, { setAccessToken } from '../lib/api';

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
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
      applyUserPrefs(data);
    } catch (e) {
      setAccessToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [applyUserPrefs]);

  useEffect(() => { loadMe(); }, [loadMe]);

  const login = async (email, password, otp = undefined) => {
    const { data } = await api.post('/auth/login', { email, password, otp });
    setAccessToken(data.access_token);
    setUser(data.user);
    applyUserPrefs(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post('/auth/register', payload);
    setAccessToken(data.access_token);
    setUser(data.user);
    applyUserPrefs(data.user);
    return data.user;
  };

  const logout = () => {
    api.post('/auth/logout').catch(() => {});
    setAccessToken(null);
    setUser(null);
  };

  const logoutAllDevices = async () => {
    await api.post('/auth/logout-all');
    setAccessToken(null);
    setUser(null);
  };

  const changePassword = async (currentPassword, newPassword) => {
    const { data } = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    setAccessToken(data.access_token);
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
