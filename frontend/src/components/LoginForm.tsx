import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginForm.css';

interface LoginFormProps {
  onLogin?: (email: string, password: string) => Promise<void>;
  onRegister?: (userData: any) => Promise<void>;
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin, onRegister }) => {
  const { state, login, register, clearError } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  // Use auth context state
  const loading = state.isLoading;
  const error = state.error;

  // Clear error when switching between login/register
  useEffect(() => {
    clearError();
    setRegistrationSuccess(false);
  }, [isLogin, clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegistrationSuccess(false);

    try {
      if (isLogin) {
        // Use auth context login or fallback to prop
        if (login) {
          await login(email, password);
        } else if (onLogin) {
          await onLogin(email, password);
        }
      } else {
        // Use auth context register or fallback to prop
        const userData = {
          email,
          password,
          first_name: firstName,
          last_name: lastName
        };
        
        if (register) {
          await register(userData);
        } else if (onRegister) {
          await onRegister(userData);
        }
        
        setRegistrationSuccess(true);
        // Switch to login form after successful registration
        setTimeout(() => {
          setIsLogin(true);
          setRegistrationSuccess(false);
        }, 2000);
      }
    } catch (err) {
      // Error is handled by auth context
      console.error('Authentication error:', err);
    }
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <div className="logo-section">
          <img src="/weblogo.png" alt="SnapStudy" className="app-logo" />
          <h1 style={{color:"purple"}}>Snap Study</h1>
        </div>
        {/* <h2>{isLogin ? 'Sign In' : 'Sign Up'}</h2> */}

        {error && <div className="error-message">{error}</div>}
        {registrationSuccess && <div className="success-message">Registration successful! Please log in to continue.</div>}

        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <>
              <input
                type="text"
                placeholder="First Name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
              <input
                type="text"
                placeholder="Last Name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </>
          )}

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? 'Loading...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <p>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="link-button"
          >
            {isLogin ? 'Sign Up' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginForm;