import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { ProtectedRoute, useAuthGuard } from './ProtectedRoute';

/**
 * Example component showing how to use authentication context
 */
const AuthExample: React.FC = () => {
  const { state, login, logout, clearError } = useAuth();
  const { isAuthorized, isLoading } = useAuthGuard(true); // Requires onboarding

  const handleLogin = async () => {
    try {
      await login('user@example.com', 'password');
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthorized) {
    return <div>Not authorized to view this content</div>;
  }

  return (
    <div>
      <h2>Authentication Example</h2>
      
      {state.error && (
        <div style={{ color: 'red' }}>
          Error: {state.error}
          <button onClick={clearError}>Clear Error</button>
        </div>
      )}

      {state.isAuthenticated ? (
        <div>
          <p>Welcome, {state.user?.full_name || state.user?.email}!</p>
          <p>Onboarding completed: {state.user?.onboarding_completed ? 'Yes' : 'No'}</p>
          <button onClick={handleLogout}>Logout</button>
        </div>
      ) : (
        <div>
          <p>Please log in</p>
          <button onClick={handleLogin}>Login</button>
        </div>
      )}
    </div>
  );
};

/**
 * Example of using ProtectedRoute wrapper
 */
const ProtectedAuthExample: React.FC = () => {
  return (
    <ProtectedRoute requireOnboarding={true}>
      <AuthExample />
    </ProtectedRoute>
  );
};

export default AuthExample;
export { ProtectedAuthExample };