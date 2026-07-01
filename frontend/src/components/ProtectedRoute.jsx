import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const PAID_PLANS = ['starter', 'pro', 'investor'];

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--dz-bg)]">
        <div className="h-8 w-8 rounded-full border-2 border-[var(--dz-line)] border-t-[var(--dz-mint)] animate-spin" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Paywall: users without an active (paid/trialing) plan must pick a plan first.
  const hasAccess = PAID_PLANS.includes(user.plan) || user.role === 'superadmin';
  if (!hasAccess && location.pathname !== '/app/upgrade') {
    return <Navigate to="/app/upgrade" replace />;
  }
  return children;
}
