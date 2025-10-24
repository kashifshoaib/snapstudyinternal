import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { User, OnboardingData } from '../types';
import { authService } from '../services/authService';
import { config } from '../config';

// Authentication state interface
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  needsOnboarding: boolean;
  error: string | null;
  sessionExpiry: number | null;
}

// Authentication actions
interface AuthAction {
  type: 'SET_LOADING' | 'LOGIN_SUCCESS' | 'LOGIN_FAILURE' | 'LOGOUT' | 'SET_USER' | 'SET_ONBOARDING' | 'CLEAR_ERROR' | 'SESSION_EXPIRED';
  payload?: any;
}

// Authentication context interface
interface AuthContextType {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => Promise<void>;
  completeOnboarding: (onboardingData: OnboardingData) => Promise<void>;
  skipOnboarding: () => void;
  updateUser: (userData: Partial<User>) => Promise<void>;
  clearError: () => void;
  checkAuthState: () => Promise<void>;
  isTokenExpired: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Initial authentication state
const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  needsOnboarding: false,
  error: null,
  sessionExpiry: null,
};

// Authentication reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
        error: null,
      };

    case 'LOGIN_SUCCESS':
      const { user, sessionExpiry } = action.payload;
      return {
        ...state,
        user,
        isAuthenticated: true,
        isLoading: false,
        needsOnboarding: !user.onboarding_completed,
        error: null,
        sessionExpiry,
      };

    case 'LOGIN_FAILURE':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        needsOnboarding: false,
        error: action.payload,
        sessionExpiry: null,
      };

    case 'LOGOUT':
      return {
        ...initialState,
        isLoading: false,
      };

    case 'SET_USER':
      return {
        ...state,
        user: action.payload,
        needsOnboarding: !action.payload.onboarding_completed,
      };

    case 'SET_ONBOARDING':
      return {
        ...state,
        needsOnboarding: action.payload,
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };

    case 'SESSION_EXPIRED':
      return {
        ...initialState,
        isLoading: false,
        error: 'Your session has expired. Please log in again.',
      };

    default:
      return state;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Session expiry check interval
  useEffect(() => {
    let sessionCheckInterval: NodeJS.Timeout;

    if (state.isAuthenticated && state.sessionExpiry) {
      sessionCheckInterval = setInterval(() => {
        const now = Date.now();
        if (now >= state.sessionExpiry!) {
          dispatch({ type: 'SESSION_EXPIRED' });
          authService.logout();
        }
      }, 60000); // Check every minute
    }

    return () => {
      if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
      }
    };
  }, [state.isAuthenticated, state.sessionExpiry]);

  // Listen for auth expiration events
  useEffect(() => {
    const handleAuthExpired = () => {
      dispatch({ type: 'SESSION_EXPIRED' });
    };

    window.addEventListener('auth:expired', handleAuthExpired);

    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired);
    };
  }, []);

  // Check authentication state on mount
  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      // Skip auth check if API is not properly configured
      if (!config.api.baseUrl || 
          config.api.baseUrl.includes('PLACEHOLDER') || 
          config.api.baseUrl.includes('your-api-domain.com')) {
        console.log('API not configured, skipping authentication');
        dispatch({ type: 'LOGOUT' });
        return;
      }

      if (await authService.isAuthenticated()) {
        const currentUser = await authService.getCurrentUser();
        const sessionExpiry = Date.now() + (8 * 60 * 60 * 1000); // 8 hours from now
        
        dispatch({ 
          type: 'LOGIN_SUCCESS', 
          payload: { 
            user: currentUser, 
            sessionExpiry 
          } 
        });
      } else {
        dispatch({ type: 'LOGOUT' });
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      await authService.logout();
      dispatch({ 
        type: 'LOGIN_FAILURE', 
        payload: error instanceof Error ? error.message : 'Authentication failed' 
      });
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      const response = await authService.login({ email, password });
      const sessionExpiry = Date.now() + (8 * 60 * 60 * 1000); // 8 hours from now
      
      dispatch({ 
        type: 'LOGIN_SUCCESS', 
        payload: { 
          user: response.user, 
          sessionExpiry 
        } 
      });
    } catch (error) {
      dispatch({ 
        type: 'LOGIN_FAILURE', 
        payload: error instanceof Error ? error.message : 'Login failed' 
      });
      throw error;
    }
  }, []);

  const register = useCallback(async (userData: any) => {
    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      await authService.register(userData);
      dispatch({ type: 'SET_LOADING', payload: false });
    } catch (error) {
      dispatch({ 
        type: 'LOGIN_FAILURE', 
        payload: error instanceof Error ? error.message : 'Registration failed' 
      });
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    dispatch({ type: 'LOGOUT' });
  }, []);

  const completeOnboarding = useCallback(async (onboardingData: OnboardingData) => {
    try {
      const updatedUser = await authService.completeOnboarding(onboardingData);
      dispatch({ type: 'SET_USER', payload: updatedUser });
    } catch (error) {
      dispatch({ 
        type: 'LOGIN_FAILURE', 
        payload: error instanceof Error ? error.message : 'Onboarding failed' 
      });
      throw error;
    }
  }, []);

  const skipOnboarding = useCallback(() => {
    dispatch({ type: 'SET_ONBOARDING', payload: false });
  }, []);

  const updateUser = useCallback(async (userData: Partial<User>) => {
    try {
      const updatedUser = await authService.updateProfile(userData);
      dispatch({ type: 'SET_USER', payload: updatedUser });
    } catch (error) {
      throw error;
    }
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const isTokenExpired = useCallback(() => {
    if (!state.sessionExpiry) return false;
    return Date.now() >= state.sessionExpiry;
  }, [state.sessionExpiry]);

  const contextValue: AuthContextType = {
    state,
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

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}