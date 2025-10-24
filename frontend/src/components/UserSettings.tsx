import React, { useState, useEffect } from 'react';
import { User, UserProfile } from '../types';
import { useAuth } from '../contexts/AuthContext';
import AnalyticsDashboard from './AnalyticsDashboard';
import ProfileSettings from './ProfileSettings';
import './UserSettings.css';

interface UserSettingsProps {
  user?: User;
  userProfile?: UserProfile | null;
  onProfileUpdate?: (profile: UserProfile) => void;
  onLogout?: () => void;
}

// SVG Icons matching lessons page style
const UserIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
  </svg>
);

const AnalyticsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
  </svg>
);

const LogoutIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
  </svg>
);

const EditIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
  </svg>
);

const SaveIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/>
  </svg>
);

const UserSettings: React.FC<UserSettingsProps> = ({
  user: propUser,
  userProfile,
  onProfileUpdate,
  onLogout
}) => {
  const { state, updateUser, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'analytics'>('profile');
  const [showProfileEditor, setShowProfileEditor] = useState(false);
  
  // Use auth context user or fallback to prop
  const user = propUser || state.user;
  const [currentUser, setCurrentUser] = useState<User>(user!);

  // Update local state when user changes
  useEffect(() => {
    if (user) {
      setCurrentUser(user);
    }
  }, [user]);

  const handleProfileUpdate = async (updatedUser: User) => {
    try {
      // Use auth context update or fallback to prop
      if (updateUser) {
        await updateUser(updatedUser);
      } else if (onProfileUpdate) {
        const updatedProfile: UserProfile = {
          user_id: updatedUser.id,
          email: updatedUser.email,
          username: updatedUser.username,
          first_name: updatedUser.first_name,
          last_name: updatedUser.last_name,
          profile_picture: '',
          created_at: userProfile?.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString(),
          last_login: userProfile?.last_login || new Date().toISOString(),
          preferences: updatedUser.preferences || {
            learning_style: 'visual',
            attention_span: 15,
            difficulty_level: 'intermediate'
          }
        };
        onProfileUpdate(updatedProfile);
      }
      
      // Update local state for instant UI update
      setCurrentUser(updatedUser);
      setShowProfileEditor(false);
    } catch (error) {
      console.error('Profile update failed:', error);
      // Error handling could be improved with toast notifications
    }
  };

  const handleLogout = async () => {
    try {
      // Use auth context logout or fallback to prop
      if (logout) {
        await logout();
      } else if (onLogout) {
        onLogout();
      }
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <div className="user-settings-container">
      <div className="profile-tabs">
        <button
          className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <span className="tab-icon"><UserIcon /></span>
          <span>Profile</span>
        </button>
        <button
          className={`tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          <span className="tab-icon"><AnalyticsIcon /></span>
          <span>Analytics</span>
        </button>
        <button
          className="tab-button logout-tab"
          onClick={handleLogout}
        >
          <span className="tab-icon"><LogoutIcon /></span>
          <span>Logout</span>
        </button>
      </div>

      {activeTab === 'profile' ? (
        <div className="settings-page">
          <div className="settings-container">
            <h1>Settings</h1>

            {/* Profile Section */}
            <div className="settings-section">
              <div className="section-title">
                <h2>Profile</h2>
                <button
                  className="edit-button"
                  onClick={() => setShowProfileEditor(true)}
                >
                  Edit
                </button>
              </div>

              <div className="settings-list">
                <div className="setting-item">
                  <span className="setting-label">Email</span>
                  <span className="setting-value">{currentUser.email}</span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Name</span>
                  <span className="setting-value">{currentUser.full_name || 'Not set'}</span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Age</span>
                  <span className="setting-value">{currentUser.age || 'Not set'}</span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Profession</span>
                  <span className="setting-value">{currentUser.profession || 'Not set'}</span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Education</span>
                  <span className="setting-value">{currentUser.education_level || 'Not set'}</span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Country</span>
                  <span className="setting-value">{currentUser.country || 'Not set'}</span>
                </div>
              </div>
            </div>

            {/* Learning Preferences Section */}
            <div className="settings-section">
              <div className="section-title">
                <h2>Learning Preferences</h2>
              </div>

              <div className="settings-list">
                <div className="setting-item">
                  <span className="setting-label">Learning Style</span>
                  <span className="setting-value">
                    {currentUser.preferences?.learning_style === 'visual' && 'Visual'}
                    {currentUser.preferences?.learning_style === 'auditory' && 'Auditory'}
                    {currentUser.preferences?.learning_style === 'reading' && 'Reading'}
                    {!currentUser.preferences?.learning_style && 'Not set'}
                  </span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Lesson Length</span>
                  <span className="setting-value">
                    {currentUser.preferences?.attention_span
                      ? `${currentUser.preferences.attention_span} minutes`
                      : 'Not set'
                    }
                  </span>
                </div>
                <div className="setting-item">
                  <span className="setting-label">Difficulty Level</span>
                  <span className="setting-value">
                    {currentUser.preferences?.difficulty_level === 'beginner' && 'Beginner'}
                    {currentUser.preferences?.difficulty_level === 'intermediate' && 'Intermediate'}
                    {currentUser.preferences?.difficulty_level === 'advanced' && 'Advanced'}
                    {!currentUser.preferences?.difficulty_level && 'Not set'}
                  </span>
                </div>
              </div>
            </div>

            {/* Account Section */}
            <div className="settings-section">
              <div className="section-title">
                <h2>Account</h2>
              </div>

              <div className="settings-list">
                <div className="setting-item">
                  <span className="setting-label">Onboarding Status</span>
                  <span className={`setting-value ${currentUser.onboarding_completed ? 'status-complete' : 'status-incomplete'}`}>
                    {currentUser.onboarding_completed ? 'Complete' : 'Incomplete'}
                  </span>
                </div>
              </div>

              {!currentUser.onboarding_completed && (
                <button
                  className="complete-onboarding-button"
                  onClick={() => setShowProfileEditor(true)}
                >
                  Complete Onboarding
                </button>
              )}
            </div>
          </div>

          {showProfileEditor && (
            <ProfileSettings
              user={currentUser}
              onUpdate={handleProfileUpdate}
              onClose={() => setShowProfileEditor(false)}
            />
          )}
        </div>
      ) : (
        <div className="analytics-content">
          <AnalyticsDashboard user={currentUser} />
        </div>
      )}
    </div>
  );
};

export default UserSettings;