import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import '@/App.css';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import ProtectedRoute from './components/ProtectedRoute';
import { AppShell } from './components/TopBar';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import AssetDetail from './pages/AssetDetail';
import Alerts from './pages/Alerts';
import Notifications from './pages/Notifications';
import Settings from './pages/Settings';
import Upgrade from './pages/Upgrade';
import Screener from './pages/Screener';
import Admin from './pages/Admin';
import News from './pages/News';
import Markets from './pages/Markets';
import Portfolio from './pages/Portfolio';

const Protected = ({ children }) => (
  <ProtectedRoute><AppShell>{children}</AppShell></ProtectedRoute>
);

function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
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
            <Toaster position="top-right" richColors />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}

export default App;
