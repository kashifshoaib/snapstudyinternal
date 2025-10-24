import { useAuth } from '../contexts/AuthContext';
import { User } from '../types';

/**
 * Simplified hook for accessing authentication state
 */
export function useAuthState() {
  const { state } = useAuth();
  
  return {
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    needsOnboarding: state.needsOnboarding,
    error: state.error,
    sessionExpiry: state.sessionExpiry,
  };
}

/**
 * Hook for authentication actions
 */
export function useAuthActions() {
  const { 
    login, 
    register, 
    logout, 
    completeOnboarding, 
    skipOnboarding, 
    updateUser, 
    clearError,
    checkAuthState,
    isTokenExpired
  } = useAuth();
  
  return {
    login,
    register,
    logout,
    completeOnboarding,
    skipOnboarding,
    updateUser,
    clearError,
    checkAuthState,
    isTokenExpired,
  };
}

/**
 * Hook that combines auth state and actions for convenience
 */
export function useAuthComplete() {
  const authState = useAuthState();
  const authActions = useAuthActions();
  
  return {
    ...authState,
    ...authActions,
  };
}

/**
 * Hook for checking if user has specific permissions (future extensibility)
 */
export function usePermissions() {
  const { user } = useAuthState();
  
  const hasPermission = (permission: string): boolean => {
    // For now, all authenticated users have all permissions
    // This can be extended when role-based access control is implemented
    return !!user;
  };
  
  const hasRole = (role: string): boolean => {
    // For now, all authenticated users have 'user' role
    // This can be extended when role system is implemented
    return !!user && role === 'user';
  };
  
  return {
    hasPermission,
    hasRole,
    user,
  };
}