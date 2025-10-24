import React from 'react';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireOnboarding?: boolean;
  fallback?: React.ReactNode;
}

/**
 * ProtectedRoute component that handles authentication and onboarding requirements
 * 
 * @param children - The component to render if authenticated
 * @param requireOnboarding - Whether the route requires completed onboarding
 * @param fallback - Custom fallback component to render when not authenticated
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireOnboarding = false,
  fallback
}) => {
  const { state } = useAuth();
  const { isAuthenticated, needsOnboarding, isLoading, user } = state;

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Checking authentication...</p>
      </div>
    );
  }

  // Not authenticated - show fallback or redirect to login
  if (!isAuthenticated || !user) {
    if (fallback) {
      return <>{fallback}</>;
    }
    
    // This will be handled by the main App component
    return null;
  }

  // Authenticated but needs onboarding and route requires it
  if (requireOnboarding && needsOnboarding) {
    // This will be handled by the main App component
    return null;
  }

  // All checks passed - render the protected content
  return <>{children}</>;
};

/**
 * Higher-order component for protecting routes
 */
export function withProtectedRoute<P extends object>(
  Component: React.ComponentType<P>,
  options: { requireOnboarding?: boolean } = {}
) {
  return function ProtectedComponent(props: P) {
    return (
      <ProtectedRoute requireOnboarding={options.requireOnboarding}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

/**
 * Hook for checking authentication status in components
 */
export function useAuthGuard(requireOnboarding: boolean = false) {
  const { state } = useAuth();
  const { isAuthenticated, needsOnboarding, isLoading, user } = state;

  const isAuthorized = React.useMemo(() => {
    if (isLoading) return false;
    if (!isAuthenticated || !user) return false;
    if (requireOnboarding && needsOnboarding) return false;
    return true;
  }, [isAuthenticated, needsOnboarding, isLoading, user, requireOnboarding]);

  return {
    isAuthorized,
    isLoading,
    isAuthenticated,
    needsOnboarding,
    user,
  };
}