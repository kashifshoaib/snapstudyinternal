import api from './api';
import { User, OnboardingData } from '../types';
import { config } from '../config';
import { profileService } from './profileService';
import { SecureStorage, SessionManager } from '../utils/secureStorage';


interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

interface AuthResponse {
  user: User;
  token: string;
}

class AuthService {
  private tokenKey = 'auth_token';
  private refreshTokenKey = 'refresh_token';
  private profileUserKey = 'profile_user';
  private userDataKey = 'user_data';

  constructor() {
    // Set up session timeout handler
    SessionManager.onTimeout(() => {
      this.handleSessionTimeout();
    });
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // First, try to authenticate with profile.json
    const profileUser = await profileService.authenticateWithProfile(
      credentials.email,
      credentials.password
    );

    if (profileUser) {
      // Store profile user flag and user data securely
      await SecureStorage.setItem(this.profileUserKey, true, { encrypt: true });
      await SecureStorage.setItem(this.userDataKey, profileUser, {
        encrypt: true,
        expirationMinutes: 480 // 8 hours
      });

      // Start session management
      SessionManager.startSession(480); // 8 hours

      console.log('Logged in as profile user');
      return { user: profileUser, token: 'profile-token' };
    }

    // If profile authentication fails, try API authentication
    try {
      const response = await api.post('/api/v1/auth/login', credentials);
      const { access_token, refresh_token } = response.data;

      // Store tokens securely with encryption
      await SecureStorage.setItem(this.tokenKey, access_token, {
        encrypt: true,
        expirationMinutes: 60 // 1 hour for access token
      });

      if (refresh_token) {
        await SecureStorage.setItem(this.refreshTokenKey, refresh_token, {
          encrypt: true,
          expirationMinutes: 10080 // 7 days for refresh token
        });
      }

      // Clear profile user flag
      await SecureStorage.removeItem(this.profileUserKey);

      // Get user data separately and store securely
      const user = await this.getCurrentUser();
      await SecureStorage.setItem(this.userDataKey, user, {
        encrypt: true,
        expirationMinutes: 480 // 8 hours
      });

      // Start session management
      SessionManager.startSession(60); // 1 hour for API sessions

      return { user, token: access_token };
    } catch (error) {
      console.error('Login error:', error);
      throw new Error('Login failed. Please check your credentials.');
    }
  }

  async register(userData: RegisterData): Promise<AuthResponse> {
    try {
      const response = await api.post('/api/v1/auth/register', userData);
      const { access_token, refresh_token } = response.data;

      // Store tokens securely with encryption
      await SecureStorage.setItem(this.tokenKey, access_token, {
        encrypt: true,
        expirationMinutes: 60 // 1 hour for access token
      });

      if (refresh_token) {
        await SecureStorage.setItem(this.refreshTokenKey, refresh_token, {
          encrypt: true,
          expirationMinutes: 10080 // 7 days for refresh token
        });
      }

      // Clear profile user flag
      await SecureStorage.removeItem(this.profileUserKey);

      // Get user data and store securely
      const user = await this.getCurrentUser();
      await SecureStorage.setItem(this.userDataKey, user, {
        encrypt: true,
        expirationMinutes: 480 // 8 hours
      });

      // Start session management
      SessionManager.startSession(60); // 1 hour for API sessions

      return { user, token: access_token };
    } catch (error) {
      console.error('Registration error:', error);
      throw new Error('Registration failed');
    }
  }

  async getCurrentUser(): Promise<User> {
    // Check if this is a profile user
    const isProfileUser = await SecureStorage.getItem(this.profileUserKey);

    if (isProfileUser) {
      const userData = await SecureStorage.getItem(this.userDataKey);
      if (userData) {
        return userData;
      }
    }

    // Get user data from JWT token and cached data
    try {
      const token = await this.getToken();
      if (!token) {
        throw new Error('No authentication token found');
      }

      // Decode JWT token to get user info (without verification for client-side)
      const payload = JSON.parse(atob(token.split('.')[1]));
      
      // Check if we have cached user data with onboarding status
      const cachedUser = await SecureStorage.getItem(this.userDataKey);
      
      const user: User = {
        id: payload.user_id,
        email: payload.email,
        full_name: payload.full_name || '',
        onboarding_completed: cachedUser?.onboarding_completed || payload.onboarding_completed || false,
        // Include other cached user data if available
        ...cachedUser
      };

      // Update cache with latest data
      await SecureStorage.setItem(this.userDataKey, user, {
        encrypt: true,
        expirationMinutes: 480
      });

      return user;
    } catch (error) {
      throw new Error('Failed to get current user');
    }
  }

  async isAuthenticated(): Promise<boolean> {
    // Check session validity first
    const sessionValid = await SessionManager.isSessionValid();
    if (!sessionValid) {
      await this.logout();
      return false;
    }

    // Check if profile user is logged in
    const isProfileUser = await SecureStorage.getItem(this.profileUserKey);
    if (isProfileUser) {
      const userData = await SecureStorage.getItem(this.userDataKey);
      return !!userData;
    }

    // If API URL is not properly configured, skip authentication
    if (!config.api.baseUrl ||
      config.api.baseUrl.includes('PLACEHOLDER') ||
      config.api.baseUrl.includes('your-api-domain.com')) {
      return false;
    }

    const token = await SecureStorage.getItem(this.tokenKey);
    return !!token;
  }

  async logout(): Promise<void> {
    // Clear all secure storage
    await SecureStorage.removeItem(this.tokenKey);
    await SecureStorage.removeItem(this.refreshTokenKey);
    await SecureStorage.removeItem(this.profileUserKey);
    await SecureStorage.removeItem(this.userDataKey);

    // Clear session
    SessionManager.clearSession();

    // Clear any legacy localStorage items
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('profile_user');
    localStorage.removeItem('user_data');
  }

  async getToken(): Promise<string | null> {
    return await SecureStorage.getItem(this.tokenKey);
  }

  async getRefreshToken(): Promise<string | null> {
    return await SecureStorage.getItem(this.refreshTokenKey);
  }

  async completeOnboarding(onboardingData: OnboardingData): Promise<User> {
    try {
      // Send onboarding data to backend
      const response = await api.post('/api/v1/users/onboarding', onboardingData);
      const updatedUser = response.data.user;
      
      // Cache the updated user data
      await SecureStorage.setItem(this.userDataKey, updatedUser, {
        encrypt: true,
        expirationMinutes: 480
      });
      
      return updatedUser;
    } catch (error) {
      throw new Error('Failed to complete onboarding');
    }
  }

  async updateProfile(profileData: Partial<User>): Promise<User> {
    try {
      const response = await api.put('/api/v1/users/profile', profileData);
      return response.data.user;
    } catch (error) {
      throw new Error('Failed to update profile');
    }
  }

  /**
   * Handles session timeout
   */
  private async handleSessionTimeout(): Promise<void> {
    console.warn('Session timeout - logging out user');
    await this.logout();

    // Dispatch event instead of using window.location to avoid page reload
    window.dispatchEvent(new CustomEvent('auth:expired', {
      detail: { reason: 'session_timeout' }
    }));

    // Show user-friendly notification without blocking
    setTimeout(() => {
      alert('Your session has expired for security reasons. Please log in again.');
    }, 100);
  }
}

export const authService = new AuthService();