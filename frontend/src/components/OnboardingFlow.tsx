import React, { useState, useEffect } from 'react';
import { OnboardingData } from '../types';
import { useAuth } from '../contexts/AuthContext';
import './OnboardingFlow.css';

interface OnboardingFlowProps {
  onComplete?: (data: OnboardingData) => Promise<void>;
  onSkip?: () => void;
}

const OnboardingFlow: React.FC<OnboardingFlowProps> = ({ onComplete, onSkip }) => {
  const { state, completeOnboarding, skipOnboarding, clearError } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  
  // Use auth context state
  const loading = state.isLoading;
  const error = state.error;
  
  const [formData, setFormData] = useState<OnboardingData>({
    full_name: '',
    age: undefined,
    profession: '',
    education_level: '',
    country: '',
    learning_style: 'visual',
    attention_span: 15,
    difficulty_level: 'intermediate'
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



  const handleNext = () => {
    if (currentStep < 2) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Clear error when component mounts or step changes
  useEffect(() => {
    clearError();
  }, [currentStep, clearError]);

  const handleSubmit = async () => {
    try {
      // Use auth context onboarding completion or fallback to prop
      if (completeOnboarding) {
        await completeOnboarding(formData);
      } else if (onComplete) {
        await onComplete(formData);
      }
    } catch (err) {
      // Error is handled by auth context
      console.error('Onboarding error:', err);
    }
  };

  const handleSkip = () => {
    // Use auth context skip or fallback to prop
    if (skipOnboarding) {
      skipOnboarding();
    } else if (onSkip) {
      onSkip();
    }
  };

  const renderStep1 = () => (
    <div className="onboarding-step">
      <h2>Tell us about yourself</h2>
      <p>Help us personalize your learning experience</p>
      
      <div className="form-group">
        <label>Full Name</label>
        <input
          type="text"
          value={formData.full_name}
          onChange={(e) => handleInputChange('full_name', e.target.value)}
          placeholder="Enter your full name"
        />
      </div>

      <div className="form-group">
        <label>Age</label>
        <input
          type="number"
          value={formData.age || ''}
          onChange={(e) => handleInputChange('age', parseInt(e.target.value) || undefined)}
          placeholder="Enter your age"
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
          placeholder="e.g., Software Engineer, Student, Teacher"
        />
      </div>

      <div className="form-group">
        <label>Education Level</label>
        <select
          value={formData.education_level}
          onChange={(e) => handleInputChange('education_level', e.target.value)}
        >
          <option value="">Select your education level</option>
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
          <option value="">Select your country</option>
          {countries.map(country => (
            <option key={country} value={country}>{country}</option>
          ))}
        </select>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="onboarding-step">
      <h2>Learning Preferences</h2>
      <p>How do you prefer to learn?</p>
      
      <div className="form-group">
        <label>Learning Style</label>
        <div className="radio-group">
          {[
            { value: 'visual', label: 'Visual', desc: 'I learn best with images, diagrams, and visual aids' },
            { value: 'auditory', label: 'Auditory', desc: 'I learn best by listening and discussing' },
            { value: 'reading', label: 'Reading', desc: 'I learn best by reading and writing' }
          ].map(option => (
            <label key={option.value} className="radio-option">
              <input
                type="radio"
                name="learning_style"
                value={option.value}
                checked={formData.learning_style === option.value}
                onChange={(e) => handleInputChange('learning_style', e.target.value)}
              />
              <div>
                <strong>{option.label}</strong>
                <p>{option.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label>Attention Span (Preferred Lesson Length)</label>
        <div className="slider-group">
          <input
            type="range"
            min="5"
            max="60"
            value={formData.attention_span}
            onChange={(e) => handleInputChange('attention_span', parseInt(e.target.value))}
          />
          <span>{formData.attention_span} minutes</span>
        </div>
      </div>

      <div className="form-group">
        <label>Preferred Difficulty Level</label>
        <div className="radio-group">
          {[
            { value: 'beginner', label: 'Beginner', desc: 'I\'m new to most topics' },
            { value: 'intermediate', label: 'Intermediate', desc: 'I have some background knowledge' },
            { value: 'advanced', label: 'Advanced', desc: 'I have extensive experience' }
          ].map(option => (
            <label key={option.value} className="radio-option">
              <input
                type="radio"
                name="difficulty_level"
                value={option.value}
                checked={formData.difficulty_level === option.value}
                onChange={(e) => handleInputChange('difficulty_level', e.target.value)}
              />
              <div>
                <strong>{option.label}</strong>
                <p>{option.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );



  return (
    <div className="onboarding-container">
      <div className="onboarding-form">
        <div className="onboarding-header">
          <img src="/weblogo.png" alt="SnapStudy" className="onboarding-logo" />
          <h1>SnapStudy</h1>
        </div>
        
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(currentStep / 2) * 100}%` }}></div>
        </div>
        
        <div className="step-indicator">
          Step {currentStep} of 2
        </div>

        {error && <div className="error-message">{error}</div>}

        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}

        <div className="button-group">
          {currentStep > 1 && (
            <button type="button" onClick={handleBack} className="btn-secondary">
              Back
            </button>
          )}
          
          {currentStep < 2 ? (
            <button type="button" onClick={handleNext} className="btn-primary">
              Next
            </button>
          ) : (
            <button 
              type="button" 
              onClick={handleSubmit} 
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Completing...' : 'Complete Setup'}
            </button>
          )}
        </div>

        {(onSkip || skipOnboarding) && (
          <div className="skip-option">
            <button type="button" onClick={handleSkip} className="btn-link">
              Skip for now
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingFlow;