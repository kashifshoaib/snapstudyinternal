/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
// Basic Jest matchers only
import LoginForm from '../LoginForm';
import { AuthProvider } from '../../contexts/AuthContext';

// Mock the auth service
jest.mock('../../services/authService', () => ({
  authService: {
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    isAuthenticated: jest.fn().mockResolvedValue(false),
    getCurrentUser: jest.fn(),
  },
}));

// Mock the config
jest.mock('../../config', () => ({
  config: {
    api: {
      baseUrl: 'http://localhost:8000',
    },
  },
}));

// Mock CSS imports
jest.mock('../LoginForm.css', () => ({}));

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('LoginForm Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders login form by default', () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    );

    expect(screen.getByPlaceholderText('Email')).toBeTruthy();
    expect(screen.getByPlaceholderText('Password')).toBeTruthy();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy();
    expect(screen.getByText("Don't have an account?")).toBeTruthy();
  });

  test('switches to registration form when sign up is clicked', () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    );

    const signUpButton = screen.getByRole('button', { name: /sign up/i });
    fireEvent.click(signUpButton);

    expect(screen.getByPlaceholderText('First Name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Last Name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign up/i })).toBeInTheDocument();
    expect(screen.getByText('Already have an account?')).toBeInTheDocument();
  });

  test('validates required fields in login form', async () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    );

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    // HTML5 validation should prevent form submission
    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');

    expect(emailInput).toBeRequired();
    expect(passwordInput).toBeRequired();
  });

  test('validates required fields in registration form', () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    );

    // Switch to registration form
    const signUpToggle = screen.getByRole('button', { name: /sign up/i });
    fireEvent.click(signUpToggle);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');

    expect(firstNameInput).toBeRequired();
    expect(lastNameInput).toBeRequired();
    expect(emailInput).toBeRequired();
    expect(passwordInput).toBeRequired();
  });

  test('handles form input changes', () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    );

    const emailInput = screen.getByPlaceholderText('Email') as HTMLInputElement;
    const passwordInput = screen.getByPlaceholderText('Password') as HTMLInputElement;

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(emailInput.value).toBe('test@example.com');
    expect(passwordInput.value).toBe('password123');
  });

  test('handles registration form input changes', () => {
    render(
      <TestWrapper>
        <LoginForm />
      </TestWrapper>
    );

    // Switch to registration form
    const signUpToggle = screen.getByRole('button', { name: /sign up/i });
    fireEvent.click(signUpToggle);

    const firstNameInput = screen.getByPlaceholderText('First Name') as HTMLInputElement;
    const lastNameInput = screen.getByPlaceholderText('Last Name') as HTMLInputElement;
    const emailInput = screen.getByPlaceholderText('Email') as HTMLInputElement;
    const passwordInput = screen.getByPlaceholderText('Password') as HTMLInputElement;

    fireEvent.change(firstNameInput, { target: { value: 'John' } });
    fireEvent.change(lastNameInput, { target: { value: 'Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(firstNameInput.value).toBe('John');
    expect(lastNameInput.value).toBe('Doe');
    expect(emailInput.value).toBe('john@example.com');
    expect(passwordInput.value).toBe('password123');
  });

  test('calls onLogin prop when login form is submitted', async () => {
    const mockOnLogin = jest.fn().mockResolvedValue(undefined);

    render(
      <TestWrapper>
        <LoginForm onLogin={mockOnLogin} />
      </TestWrapper>
    );

    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnLogin).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });

  test('calls onRegister prop when registration form is submitted', async () => {
    const mockOnRegister = jest.fn().mockResolvedValue(undefined);

    render(
      <TestWrapper>
        <LoginForm onRegister={mockOnRegister} />
      </TestWrapper>
    );

    // Switch to registration form
    const signUpToggle = screen.getByRole('button', { name: /sign up/i });
    fireEvent.click(signUpToggle);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const submitButton = screen.getByRole('button', { name: /sign up/i });

    fireEvent.change(firstNameInput, { target: { value: 'John' } });
    fireEvent.change(lastNameInput, { target: { value: 'Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnRegister).toHaveBeenCalledWith({
        email: 'john@example.com',
        password: 'password123',
        first_name: 'John',
        last_name: 'Doe',
      });
    });
  });

  test('displays loading state during form submission', async () => {
    const mockOnLogin = jest.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(
      <TestWrapper>
        <LoginForm onLogin={mockOnLogin} />
      </TestWrapper>
    );

    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    // Check for loading state
    expect(screen.getByRole('button', { name: /loading/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });
  });

  test('displays error message when provided', () => {
    // We'll need to mock the auth context to provide an error state
    const mockAuthContext = {
      state: {
        isLoading: false,
        error: 'Invalid credentials',
        user: null,
        isAuthenticated: false,
        needsOnboarding: false,
        sessionExpiry: null,
      },
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      completeOnboarding: jest.fn(),
      skipOnboarding: jest.fn(),
      updateUser: jest.fn(),
      clearError: jest.fn(),
      checkAuthState: jest.fn(),
      isTokenExpired: jest.fn(),
    };

    // Mock the useAuth hook
    jest.doMock('../../contexts/AuthContext', () => ({
      useAuth: () => mockAuthContext,
      AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    }));

    render(<LoginForm />);

    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    expect(screen.getByText('Invalid credentials')).toHaveClass('error-message');
  });

  test('displays success message after successful registration', async () => {
    const mockOnRegister = jest.fn().mockResolvedValue(undefined);

    render(
      <TestWrapper>
        <LoginForm onRegister={mockOnRegister} />
      </TestWrapper>
    );

    // Switch to registration form
    const signUpToggle = screen.getByRole('button', { name: /sign up/i });
    fireEvent.click(signUpToggle);

    // Fill and submit form
    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const submitButton = screen.getByRole('button', { name: /sign up/i });

    fireEvent.change(firstNameInput, { target: { value: 'John' } });
    fireEvent.change(lastNameInput, { target: { value: 'Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Registration successful! Please log in to continue.')).toBeInTheDocument();
    });

    // Should switch back to login form after success
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('clears error when switching between login and register', () => {
    const mockClearError = jest.fn();
    
    // Mock the useAuth hook to provide clearError function
    const mockAuthContext = {
      state: {
        isLoading: false,
        error: 'Some error',
        user: null,
        isAuthenticated: false,
        needsOnboarding: false,
        sessionExpiry: null,
      },
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      completeOnboarding: jest.fn(),
      skipOnboarding: jest.fn(),
      updateUser: jest.fn(),
      clearError: mockClearError,
      checkAuthState: jest.fn(),
      isTokenExpired: jest.fn(),
    };

    jest.doMock('../../contexts/AuthContext', () => ({
      useAuth: () => mockAuthContext,
      AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    }));

    render(<LoginForm />);

    const signUpToggle = screen.getByRole('button', { name: /sign up/i });
    fireEvent.click(signUpToggle);

    expect(mockClearError).toHaveBeenCalled();
  });
});