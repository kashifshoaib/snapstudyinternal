/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
// Basic Jest matchers only
import UserSettings from '../UserSettings';
import { AuthProvider } from '../../contexts/AuthContext';
import { User, UserProfile } from '../../types';

// Mock the auth service
jest.mock('../../services/authService', () => ({
  authService: {
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    isAuthenticated: jest.fn().mockResolvedValue(true),
    getCurrentUser: jest.fn(),
    updateProfile: jest.fn(),
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
jest.mock('../UserSettings.css', () => ({}));
jest.mock('../AnalyticsDashboard.css', () => ({}));

// Mock child components
jest.mock('../AnalyticsDashboard', () => {
  return function MockAnalyticsDashboard({ user }: { user: User }) {
    return <div data-testid="analytics-dashboard">Analytics for {user.email}</div>;
  };
});

jest.mock('../ProfileSettings', () => {
  return function MockProfileSettings({ 
    user, 
    onUpdate, 
    onClose 
  }: { 
    user: User; 
    onUpdate: (user: User) => void; 
    onClose: () => void; 
  }) {
    return (
      <div data-testid="profile-settings">
        <h3>Profile Settings for {user.email}</h3>
        <button 
          onClick={() => onUpdate({ ...user, full_name: 'Updated Name' })}
          data-testid="update-profile-btn"
        >
          Update Profile
        </button>
        <button onClick={onClose} data-testid="close-profile-btn">
          Close
        </button>
      </div>
    );
  };
});

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>{children}</AuthProvider>
);

// Mock user data
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

const mockUserProfile: UserProfile = {
  user_id: 'user123',
  email: 'test@example.com',
  username: 'testuser',
  first_name: 'Test',
  last_name: 'User',
  profile_picture: '',
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  last_login: '2023-01-01T00:00:00Z',
  preferences: {
    learning_style: 'visual',
    attention_span: 30,
    difficulty_level: 'intermediate',
  },
};

describe('UserSettings Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders user settings with profile tab active by default', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Logout')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    
    // Profile tab should be active
    const profileTab = screen.getByRole('button', { name: /profile/i });
    expect(profileTab).toHaveClass('active');
  });

  test('displays user profile information correctly', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('test@example.com')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('Software Engineer')).toBeInTheDocument();
    expect(screen.getByText("Bachelor's Degree")).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
  });

  test('displays learning preferences correctly', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('Visual')).toBeInTheDocument();
    expect(screen.getByText('30 minutes')).toBeInTheDocument();
    expect(screen.getByText('Intermediate')).toBeInTheDocument();
  });

  test('displays onboarding status correctly for completed user', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    const statusElement = screen.getByText('Complete');
    expect(statusElement).toBeInTheDocument();
    expect(statusElement).toHaveClass('status-complete');
  });

  test('displays onboarding status correctly for incomplete user', () => {
    const incompleteUser = { ...mockUser, onboarding_completed: false };

    render(
      <TestWrapper>
        <UserSettings user={incompleteUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    const statusElement = screen.getByText('Incomplete');
    expect(statusElement).toBeInTheDocument();
    expect(statusElement).toHaveClass('status-incomplete');
    
    // Should show complete onboarding button
    expect(screen.getByText('Complete Onboarding')).toBeInTheDocument();
  });

  test('switches to analytics tab when clicked', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    const analyticsTab = screen.getByRole('button', { name: /analytics/i });
    fireEvent.click(analyticsTab);

    expect(analyticsTab).toHaveClass('active');
    expect(screen.getByTestId('analytics-dashboard')).toBeInTheDocument();
    expect(screen.getByText('Analytics for test@example.com')).toBeInTheDocument();
  });

  test('opens profile editor when edit button is clicked', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);

    expect(screen.getByTestId('profile-settings')).toBeInTheDocument();
    expect(screen.getByText('Profile Settings for test@example.com')).toBeInTheDocument();
  });

  test('opens profile editor when complete onboarding button is clicked', () => {
    const incompleteUser = { ...mockUser, onboarding_completed: false };

    render(
      <TestWrapper>
        <UserSettings user={incompleteUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    const completeOnboardingButton = screen.getByText('Complete Onboarding');
    fireEvent.click(completeOnboardingButton);

    expect(screen.getByTestId('profile-settings')).toBeInTheDocument();
  });

  test('handles profile update correctly', async () => {
    const mockOnProfileUpdate = jest.fn();

    render(
      <TestWrapper>
        <UserSettings 
          user={mockUser} 
          userProfile={mockUserProfile} 
          onProfileUpdate={mockOnProfileUpdate}
        />
      </TestWrapper>
    );

    // Open profile editor
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);

    // Update profile
    const updateButton = screen.getByTestId('update-profile-btn');
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(mockOnProfileUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 'user123',
          email: 'test@example.com',
          username: 'testuser',
          first_name: 'Test',
          last_name: 'User',
        })
      );
    });

    // Profile editor should close
    expect(screen.queryByTestId('profile-settings')).not.toBeInTheDocument();
  });

  test('closes profile editor when close button is clicked', () => {
    render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    // Open profile editor
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);

    expect(screen.getByTestId('profile-settings')).toBeInTheDocument();

    // Close profile editor
    const closeButton = screen.getByTestId('close-profile-btn');
    fireEvent.click(closeButton);

    expect(screen.queryByTestId('profile-settings')).not.toBeInTheDocument();
  });

  test('calls logout function when logout button is clicked', async () => {
    const mockOnLogout = jest.fn();

    render(
      <TestWrapper>
        <UserSettings 
          user={mockUser} 
          userProfile={mockUserProfile} 
          onLogout={mockOnLogout}
        />
      </TestWrapper>
    );

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    fireEvent.click(logoutButton);

    await waitFor(() => {
      expect(mockOnLogout).toHaveBeenCalled();
    });
  });

  test('displays "Not set" for missing profile fields', () => {
    const incompleteUser: User = {
      ...mockUser,
      full_name: undefined,
      age: undefined,
      profession: undefined,
      education_level: undefined,
      country: undefined,
      preferences: undefined,
    };

    render(
      <TestWrapper>
        <UserSettings user={incompleteUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    // Should show "Not set" for missing fields
    const notSetElements = screen.getAllByText('Not set');
    expect(notSetElements).toHaveLength(6); // name, age, profession, education, country, and learning preferences
  });

  test('displays learning preferences as "Not set" when missing', () => {
    const userWithoutPreferences: User = {
      ...mockUser,
      preferences: undefined,
    };

    render(
      <TestWrapper>
        <UserSettings user={userWithoutPreferences} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    // Learning preferences section should show "Not set"
    const learningStyleLabel = screen.getByText('Learning Style').closest('.setting-item');
    const lessonLengthLabel = screen.getByText('Lesson Length').closest('.setting-item');
    const difficultyLabel = screen.getByText('Difficulty Level').closest('.setting-item');

    expect(learningStyleLabel).toHaveTextContent('Not set');
    expect(lessonLengthLabel).toHaveTextContent('Not set');
    expect(difficultyLabel).toHaveTextContent('Not set');
  });

  test('handles different learning style values correctly', () => {
    const userWithAuditoryStyle: User = {
      ...mockUser,
      preferences: {
        learning_style: 'auditory',
        attention_span: 45,
        difficulty_level: 'advanced',
      },
    };

    render(
      <TestWrapper>
        <UserSettings user={userWithAuditoryStyle} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('Auditory')).toBeInTheDocument();
    expect(screen.getByText('45 minutes')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  test('handles reading learning style correctly', () => {
    const userWithReadingStyle: User = {
      ...mockUser,
      preferences: {
        learning_style: 'reading',
        attention_span: 15,
        difficulty_level: 'beginner',
      },
    };

    render(
      <TestWrapper>
        <UserSettings user={userWithReadingStyle} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('Reading')).toBeInTheDocument();
    expect(screen.getByText('15 minutes')).toBeInTheDocument();
    expect(screen.getByText('Beginner')).toBeInTheDocument();
  });

  test('updates local user state when user prop changes', () => {
    const { rerender } = render(
      <TestWrapper>
        <UserSettings user={mockUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('Test User')).toBeInTheDocument();

    const updatedUser = { ...mockUser, full_name: 'Updated User' };
    rerender(
      <TestWrapper>
        <UserSettings user={updatedUser} userProfile={mockUserProfile} />
      </TestWrapper>
    );

    expect(screen.getByText('Updated User')).toBeInTheDocument();
  });
});