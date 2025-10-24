/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
// Basic Jest matchers only
import { AuthProvider, useAuth } from '../AuthContext';
import { User, OnboardingData } from '../../types';

// Mock the auth service
const mockAuthService = {
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  isAuthenticated: jest.fn(),
  getCurrentUser: jest.fn(),
  completeOnboarding: jest.fn(),
  updateProfile: jest.fn(),
};

jest.mock('../../services/authService', () => ({
  authService: mockAuthService,
}));

// Mock the config
jest.mock('../../config', () => ({
  config: {
    api: {
      baseUrl: 'http://localhost:8000',
    },
  },
}));

// Test component to access auth context
const TestComponent: React.FC = () => {
  const auth = useAuth();

  return (
    <div>
      <div data-testid="auth-state">
        {JSON.stringify({
          isAuthenticated: auth.state.isAuthenticated,
          isLoading: auth.state.isLoading,
          needsOnboarding: auth.state.needsOnboarding,
          error: auth.state.error,
          user: auth.state.user ? { email: auth.state.user.email } : null,
        })}
      </div>
      <button onClick={() => auth.login('test@example.com', 'password')} data-testid="login-btn">
        Login
      </button>
      <button onClick={() => auth.register({ email: 'test@example.com', password: 'password' })} data-testid="register-btn">
        Register
      </button>
      <button onClick={() => auth.logout()} data-testid="logout-btn">
        Logout
      </button>
      <button onClick={() => auth.clearError()} data-testid="clear-error-btn">
        Clear Error
      </button>
      <button 
        onClick={() => auth.completeOnboarding({
          full_name: 'Test User',
          age: 25,
          profession: 'Engineer',
          education_level: 'Bachelor',
          country: 'US',
          learning_style: 'visual',
          attention_span: 30,
          difficulty_level: 'intermediate',
        } as OnboardingData)} 
        data-testid="complete-onboarding-btn"
      >
        Complete Onboarding
      </button>
      <button onClick={() => auth.skipOnboarding()} data-testid="skip-onboarding-btn">
        Skip Onboarding
      </button>
      <button 
        onClick={() => auth.updateUser({ full_name: 'Updated Name' })} 
        data-testid="update-user-btn"
      >
        Update User
      </button>
    </div>
  );
};

const mockUser: User = {
  id: 'user123',
  email: 'test@example.com',
  username: 'testuser',
  first_name: 'Test',
  last_name: 'User',
  full_name: 'Test User',
  age: 25,
  profession: 'Software Engineer',
  education_level: "Bachelor's Degree",
  country: 'United States',
  onboarding_completed: true,
  preferences: {
    learning_style: 'visual',
    attention_span: 30,
    difficulty_level: 'intermediate',
  },
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  test('provides initial auth state', async () => {
    mockAuthService.isAuthenticated.mockResolvedValue(false);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.isLoading).toBe(false);
      expect(authState.user).toBe(null);
    });
  });

  test('handles successful login', async () => {
    mockAuthService.login.mockResolvedValue({ user: mockUser });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const loginBtn = screen.getByTestId('login-btn');
    
    await act(async () => {
      loginBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(true);
      expect(authState.isLoading).toBe(false);
      expect(authState.user.email).toBe('test@example.com');
      expect(authState.needsOnboarding).toBe(false); // user has completed onboarding
    });

    expect(mockAuthService.login).toHaveBeenCalledWith('test@example.com', 'password');
  });

  test('handles login failure', async () => {
    mockAuthService.login.mockRejectedValue(new Error('Invalid credentials'));

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const loginBtn = screen.getByTestId('login-btn');
    
    await act(async () => {
      loginBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.isLoading).toBe(false);
      expect(authState.error).toBe('Invalid credentials');
    });
  });

  test('handles successful registration', async () => {
    mockAuthService.register.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const registerBtn = screen.getByTestId('register-btn');
    
    await act(async () => {
      registerBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isLoading).toBe(false);
    });

    expect(mockAuthService.register).toHaveBeenCalledWith({ 
      email: 'test@example.com', 
      password: 'password' 
    });
  });

  test('handles registration failure', async () => {
    mockAuthService.register.mockRejectedValue(new Error('Email already exists'));

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const registerBtn = screen.getByTestId('register-btn');
    
    await act(async () => {
      registerBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.isLoading).toBe(false);
      expect(authState.error).toBe('Email already exists');
    });
  });

  test('handles logout', async () => {
    // First login
    mockAuthService.login.mockResolvedValue({ user: mockUser });
    mockAuthService.logout.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Login first
    const loginBtn = screen.getByTestId('login-btn');
    await act(async () => {
      loginBtn.click();
    });

    // Then logout
    const logoutBtn = screen.getByTestId('logout-btn');
    await act(async () => {
      logoutBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.user).toBe(null);
    });

    expect(mockAuthService.logout).toHaveBeenCalled();
  });

  test('handles onboarding completion', async () => {
    const userNeedingOnboarding = { ...mockUser, onboarding_completed: false };
    const updatedUser = { ...mockUser, onboarding_completed: true };
    
    mockAuthService.login.mockResolvedValue({ user: userNeedingOnboarding });
    mockAuthService.completeOnboarding.mockResolvedValue(updatedUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Login first
    const loginBtn = screen.getByTestId('login-btn');
    await act(async () => {
      loginBtn.click();
    });

    // Verify user needs onboarding
    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.needsOnboarding).toBe(true);
    });

    // Complete onboarding
    const completeOnboardingBtn = screen.getByTestId('complete-onboarding-btn');
    await act(async () => {
      completeOnboardingBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.needsOnboarding).toBe(false);
    });

    expect(mockAuthService.completeOnboarding).toHaveBeenCalledWith({
      full_name: 'Test User',
      age: 25,
      profession: 'Engineer',
      education_level: 'Bachelor',
      country: 'US',
      learning_style: 'visual',
      attention_span: 30,
      difficulty_level: 'intermediate',
    });
  });

  test('handles skipping onboarding', async () => {
    const userNeedingOnboarding = { ...mockUser, onboarding_completed: false };
    
    mockAuthService.login.mockResolvedValue({ user: userNeedingOnboarding });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Login first
    const loginBtn = screen.getByTestId('login-btn');
    await act(async () => {
      loginBtn.click();
    });

    // Verify user needs onboarding
    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.needsOnboarding).toBe(true);
    });

    // Skip onboarding
    const skipOnboardingBtn = screen.getByTestId('skip-onboarding-btn');
    await act(async () => {
      skipOnboardingBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.needsOnboarding).toBe(false);
    });
  });

  test('handles user profile update', async () => {
    const updatedUser = { ...mockUser, full_name: 'Updated Name' };
    
    mockAuthService.login.mockResolvedValue({ user: mockUser });
    mockAuthService.updateProfile.mockResolvedValue(updatedUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Login first
    const loginBtn = screen.getByTestId('login-btn');
    await act(async () => {
      loginBtn.click();
    });

    // Update user
    const updateUserBtn = screen.getByTestId('update-user-btn');
    await act(async () => {
      updateUserBtn.click();
    });

    expect(mockAuthService.updateProfile).toHaveBeenCalledWith({ full_name: 'Updated Name' });
  });

  test('clears error state', async () => {
    mockAuthService.login.mockRejectedValue(new Error('Login failed'));

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Trigger error
    const loginBtn = screen.getByTestId('login-btn');
    await act(async () => {
      loginBtn.click();
    });

    // Verify error exists
    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.error).toBe('Login failed');
    });

    // Clear error
    const clearErrorBtn = screen.getByTestId('clear-error-btn');
    await act(async () => {
      clearErrorBtn.click();
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.error).toBe(null);
    });
  });

  test('checks auth state on mount when API is configured', async () => {
    mockAuthService.isAuthenticated.mockResolvedValue(true);
    mockAuthService.getCurrentUser.mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(true);
      expect(authState.user.email).toBe('test@example.com');
    });

    expect(mockAuthService.isAuthenticated).toHaveBeenCalled();
    expect(mockAuthService.getCurrentUser).toHaveBeenCalled();
  });

  test('skips auth check when API is not configured', async () => {
    // Mock config with placeholder API URL
    jest.doMock('../../config', () => ({
      config: {
        api: {
          baseUrl: 'https://your-api-domain.com',
        },
      },
    }));

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.isLoading).toBe(false);
    });

    // Should not call auth service when API is not configured
    expect(mockAuthService.isAuthenticated).not.toHaveBeenCalled();
  });

  test('handles session expiry', async () => {
    mockAuthService.login.mockResolvedValue({ user: mockUser });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Login first
    const loginBtn = screen.getByTestId('login-btn');
    await act(async () => {
      loginBtn.click();
    });

    // Simulate session expiry event
    await act(async () => {
      window.dispatchEvent(new Event('auth:expired'));
    });

    await waitFor(() => {
      const authState = JSON.parse(screen.getByTestId('auth-state').textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.error).toBe('Your session has expired. Please log in again.');
    });
  });

  test('throws error when useAuth is used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within an AuthProvider');

    consoleSpy.mockRestore();
  });
});