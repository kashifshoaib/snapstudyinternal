import React, { useState } from 'react';
import { User, OnboardingData } from '../types';
import { authService } from '../services/authService';
import './ProfileSettings.css';

interface ProfileSettingsProps {
  user: User;
  onUpdate: (updatedUser: User) => void;
  onClose: () => void;
}

const ProfileSettings: React.FC<ProfileSettingsProps> = ({ user, onUpdate, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState<OnboardingData>({
    full_name: user.full_name || '',
    age: user.age,
    profession: user.profession || '',
    education_level: user.education_level || '',
    country: user.country || '',
    learning_style: user.preferences?.learning_style || 'visual',
    attention_span: user.preferences?.attention_span || 15,
    difficulty_level: user.preferences?.difficulty_level || 'intermediate'
  });

  const educationLevels = [
    'High School',
    'Associate Degree',
    'Bachelor\'s Degree',
    'Master\'s Degree',
    'PhD',
    'Professional Certification',
    'Other'
  ];

  const countries = [
    'United States', 'Canada', 'United Kingdom', 'Australia', 'Germany',
    'France', 'Spain', 'Italy', 'Netherlands', 'Sweden', 'Norway',
    'India', 'China', 'Japan', 'South Korea', 'Singapore', 'Brazil',
    'Mexico', 'Argentina', 'Other'
  ];

  const handleInputChange = (field: keyof OnboardingData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const updatedUser = await authService.completeOnboarding(formData);
      onUpdate(updatedUser);
      setSuccess('Profile updated successfully!');
      
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Profile</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form onSubmit={handleSubmit} className="profile-form">
          <div className="form-section">
            <h3>Personal Information</h3>
            
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => handleInputChange('full_name', e.target.value)}
                placeholder="Enter your full name"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Age</label>
                <input
                  type="number"
                  value={formData.age || ''}
                  onChange={(e) => handleInputChange('age', parseInt(e.target.value) || undefined)}
                  placeholder="Age"
                  min="13"
                  max="100"
                />
              </div>

              <div className="form-group">
                <label>Profession</label>
                <input
                  type="text"
                  value={formData.profession}
                  onChange={(e) => handleInputChange('profession', e.target.value)}
                  placeholder="Your profession"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Education Level</label>
                <select
                  value={formData.education_level}
                  onChange={(e) => handleInputChange('education_level', e.target.value)}
                >
                  <option value="">Select education level</option>
                  {educationLevels.map(level => (
                    <option key={level} value={level}>{level}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Country</label>
                <select
                  value={formData.country}
                  onChange={(e) => handleInputChange('country', e.target.value)}
                >
                  <option value="">Select country</option>
                  {countries.map(country => (
                    <option key={country} value={country}>{country}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>Learning Preferences</h3>
            
            <div className="form-group">
              <label>Learning Style</label>
              <div className="radio-group">
                <label className="radio-item">
                  <input
                    type="radio"
                    name="learning_style"
                    value="visual"
                    checked={formData.learning_style === 'visual'}
                    onChange={(e) => handleInputChange('learning_style', e.target.value)}
                  />
                  <span>Visual - Learn with images and diagrams</span>
                </label>
                <label className="radio-item">
                  <input
                    type="radio"
                    name="learning_style"
                    value="auditory"
                    checked={formData.learning_style === 'auditory'}
                    onChange={(e) => handleInputChange('learning_style', e.target.value)}
                  />
                  <span>Auditory - Learn by listening</span>
                </label>
                <label className="radio-item">
                  <input
                    type="radio"
                    name="learning_style"
                    value="reading"
                    checked={formData.learning_style === 'reading'}
                    onChange={(e) => handleInputChange('learning_style', e.target.value)}
                  />
                  <span>Reading - Learn by reading and writing</span>
                </label>
              </div>
            </div>

            <div className="form-group">
              <label>Lesson Length: {formData.attention_span} minutes</label>
              <input
                type="range"
                min="5"
                max="60"
                value={formData.attention_span}
                onChange={(e) => handleInputChange('attention_span', parseInt(e.target.value))}
                className="slider"
              />
            </div>

            <div className="form-group">
              <label>Difficulty Level</label>
              <div className="radio-group">
                <label className="radio-item">
                  <input
                    type="radio"
                    name="difficulty_level"
                    value="beginner"
                    checked={formData.difficulty_level === 'beginner'}
                    onChange={(e) => handleInputChange('difficulty_level', e.target.value)}
                  />
                  <span>Beginner</span>
                </label>
                <label className="radio-item">
                  <input
                    type="radio"
                    name="difficulty_level"
                    value="intermediate"
                    checked={formData.difficulty_level === 'intermediate'}
                    onChange={(e) => handleInputChange('difficulty_level', e.target.value)}
                  />
                  <span>Intermediate</span>
                </label>
                <label className="radio-item">
                  <input
                    type="radio"
                    name="difficulty_level"
                    value="advanced"
                    checked={formData.difficulty_level === 'advanced'}
                    onChange={(e) => handleInputChange('difficulty_level', e.target.value)}
                  />
                  <span>Advanced</span>
                </label>
              </div>
            </div>
          </div>

          <div className="form-actions">
            <button type="button" onClick={onClose} className="cancel-button">
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={loading}
              className="save-button"
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileSettings;