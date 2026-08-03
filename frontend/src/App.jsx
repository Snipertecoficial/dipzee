import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import '@/App.css';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import ProtectedRoute from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppShell } from './components/TopBar';
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy'));
const TermsOfService = lazy(() => import('./pages/TermsOfService'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const AssetDetail = lazy(() => import('./pages/AssetDetail'));
const Alerts = lazy(() => import('./pages/Alerts'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Settings = lazy(() => import('./pages/Settings'));
const Upgrade = lazy(() => import('./pages/Upgrade'));
const Screener = lazy(() => import('./pages/Screener'));
const Admin = lazy(() => import('./pages/Admin'));
const News = lazy(() => import('./pages/News'));
const Markets = lazy(() => import('./pages/Markets'));
const Portfolio = lazy(() => import('./pages/Portfolio'));

const Protected = ({ children }) => (
  <ProtectedRoute><AppShell>{children}</AppShell></ProtectedRoute>
);

function App() {
  return (
    <div className="App">
      <ErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <Suspense fallback={<div role="status" aria-live="polite" className="min-h-screen grid place-items-center">Loading…</div>}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/terms" element={<TermsOfService />} />
              <Route path="/app" element={<Navigate to="/app/dashboard" replace />} />
              <Route path="/app/dashboard" element={<Protected><Dashboard /></Protected>} />
              <Route path="/app/markets" element={<Protected><Markets /></Protected>} />
              <Route path="/app/portfolio" element={<Protected><Portfolio /></Protected>} />
              <Route path="/app/screener" element={<Protected><Screener /></Protected>} />
              <Route path="/app/admin" element={<Protected><Admin /></Protected>} />
              <Route path="/app/news" element={<Protected><News /></Protected>} />
              <Route path="/app/asset/:ticker" element={<Protected><AssetDetail /></Protected>} />
              <Route path="/app/alerts" element={<Protected><Alerts /></Protected>} />
              <Route path="/app/notifications" element={<Protected><Notifications /></Protected>} />
              <Route path="/app/settings" element={<Protected><Settings /></Protected>} />
              <Route path="/app/upgrade" element={<Protected><Upgrade /></Protected>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            </Suspense>
            <Toaster position="top-right" richColors />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
      </ErrorBoundary>
    </div>
  );
}

export default App;
