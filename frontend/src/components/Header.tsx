import React from 'react';
import { User, UserProfile } from '../types';
import { useAuth } from '../contexts/AuthContext';

interface HeaderProps {
  user: User;
  userProfile: UserProfile | null;
  currentView: string;
  onViewChange: (view: 'lessons' | 'library' | 'settings') => void;
  onLogout?: () => void;
}

const Header: React.FC<HeaderProps> = ({ 
  user, 
  userProfile, 
  currentView, 
  onViewChange, 
  onLogout 
}) => {
  const { logout } = useAuth();

  const handleLogout = async () => {
    try {
      if (onLogout) {
        onLogout();
      } else if (logout) {
        await logout();
      }
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };
  return (
    <header className="snap-header">
      <div className="brand">
        <img src="/weblogo.png" alt="SnapStudy logo" />
        <span>SnapStudy</span>
      </div>
      <nav>
        <button
          className={`lessons-btn ${currentView === 'lessons' ? 'active' : ''}`}
          onClick={() => onViewChange('lessons')}
        >
          My Lessons
        </button>
        <button
          className={`lessons-btn ${currentView === 'library' ? 'active' : ''}`}
          onClick={() => onViewChange('library')}
        >
          My Library
        </button>
        <button
          className={`profile-icon-btn ${currentView === 'settings' ? 'active' : ''}`}
          onClick={() => onViewChange('settings')}
          title={user.full_name || user.username || 'Profile'}
        >
          <div className="header-avatar">
            {(user.first_name?.[0] || user.username?.[0] || 'U').toUpperCase()}
          </div>
        </button>
      </nav>
    </header>
  );
};

export default Header;