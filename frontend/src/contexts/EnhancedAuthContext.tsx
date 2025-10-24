/**
 * Enhanced Authentication Context with comprehensive error handling and loading states.
 * 
 * This context provides authentication state management with:
 * - Comprehensive error handling and user feedback
 * - Loading state management with progress indicators
 * - Network-aware operations with offline support
 * - Graceful degradation for poor connections
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect, ReactNode } from 'react';
import { User, OnboardingData } from '../types';
import { authService } from '../services/authService';
import { 
  useLoadingState, 
  useNotifications, 
  AuthLoadingOperations, 
  createAuthLoadingOptions,
  handleNetworkError 
} from '../utils/loadingStateManager';
import { useNetworkStatus, executeWithNetworkFallback } from '../utils/networkStatusManager';


// Enhanced authentication state interface
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  needsOnboarding: boolean;
  error: string | null;
  sessionExpiry: number | null;
  lastActivity: Date | null;
  retryCount: number;
}

// Authentication actions
interface AuthAction {
  type: 
    | 'SET_LOADING' 
    | 'LOGIN_SUCCESS' 
    | 'LOGIN_FAILURE' 
    | 'LOGOUT' 
    | 'SET_USER' 
    | 'SET_ONBOARDING' 
    | 'CLEAR_ERROR' 
    | 'SESSION_EXPIRED'
    | 'NETWORK_ERROR'
    | 'RETRY_OPERATION'
    | 'UPDATE_ACTIVITY';
  payload?: any;
}

// Enhanced authentication context interface
interface AuthContextType {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => Promise<void>;
  completeOnboarding: (onboardingData: OnboardingData) => Promise<void>;
  skipOnboarding: () => void;
  updateUser: (userData: Partial<User>) => Promise<void>;
  clearError: () => void;
  retryLastOperation: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

// Initial state
const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  needsOnboarding: false,
  error: null,
  sessionExpiry: null,
  lastActivity: null,
  retryCount: 0
};

// Auth reducer with enhanced error handling
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
        error: action.payload ? null : state.error
      };

    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        isAuthenticated: true,
        isLoading: false,
        needsOnboarding: !action.payload.user.onboarding_completed,
        error: null,
        sessionExpiry: action.payload.sessionExpiry,
        lastActivity: new Date(),
        retryCount: 0
      };

    case 'LOGIN_FAILURE':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload,
        retryCount: state.retryCount + 1
      };

    case 'LOGOUT':
      return {
        ...initialState,
        isLoading: false
      };

    case 'SET_USER':
      return {
        ...state,
        user: action.payload,
        needsOnboarding: action.payload ? !action.payload.onboarding_completed : false,
        lastActivity: new Date()
      };

    case 'SET_ONBOARDING':
      return {
        ...state,
        needsOnboarding: action.payload,
        user: state.user ? { ...state.user, onboarding_completed: !action.payload } : null
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
        retryCount: 0
      };

    case 'SESSION_EXPIRED':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        error: 'Your session has expired. Please log in again.',
        sessionExpiry: null
      };

    case 'NETWORK_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false
      };

    case 'RETRY_OPERATION':
      return {
        ...state,
        error: null,
        isLoading: true
      };

    case 'UPDATE_ACTIVITY':
      return {
        ...state,
        lastActivity: new Date()
      };

    default:
      return state;
  }
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Enhanced Auth Provider component
export function EnhancedAuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);
  const [loadingState, loadingActions] = useLoadingState();
  const notifications = useNotifications();
  const [networkStatus, networkActions] = useNetworkStatus();

  // Store last operation for retry functionality
  const lastOperationRef = React.useRef<(() => Promise<void>) | null>(null);

  // Initialize authentication state
  useEffect(() => {
    initializeAuth();
  }, []);

  // Session monitoring
  useEffect(() => {
    if (state.isAuthenticated && state.sessionExpiry) {
      const timeUntilExpiry = state.sessionExpiry - Date.now();
      
      if (timeUntilExpiry > 0) {
        const warningTime = Math.max(timeUntilExpiry - 5 * 60 * 1000, 0); // 5 minutes before expiry
        
        setTimeout(() => {
          notifications.warning(
            'Session Expiring',
            'Your session will expire in 5 minutes. Please save your work.',
            30000
          );
        }, warningTime);

        setTimeout(() => {
          dispatch({ type: 'SESSION_EXPIRED' });
          notifications.error(
            'Session Expired',
            'Your session has expired. Please log in again.',
            true
          );
        }, timeUntilExpiry);
      }
    }
  }, [state.sessionExpiry, state.isAuthenticated, notifications]);

  // Activity tracking
  useEffect(() => {
    const handleActivity = () => {
      if (state.isAuthenticated) {
        dispatch({ type: 'UPDATE_ACTIVITY' });
      }
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, handleActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleActivity, true);
      });
    };
  }, [state.isAuthenticated]);

  const initializeAuth = async () => {
    try {
      loadingActions.startLoading(createAuthLoadingOptions('VERIFY_TOKEN', {
        message: 'Checking your session...'
      }));

      const token = localStorage.getItem('auth_token');
      if (!token) {
        dispatch({ type: 'SET_LOADING', payload: false });
        loadingActions.stopLoading();
        return;
      }

      const user = await executeWithNetworkFallback(
        () => authService.getCurrentUser(),
        undefined,
        'getCurrentUser'
      );

      if (user) {
        dispatch({ 
          type: 'LOGIN_SUCCESS', 
          payload: { 
            user, 
            sessionExpiry: Date.now() + 24 * 60 * 60 * 1000 // 24 hours
          } 
        });
      } else {
        localStorage.removeItem('auth_token');
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      localStorage.removeItem('auth_token');
      dispatch({ type: 'SET_LOADING', payload: false });
    } finally {
      loadingActions.stopLoading();
    }
  };

  const login = useCallback(async (email: string, password: string) => {
    const operation = async () => {
      try {
        loadingActions.startLoading(createAuthLoadingOptions('LOGIN', {
          message: 'Signing you in...'
        }));

        dispatch({ type: 'SET_LOADING', payload: true });

        const result = await executeWithNetworkFallback(
          () => authService.login({ email, password }),
          undefined,
          'login'
        );

        if (result.token && result.user) {
          localStorage.setItem('auth_token', result.token);
          
          dispatch({ 
            type: 'LOGIN_SUCCESS', 
            payload: { 
              user: result.user,
              sessionExpiry: Date.now() + 24 * 60 * 60 * 1000
            } 
          });

          notifications.success(
            'Welcome back!',
            `Good to see you again, ${result.user.full_name || result.user.email}!`
          );
        } else {
          throw new Error('Invalid response from server');
        }
      } catch (error: any) {
        const errorMessage = error.response?.data?.user_message || 
                           error.message || 
                           'Login failed. Please check your credentials.';
        
        dispatch({ type: 'LOGIN_FAILURE', payload: errorMessage });
        
        // Show appropriate error notification
        if (error.response?.status === 401) {
          notifications.error(
            'Invalid Credentials',
            'The email or password you entered is incorrect. Please try again.'
          );
        } else if (!networkStatus.isOnline) {
          notifications.error(
            'Connection Error',
            'Please check your internet connection and try again.'
          );
        } else {
          notifications.error(
            'Login Failed',
            errorMessage
          );
        }

        throw error;
      } finally {
        loadingActions.stopLoading();
      }
    };

    lastOperationRef.current = operation;
    await operation();
  }, [loadingActions, notifications, networkStatus.isOnline]);

  const register = useCallback(async (userData: any) => {
    const operation = async () => {
      try {
        loadingActions.startLoading(createAuthLoadingOptions('REGISTER', {
          message: 'Creating your account...'
        }));

        dispatch({ type: 'SET_LOADING', payload: true });

        await executeWithNetworkFallback(
          () => authService.register(userData),
          undefined,
          'register'
        );

        // Registration successful, but user needs to login
        dispatch({ type: 'SET_LOADING', payload: false });

        notifications.success(
          'Account Created!',
          'Welcome to SnapStudy! Let\'s get you set up.'
        );
      } catch (error: any) {
        const errorMessage = error.response?.data?.user_message || 
                           error.message || 
                           'Registration failed. Please try again.';
        
        dispatch({ type: 'LOGIN_FAILURE', payload: errorMessage });
        
        // Show appropriate error notification
        if (error.response?.status === 409) {
          notifications.error(
            'Email Already Registered',
            'An account with this email already exists. Try logging in instead.'
          );
        } else if (error.response?.data?.error_code === 'REG_WEAK_PASSWORD') {
          notifications.error(
            'Weak Password',
            'Please use a stronger password with at least 8 characters, including uppercase, lowercase, numbers, and special characters.'
          );
        } else {
          notifications.error(
            'Registration Failed',
            errorMessage
          );
        }

        throw error;
      } finally {
        loadingActions.stopLoading();
      }
    };

    lastOperationRef.current = operation;
    await operation();
  }, [loadingActions, notifications]);

  const logout = useCallback(async () => {
    try {
      loadingActions.startLoading(createAuthLoadingOptions('LOGOUT', {
        message: 'Signing you out...'
      }));

      // Clear local storage
      localStorage.removeItem('auth_token');
      
      // Try to notify server (don't wait for response)
      if (networkStatus.isOnline) {
        authService.logout().catch(() => {
          // Ignore logout errors - user is already being logged out locally
        });
      }

      dispatch({ type: 'LOGOUT' });
      
      notifications.info(
        'Signed Out',
        'You have been successfully signed out.'
      );
    } catch (error) {
      // Even if logout fails, clear local state
      dispatch({ type: 'LOGOUT' });
    } finally {
      loadingActions.stopLoading();
    }
  }, [loadingActions, notifications, networkStatus.isOnline]);

  const completeOnboarding = useCallback(async (onboardingData: OnboardingData) => {
    const operation = async () => {
      try {
        loadingActions.startLoading(createAuthLoadingOptions('COMPLETE_ONBOARDING', {
          message: 'Completing your setup...'
        }));

        const updatedUser = await executeWithNetworkFallback(
          () => authService.completeOnboarding(onboardingData),
          undefined,
          'completeOnboarding'
        );

        dispatch({ type: 'SET_USER', payload: updatedUser });
        dispatch({ type: 'SET_ONBOARDING', payload: false });

        notifications.success(
          'Setup Complete!',
          'Your profile has been set up. Let\'s start learning!'
        );
      } catch (error: any) {
        const errorMessage = error.response?.data?.user_message || 
                           'Failed to complete onboarding. Please try again.';
        
        notifications.error(
          'Setup Failed',
          errorMessage
        );

        // Queue for offline retry if network error
        if (!networkStatus.isOnline) {
          networkActions.addToOfflineQueue('completeOnboarding', onboardingData);
        }

        throw error;
      } finally {
        loadingActions.stopLoading();
      }
    };

    lastOperationRef.current = operation;
    await operation();
  }, [loadingActions, notifications, networkStatus.isOnline, networkActions]);

  const skipOnboarding = useCallback(() => {
    dispatch({ type: 'SET_ONBOARDING', payload: false });
    notifications.info(
      'Onboarding Skipped',
      'You can complete your profile setup later in Settings.'
    );
  }, [notifications]);

  const updateUser = useCallback(async (userData: Partial<User>) => {
    const operation = async () => {
      try {
        loadingActions.startLoading(createAuthLoadingOptions('UPDATE_PROFILE', {
          message: 'Updating your profile...'
        }));

        const updatedUser = await executeWithNetworkFallback(
          () => authService.updateProfile(userData),
          undefined,
          'updateProfile'
        );

        dispatch({ type: 'SET_USER', payload: updatedUser });

        notifications.success(
          'Profile Updated',
          'Your profile has been successfully updated.'
        );
      } catch (error: any) {
        const errorMessage = error.response?.data?.user_message || 
                           'Failed to update profile. Please try again.';
        
        notifications.error(
          'Update Failed',
          errorMessage
        );

        // Queue for offline retry if network error
        if (!networkStatus.isOnline) {
          networkActions.addToOfflineQueue('updateProfile', userData);
        }

        throw error;
      } finally {
        loadingActions.stopLoading();
      }
    };

    lastOperationRef.current = operation;
    await operation();
  }, [loadingActions, notifications, networkStatus.isOnline, networkActions]);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const retryLastOperation = useCallback(async () => {
    if (lastOperationRef.current) {
      dispatch({ type: 'RETRY_OPERATION' });
      try {
        await lastOperationRef.current();
      } catch (error) {
        // Error handling is done in the individual operations
      }
    }
  }, []);

  const refreshSession = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;

      const user = await authService.getCurrentUser();
      if (user) {
        dispatch({ 
          type: 'SET_USER', 
          payload: user 
        });
      } else {
        dispatch({ type: 'SESSION_EXPIRED' });
      }
    } catch (error) {
      dispatch({ type: 'SESSION_EXPIRED' });
    }
  }, []);

  const contextValue: AuthContextType = {
    state,
    login,
    register,
    logout,
    completeOnboarding,
    skipOnboarding,
    updateUser,
    clearError,
    retryLastOperation,
    refreshSession
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useEnhancedAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useEnhancedAuth must be used within an EnhancedAuthProvider');
  }
  return context;
}

// Export for backward compatibility
export { EnhancedAuthProvider as AuthProvider, useEnhancedAuth as useAuth };